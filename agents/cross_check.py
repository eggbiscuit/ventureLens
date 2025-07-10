"""
交叉验证Agent
对比BP数据与外部搜索信息的一致性
"""

import asyncio
from typing import Dict, Any, List
import logging
from datetime import datetime

from agents.base import BaseAgent
from state import VentureLensState

logger = logging.getLogger(__name__)


class CrossCheckAgent(BaseAgent):
    """交叉验证Agent"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("cross_check", config)
        
    async def _execute(self, state: VentureLensState) -> VentureLensState:
        """执行交叉验证"""
        
        # 如果预筛选未通过，跳过
        if not state.get("prescreen_passed", False):
            return state
        
        company_name = state["company_name"]
        bp_data = state.get("bp_extracted_data", {})
        
        # 如果没有BP数据，跳过交叉验证
        if not bp_data or bp_data.get("error"):
            logger.info("No BP data available for cross-checking")
            state["cross_check_results"] = {
                "status": "skipped",
                "reason": "No BP data available"
            }
            return state
        
        # 收集外部数据进行对比
        external_data = await self._collect_external_data(company_name, state)
        
        # 使用LLM进行交叉验证分析
        cross_check_results = await self.llm_service.generate_cross_check_analysis(
            bp_data, external_data
        )
        
        # 更新状态
        state["cross_check_results"] = cross_check_results
        
        return state
    
    async def _collect_external_data(self, company_name: str, state: VentureLensState) -> Dict[str, Any]:
        """收集外部数据用于交叉验证"""
        
        # 从已有的搜索结果和分析中提取信息
        external_data = {
            "scores": state.get("scores", {}),
            "rationale": state.get("rationale", {}),
            "search_sources": []
        }
        
        # 提取搜索来源的关键信息
        for source in state.get("sources", []):
            external_data["search_sources"].append({
                "query": source.query,
                "content": source.result_snippet,
                "url": source.url,
                "confidence": source.confidence
            })
        
        # 进行一些针对性搜索验证关键声明
        verification_queries = [
            f"{company_name} 成立时间 注册信息",
            f"{company_name} 融资 真实性",
            f"{company_name} 创始人 背景 验证"
        ]
        
        verification_results = []
        for query in verification_queries:
            results = await self.search_and_record(query, state)
            verification_results.extend(results)
        
        external_data["verification_search"] = verification_results
        
        return external_data
