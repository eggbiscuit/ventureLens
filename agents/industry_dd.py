"""
行业尽调Agent
分析行业市场规模、增长率、竞争格局等
"""

import asyncio
from typing import Dict, Any, List
import logging
import json
from datetime import datetime

from agents.base import BaseAgent
from state import VentureLensState
from services.llm_inference_simple import LLMInferenceService

logger = logging.getLogger(__name__)


class IndustryDDAgent(BaseAgent):
    """行业尽职调查Agent"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("industry_dd", config)
        
        # 初始化简化的LLM服务
        self.llm_service = LLMInferenceService(config)
        
        # 行业尽调专用的system message
        self.system_message = """你是一位专业的行业分析师，专门进行投资尽职调查中的行业分析。

你的任务是：
1. 识别公司所属行业和细分领域
2. 分析行业市场规模和增长前景
3. 评估竞争格局和公司竞争优势
4. 识别行业发展趋势和风险因素
5. 对行业吸引力进行评分（1-10分）

评分标准：
- 市场规模：大型市场8-10分，中型市场5-7分，小型市场1-4分
- 增长率：高增长（>20%）8-10分，中增长（5-20%）5-7分，低增长（<5%）1-4分
- 竞争强度：垄断/寡头8-10分，适度竞争5-7分，激烈竞争1-4分
- 进入壁垒：高壁垒8-10分，中等壁垒5-7分，低壁垒1-4分
- 技术门槛：高技术8-10分，中技术5-7分，低技术1-4分

请基于搜索到的信息进行客观、专业的分析，并给出结构化的评分和详细的rationale。"""
        
    async def _execute(self, state: VentureLensState) -> VentureLensState:
        """执行行业尽调"""
        
        # 如果预筛选未通过，跳过
        if not state.get("prescreen_passed", False):
            logger.info(f"跳过行业尽调，预筛选未通过")
            return state
            
        company_name = state["company_name"]
        logger.info(f"开始行业尽调分析：{company_name}")
        
        try:
            # 1. 先进行搜索收集信息
            search_results = await self._search_industry_info(company_name, state)
            
            # 2. 构建分析prompt
            prompt = self._build_analysis_prompt(company_name, search_results)
            
            # 3. 调用简化的LLM服务
            response = await self.llm_service.simple_analyze(prompt, self.system_message)
            
            # 4. 解析结果
            if response.get("success") and response.get("content"):
                analysis_result = self.llm_service.parse_json_response(response["content"])
                
                # 检查是否解析成功
                if "error" in analysis_result:
                    logger.warning(f"JSON解析失败: {analysis_result['error']}")
                    analysis_result = self._create_default_analysis(company_name)
                else:
                    logger.info(f"行业尽调分析成功，综合评分: {analysis_result.get('scores', {}).get('overall', 'N/A')}")
            else:
                logger.error(f"LLM调用失败: {response.get('error', 'Unknown error')}")
                analysis_result = self._create_default_analysis(company_name)
            
        except Exception as e:
            logger.error(f"行业尽调分析异常: {e}")
            analysis_result = self._create_default_analysis(company_name)
        
        # 更新状态
        self._update_state(state, analysis_result)
        
        logger.info(f"行业尽调完成，综合评分: {analysis_result.get('scores', {}).get('overall', 'N/A')}")
        return state
    
    async def _search_industry_info(self, company_name: str, state: VentureLensState) -> List[Dict[str, Any]]:
        """搜索行业相关信息"""
        search_results = []
        
        # 搜索关键词列表
        search_queries = [
            f"{company_name} 行业分析 市场规模",
            f"{company_name} 行业竞争对手 竞争格局", 
            f"{company_name} 所属行业 发展趋势",
            f"{company_name} 行业壁垒 技术门槛"
        ]
        
        for query in search_queries:
            try:
                results = await self.search_and_record(query, state)
                search_results.extend(results)
            except Exception as e:
                logger.warning(f"搜索失败 '{query}': {e}")
        
        return search_results[:10]  # 限制结果数量
    
    def _build_analysis_prompt(self, company_name: str, search_results: List[Dict[str, Any]]) -> str:
        """构建分析prompt"""
        
        # 整理搜索结果
        search_content = ""
        if search_results:
            search_content = "\n".join([
                f"来源: {result.get('url', 'unknown')}\n标题: {result.get('title', '')}\n内容: {result.get('content', '')}\n"
                for result in search_results
            ])
        else:
            search_content = "暂无搜索结果"
        
        prompt = f"""请对公司 "{company_name}" 进行深入的行业尽职调查分析。

搜索到的相关信息：
{search_content}

请分析以下方面：
1. 识别公司所属的具体行业和细分领域
2. 分析该行业的市场规模、增长率和发展阶段
3. 评估行业竞争格局，包括主要竞争对手和市场集中度
4. 分析行业进入壁垒和技术门槛
5. 识别行业发展趋势、机遇和风险
6. 评估该公司在行业中的地位和竞争优势

请严格按照以下JSON格式返回分析结果：
{{
    "industry_identified": "具体行业名称",
    "market_analysis": {{
        "size": "市场规模描述",
        "growth_rate": "增长率",
        "stage": "发展阶段"
    }},
    "competition_analysis": {{
        "landscape": "竞争格局描述",
        "competitors": ["主要竞争对手"],
        "concentration": "市场集中度"
    }},
    "barriers": {{
        "entry_barriers": "进入壁垒分析",
        "tech_barriers": "技术壁垒分析"
    }},
    "trends_risks": {{
        "trends": ["发展趋势"],
        "opportunities": ["发展机遇"],
        "risks": ["风险因素"]
    }},
    "scores": {{
        "market_size": 1-10的数字评分,
        "growth_potential": 1-10的数字评分,
        "competition_intensity": 1-10的数字评分,
        "entry_barriers": 1-10的数字评分,
        "tech_barriers": 1-10的数字评分,
        "overall": 1-10的数字评分
    }},
    "rationale": {{
        "market_size": "市场规模评分理由",
        "growth_potential": "增长潜力评分理由",
        "competition_intensity": "竞争强度评分理由",
        "entry_barriers": "进入壁垒评分理由",
        "tech_barriers": "技术壁垒评分理由",
        "overall": "综合评分理由"
    }}
}}

请确保返回的是完整的JSON格式。"""
        
        return prompt
    
    def _update_state(self, state: VentureLensState, analysis_result: Dict[str, Any]):
        """更新状态"""
        # 更新评分
        if "industry" not in state["scores"]:
            state["scores"]["industry"] = {}
        state["scores"]["industry"].update(analysis_result.get("scores", {}))
        
        # 更新分析理由
        if "industry" not in state["rationale"]:
            state["rationale"]["industry"] = {}
        state["rationale"]["industry"].update(analysis_result.get("rationale", {}))
        
        # 保存详细分析结果
        state["rationale"]["industry"]["industry_identified"] = analysis_result.get("industry_identified", "未识别")
        state["rationale"]["industry"]["market_analysis"] = analysis_result.get("market_analysis", {})
        state["rationale"]["industry"]["competition_analysis"] = analysis_result.get("competition_analysis", {})
        state["rationale"]["industry"]["barriers"] = analysis_result.get("barriers", {})
        state["rationale"]["industry"]["trends_risks"] = analysis_result.get("trends_risks", {})
    
    def _create_default_analysis(self, company_name: str) -> Dict[str, Any]:
        """创建默认分析结果"""
        return {
            "industry_identified": "未识别",
            "market_analysis": {
                "size": "待分析",
                "growth_rate": "待分析", 
                "stage": "待分析"
            },
            "competition_analysis": {
                "landscape": "待分析",
                "competitors": [],
                "concentration": "待分析"
            },
            "barriers": {
                "entry_barriers": "待分析",
                "tech_barriers": "待分析"
            },
            "trends_risks": {
                "trends": [],
                "opportunities": [],
                "risks": []
            },
            "scores": {
                "market_size": 5,
                "growth_potential": 5,
                "competition_intensity": 5,
                "entry_barriers": 5,
                "tech_barriers": 5,
                "overall": 5
            },
            "rationale": {
                "market_size": f"缺乏足够信息对{company_name}所在行业的市场规模进行评估",
                "growth_potential": f"缺乏足够信息对{company_name}所在行业的增长潜力进行评估",
                "competition_intensity": f"缺乏足够信息对{company_name}所在行业的竞争强度进行评估",
                "entry_barriers": f"缺乏足够信息对{company_name}所在行业的进入壁垒进行评估",
                "tech_barriers": f"缺乏足够信息对{company_name}所在行业的技术壁垒进行评估",
                "overall": f"由于信息不足，给予{company_name}所在行业中等评分"
            }
        }
