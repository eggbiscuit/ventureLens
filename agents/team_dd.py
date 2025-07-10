"""
团队尽调Agent
分析团队背景、经验、成就等
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


class TeamDDAgent(BaseAgent):
    """团队尽职调查Agent"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("team_dd", config)
        
        # 初始化简化的LLM服务
        self.llm_service = LLMInferenceService(config)
        
        # 团队尽调专用的system message
        self.system_message = """你是一位专业的团队评估专家，专门进行投资尽职调查中的团队分析。

你的任务是：
1. 识别关键团队成员和创始人信息
2. 评估创始人的教育背景和工作经历
3. 分析团队的行业经验和专业能力
4. 评估团队的过往成就和成功案例
5. 判断团队结构的完整性和关键岗位配置

评分标准：
- 创始人背景：顶级背景8-10分，良好背景5-7分，一般背景1-4分
- 团队经验：丰富经验8-10分，中等经验5-7分，经验不足1-4分
- 过往成就：卓越成就8-10分，一定成就5-7分，缺乏成就1-4分
- 团队完整性：完整配置8-10分，基本完整5-7分，不完整1-4分

请基于搜索到的信息进行客观、专业的分析，并给出结构化的评分和详细的rationale。"""
        
    async def _execute(self, state: VentureLensState) -> VentureLensState:
        """执行团队尽调"""
        
        # 如果预筛选未通过，跳过
        if not state.get("prescreen_passed", False):
            logger.info(f"跳过团队尽调，预筛选未通过")
            return state
            
        company_name = state["company_name"]
        logger.info(f"开始团队尽调分析：{company_name}")
        
        try:
            # 1. 先进行搜索收集信息
            search_results = await self._search_team_info(company_name, state)
            
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
                    logger.info(f"团队尽调分析成功，综合评分: {analysis_result.get('scores', {}).get('overall', 'N/A')}")
            else:
                logger.error(f"LLM调用失败: {response.get('error', 'Unknown error')}")
                analysis_result = self._create_default_analysis(company_name)
            
        except Exception as e:
            logger.error(f"团队尽调分析异常: {e}")
            analysis_result = self._create_default_analysis(company_name)
        
        # 更新状态
        self._update_state(state, analysis_result)
        
        logger.info(f"团队尽调完成，综合评分: {analysis_result.get('scores', {}).get('overall', 'N/A')}")
        return state
    
    async def _search_team_info(self, company_name: str, state: VentureLensState) -> List[Dict[str, Any]]:
        """搜索团队相关信息"""
        search_results = []
        
        # 搜索关键词列表
        search_queries = [
            f"{company_name} 创始人 CEO 背景",
            f"{company_name} 团队成员 核心团队",
            f"{company_name} 创始人 工作经历 教育背景",
            f"{company_name} 团队 过往成就 经验"
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
        
        prompt = f"""请对公司 "{company_name}" 进行深入的团队尽职调查分析。

搜索到的相关信息：
{search_content}

请分析以下方面：
1. 创始人背景：教育背景、工作经历、行业经验
2. 团队经验：核心团队的相关经验和专业能力  
3. 过往成就：团队或创始人的历史成就和成功案例
4. 团队完整性：团队结构是否完整，关键岗位是否齐备

请严格按照以下JSON格式返回分析结果：
{{
    "key_people": ["关键人员姓名"],
    "founder_info": {{
        "name": "创始人姓名",
        "education": "教育背景",
        "experience": "工作经历",
        "industry_exp": "行业经验"
    }},
    "team_analysis": {{
        "core_members": ["核心团队成员"],
        "key_positions": ["关键岗位"],
        "missing_roles": ["缺失角色"]
    }},
    "achievements": {{
        "founder_achievements": ["创始人成就"],
        "team_achievements": ["团队成就"],
        "recognition": ["获得认可"]
    }},
    "scores": {{
        "founder_background": 1-10的数字评分,
        "team_experience": 1-10的数字评分,
        "past_achievements": 1-10的数字评分,
        "team_completeness": 1-10的数字评分,
        "overall": 1-10的数字评分
    }},
    "rationale": {{
        "founder_background": "创始人背景评分理由",
        "team_experience": "团队经验评分理由",
        "past_achievements": "过往成就评分理由",
        "team_completeness": "团队完整性评分理由",
        "overall": "综合评分理由"
    }}
}}

请确保返回的是完整的JSON格式。"""
        
        return prompt
    
    def _update_state(self, state: VentureLensState, analysis_result: Dict[str, Any]):
        """更新状态"""
        # 更新评分
        if "team" not in state["scores"]:
            state["scores"]["team"] = {}
        state["scores"]["team"].update(analysis_result.get("scores", {}))
        
        # 更新分析理由
        if "team" not in state["rationale"]:
            state["rationale"]["team"] = {}
        state["rationale"]["team"].update(analysis_result.get("rationale", {}))
        
        # 保存详细分析结果
        state["rationale"]["team"]["key_people"] = analysis_result.get("key_people", [])
        state["rationale"]["team"]["founder_info"] = analysis_result.get("founder_info", {})
        state["rationale"]["team"]["team_analysis"] = analysis_result.get("team_analysis", {})
        state["rationale"]["team"]["achievements"] = analysis_result.get("achievements", {})
    
    def _create_default_analysis(self, company_name: str) -> Dict[str, Any]:
        """创建默认分析结果"""
        return {
            "key_people": [],
            "founder_info": {
                "name": "未识别",
                "education": "待分析",
                "experience": "待分析",
                "industry_exp": "待分析"
            },
            "team_analysis": {
                "core_members": [],
                "key_positions": [],
                "missing_roles": []
            },
            "achievements": {
                "founder_achievements": [],
                "team_achievements": [],
                "recognition": []
            },
            "scores": {
                "founder_background": 5,
                "team_experience": 5,
                "past_achievements": 5,
                "team_completeness": 5,
                "overall": 5
            },
            "rationale": {
                "founder_background": f"缺乏足够信息对{company_name}创始人背景进行评估",
                "team_experience": f"缺乏足够信息对{company_name}团队经验进行评估",
                "past_achievements": f"缺乏足够信息对{company_name}团队过往成就进行评估",
                "team_completeness": f"缺乏足够信息对{company_name}团队完整性进行评估",
                "overall": f"由于信息不足，给予{company_name}团队中等评分"
            }
        }
