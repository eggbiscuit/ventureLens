"""
财务尽调Agent
分析财务状况、融资历史等
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


class FinDDAgent(BaseAgent):
    """财务尽职调查Agent"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("fin_dd", config)
        
        # 初始化简化的LLM服务
        self.llm_service = LLMInferenceService(config)
        
        # 财务尽调专用的system message
        self.system_message = """你是一位专业的财务分析师，专门进行投资尽职调查中的财务分析。

你的任务是：
1. 分析公司的营收状况和商业模式
2. 评估公司的盈利能力和成本控制
3. 研究公司的融资历史和投资方背景
4. 判断公司的财务健康度和可持续性

评分标准：
- 营收状况：高营收增长8-10分，稳定增长5-7分，增长缓慢1-4分
- 盈利能力：已盈利8-10分，接近盈利5-7分，亏损严重1-4分
- 融资历史：知名投资方8-10分，一般投资方5-7分，融资困难1-4分
- 财务健康度：财务稳健8-10分，基本健康5-7分，财务风险1-4分

请基于搜索到的信息进行客观、专业的分析，并给出结构化的评分和详细的rationale。"""
        
    async def _execute(self, state: VentureLensState) -> VentureLensState:
        """执行财务尽调"""
        
        # 如果预筛选未通过，跳过
        if not state.get("prescreen_passed", False):
            logger.info(f"跳过财务尽调，预筛选未通过")
            return state
            
        company_name = state["company_name"]
        logger.info(f"开始财务尽调分析：{company_name}")
        
        try:
            # 1. 先进行搜索收集信息
            search_results = await self._search_financial_info(company_name, state)
            
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
                    logger.info(f"财务尽调分析成功，综合评分: {analysis_result.get('scores', {}).get('overall', 'N/A')}")
            else:
                logger.error(f"LLM调用失败: {response.get('error', 'Unknown error')}")
                analysis_result = self._create_default_analysis(company_name)
            
        except Exception as e:
            logger.error(f"财务尽调分析异常: {e}")
            analysis_result = self._create_default_analysis(company_name)
        
        # 更新状态
        self._update_state(state, analysis_result)
        
        logger.info(f"财务尽调完成，综合评分: {analysis_result.get('scores', {}).get('overall', 'N/A')}")
        return state
    
    async def _search_financial_info(self, company_name: str, state: VentureLensState) -> List[Dict[str, Any]]:
        """搜索财务相关信息"""
        search_results = []
        
        # 搜索关键词列表
        search_queries = [
            f"{company_name} 营收 收入 业绩",
            f"{company_name} 融资 投资 估值",
            f"{company_name} 财务 盈利 亏损",
            f"{company_name} 投资方 融资轮次"
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
        
        prompt = f"""请对公司 "{company_name}" 进行深入的财务尽职调查分析。

搜索到的相关信息：
{search_content}

请分析以下方面：
1. 营收状况：营收规模、增长趋势、商业模式清晰度
2. 盈利能力：盈利状况、利润率、成本控制
3. 融资历史：融资轮次、估值、投资方质量
4. 财务健康度：现金流、负债率、财务可持续性

请严格按照以下JSON格式返回分析结果：
{{
    "key_metrics": {{
        "revenue": "营收数据和趋势",
        "funding": "融资信息",
        "valuation": "估值信息",
        "profitability": "盈利状况"
    }},
    "funding_details": {{
        "total_funding": "总融资金额",
        "latest_round": "最新轮次",
        "investors": ["主要投资方"],
        "valuation_trend": "估值变化趋势"
    }},
    "financial_analysis": {{
        "revenue_growth": "营收增长情况",
        "business_model": "商业模式分析",
        "cost_structure": "成本结构",
        "cash_flow": "现金流状况"
    }},
    "scores": {{
        "revenue_status": 1-10的数字评分,
        "profitability": 1-10的数字评分,
        "funding_history": 1-10的数字评分,
        "financial_health": 1-10的数字评分,
        "overall": 1-10的数字评分
    }},
    "rationale": {{
        "revenue_status": "营收状况评分理由",
        "profitability": "盈利能力评分理由",
        "funding_history": "融资历史评分理由",
        "financial_health": "财务健康度评分理由",
        "overall": "综合评分理由"
    }}
}}

请确保返回的是完整的JSON格式。"""
        
        return prompt
    
    def _update_state(self, state: VentureLensState, analysis_result: Dict[str, Any]):
        """更新状态"""
        # 更新评分
        if "financial" not in state["scores"]:
            state["scores"]["financial"] = {}
        state["scores"]["financial"].update(analysis_result.get("scores", {}))
        
        # 更新分析理由
        if "financial" not in state["rationale"]:
            state["rationale"]["financial"] = {}
        state["rationale"]["financial"].update(analysis_result.get("rationale", {}))
        
        # 保存详细分析结果
        state["rationale"]["financial"]["key_metrics"] = analysis_result.get("key_metrics", {})
        state["rationale"]["financial"]["funding_details"] = analysis_result.get("funding_details", {})
        state["rationale"]["financial"]["financial_analysis"] = analysis_result.get("financial_analysis", {})
    
    def _create_default_analysis(self, company_name: str) -> Dict[str, Any]:
        """创建默认分析结果"""
        return {
            "key_metrics": {
                "revenue": "待分析",
                "funding": "待分析",
                "valuation": "待分析",
                "profitability": "待分析"
            },
            "funding_details": {
                "total_funding": "未知",
                "latest_round": "未知",
                "investors": [],
                "valuation_trend": "待分析"
            },
            "financial_analysis": {
                "revenue_growth": "待分析",
                "business_model": "待分析",
                "cost_structure": "待分析",
                "cash_flow": "待分析"
            },
            "scores": {
                "revenue_status": 5,
                "profitability": 5,
                "funding_history": 5,
                "financial_health": 5,
                "overall": 5
            },
            "rationale": {
                "revenue_status": f"缺乏足够信息对{company_name}营收状况进行评估",
                "profitability": f"缺乏足够信息对{company_name}盈利能力进行评估",
                "funding_history": f"缺乏足够信息对{company_name}融资历史进行评估",
                "financial_health": f"缺乏足够信息对{company_name}财务健康度进行评估",
                "overall": f"由于信息不足，给予{company_name}财务状况中等评分"
            }
        }
