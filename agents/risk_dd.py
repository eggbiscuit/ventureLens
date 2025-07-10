"""
风险尽调Agent
分析投资风险等
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


class RiskDDAgent(BaseAgent):
    """风险尽职调查Agent"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("risk_dd", config)
        
        # 初始化简化的LLM服务
        self.llm_service = LLMInferenceService(config)
        
        # 风险尽调专用的system message
        self.system_message = """你是一位专业的风险评估专家，专门进行投资尽职调查中的风险分析。

你的任务是：
1. 识别和分析市场风险
2. 评估竞争风险和威胁
3. 分析运营风险和执行风险
4. 评估监管和政策风险
5. 对各类风险进行量化评分（1-10分，分数越高表示风险越低）

评分标准：
- 市场风险：市场稳定性高8-10分，中等风险5-7分，高风险1-4分
- 竞争风险：竞争优势明显8-10分，一般竞争5-7分，激烈竞争1-4分
- 运营风险：运营稳健8-10分，一般风险5-7分，高运营风险1-4分
- 监管风险：合规完善8-10分，一般合规5-7分，监管风险高1-4分

请基于搜索到的信息进行客观、专业的分析，并给出结构化的评分和详细的rationale。"""
        
    async def _execute(self, state: VentureLensState) -> VentureLensState:
        """执行风险尽调"""
        
        # 如果预筛选未通过，跳过
        if not state.get("prescreen_passed", False):
            logger.info(f"跳过风险尽调，预筛选未通过")
            return state
            
        company_name = state["company_name"]
        logger.info(f"开始风险尽调分析：{company_name}")
        
        try:
            # 1. 先进行搜索收集信息
            search_results = await self._search_risk_info(company_name, state)
            
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
                    logger.info(f"风险尽调分析成功，综合评分: {analysis_result.get('scores', {}).get('overall', 'N/A')}")
            else:
                logger.error(f"LLM调用失败: {response.get('error', 'Unknown error')}")
                analysis_result = self._create_default_analysis(company_name)
            
        except Exception as e:
            logger.error(f"风险尽调分析异常: {e}")
            analysis_result = self._create_default_analysis(company_name)
        
        # 更新状态
        self._update_state(state, analysis_result)
        
        logger.info(f"风险尽调完成，综合评分: {analysis_result.get('scores', {}).get('overall', 'N/A')}")
        return state
    
    async def _search_risk_info(self, company_name: str, state: VentureLensState) -> List[Dict[str, Any]]:
        """搜索风险相关信息"""
        search_results = []
        
        # 搜索关键词列表
        search_queries = [
            f"{company_name} 风险 问题 争议",
            f"{company_name} 竞争对手 威胁",
            f"{company_name} 监管 合规 政策",
            f"{company_name} 负面 诉讼 违规"
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
        
        prompt = f"""请对公司 "{company_name}" 进行全面的投资风险评估分析。

搜索到的相关信息：
{search_content}

请从以下四个维度进行风险分析（注意：分数越高表示风险越低）：
1. 市场风险：市场需求变化、技术替代、经济周期影响
2. 竞争风险：现有竞争对手威胁、新进入者风险、价格竞争
3. 运营风险：团队执行能力、技术实现风险、供应链风险
4. 监管风险：政策变化、合规要求、法律纠纷风险

请严格按照以下JSON格式返回分析结果：
{{
    "risk_analysis": {{
        "market_risks": ["具体市场风险1", "具体市场风险2"],
        "competition_risks": ["具体竞争风险1", "具体竞争风险2"],
        "operational_risks": ["具体运营风险1", "具体运营风险2"],
        "regulatory_risks": ["具体监管风险1", "具体监管风险2"]
    }},
    "major_concerns": {{
        "high_risk_areas": ["高风险领域1", "高风险领域2"],
        "critical_issues": ["关键问题1", "关键问题2"],
        "potential_threats": ["潜在威胁1", "潜在威胁2"]
    }},
    "risk_mitigation": {{
        "existing_measures": ["现有风险缓解措施1", "现有风险缓解措施2"],
        "recommended_actions": ["建议措施1", "建议措施2"],
        "monitoring_points": ["需要监控的要点1", "需要监控的要点2"]
    }},
    "scores": {{
        "market_risk": 1-10的数字评分,
        "competition_risk": 1-10的数字评分,
        "operational_risk": 1-10的数字评分,
        "regulatory_risk": 1-10的数字评分,
        "overall": 1-10的数字评分
    }},
    "rationale": {{
        "market_risk": "市场风险评分理由（分数越高风险越低）",
        "competition_risk": "竞争风险评分理由（分数越高风险越低）",
        "operational_risk": "运营风险评分理由（分数越高风险越低）",
        "regulatory_risk": "监管风险评分理由（分数越高风险越低）",
        "overall": "综合风险评价（分数越高风险越低）"
    }}
}}

请确保返回的是完整的JSON格式。"""
        
        return prompt
    
    def _update_state(self, state: VentureLensState, analysis_result: Dict[str, Any]):
        """更新状态"""
        # 更新评分
        if "risk" not in state["scores"]:
            state["scores"]["risk"] = {}
        state["scores"]["risk"].update(analysis_result.get("scores", {}))
        
        # 更新分析理由
        if "risk" not in state["rationale"]:
            state["rationale"]["risk"] = {}
        state["rationale"]["risk"].update(analysis_result.get("rationale", {}))
        
        # 保存详细分析结果
        state["rationale"]["risk"]["risk_analysis"] = analysis_result.get("risk_analysis", {})
        state["rationale"]["risk"]["major_concerns"] = analysis_result.get("major_concerns", {})
        state["rationale"]["risk"]["risk_mitigation"] = analysis_result.get("risk_mitigation", {})
    
    def _create_default_analysis(self, company_name: str) -> Dict[str, Any]:
        """创建默认分析结果"""
        return {
            "risk_analysis": {
                "market_risks": [],
                "competition_risks": [],
                "operational_risks": [],
                "regulatory_risks": []
            },
            "major_concerns": {
                "high_risk_areas": [],
                "critical_issues": [],
                "potential_threats": []
            },
            "risk_mitigation": {
                "existing_measures": [],
                "recommended_actions": [],
                "monitoring_points": []
            },
            "scores": {
                "market_risk": 5,
                "competition_risk": 5,
                "operational_risk": 5,
                "regulatory_risk": 5,
                "overall": 5
            },
            "rationale": {
                "market_risk": f"缺乏足够信息对{company_name}市场风险进行评估",
                "competition_risk": f"缺乏足够信息对{company_name}竞争风险进行评估",
                "operational_risk": f"缺乏足够信息对{company_name}运营风险进行评估",
                "regulatory_risk": f"缺乏足够信息对{company_name}监管风险进行评估",
                "overall": f"由于信息不足，给予{company_name}风险状况中等评分"
            }
        }
