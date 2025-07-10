"""
多源搜索工具类
整合多个搜索引擎和API，提供统一的搜索接口
"""

import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from urllib.parse import quote
import logging
import json

logger = logging.getLogger(__name__)


class MultiSourceRetriever:
    """多源信息检索器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tavily_api_key = config.get("search", {}).get("tavily_api_key", "")
        self.serper_api_key = config.get("search", {}).get("serper_api_key", "")
        self.timeout = config.get("search", {}).get("timeout", 30)
        self.max_results = config.get("search", {}).get("max_results", 10)
        
    async def search_multiple_sources(self, query: str, sources: List[str] = None) -> List[Dict[str, Any]]:
        """从多个源搜索信息"""
        if sources is None:
            sources = ["tavily", "serper"]
            
        tasks = []
        
        for source in sources:
            if source == "tavily" and self.tavily_api_key:
                tasks.append(self._search_tavily(query))
            elif source == "serper" and self.serper_api_key:
                tasks.append(self._search_serper(query))
                
        if not tasks:
            # 如果没有可用的API，使用fallback搜索
            return await self._fallback_search(query)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        all_results = []
        for result in results:
            if isinstance(result, list):
                all_results.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Search error: {result}")
                
        return all_results[:self.max_results]
    
    async def _search_tavily(self, query: str) -> List[Dict[str, Any]]:
        """使用Tavily API搜索"""
        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": self.tavily_api_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": 5,
                "include_answer": True,
                "include_images": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=self.timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        
                        for item in data.get("results", []):
                            results.append({
                                "title": item.get("title", ""),
                                "url": item.get("url", ""),
                                "content": item.get("content", ""),
                                "score": item.get("score", 0.7),
                                "source": "tavily"
                            })
                        return results
                        
        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            
        return []
    
    async def _search_serper(self, query: str) -> List[Dict[str, Any]]:
        """使用Serper API搜索"""
        try:
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": self.serper_api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "q": query,
                "num": 5
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=self.timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        
                        for item in data.get("organic", []):
                            results.append({
                                "title": item.get("title", ""),
                                "url": item.get("link", ""),
                                "content": item.get("snippet", ""),
                                "score": 0.8,  # Serper通常质量较高
                                "source": "serper"
                            })
                        return results
                        
        except Exception as e:
            logger.error(f"Serper search error: {e}")
            
        return []
    
        return []
    
    async def _fallback_search(self, query: str) -> List[Dict[str, Any]]:
        """fallback搜索方法，返回模拟数据"""
        logger.warning(f"Using fallback search for query: {query}")
        
        # 返回基本的模拟数据，避免系统完全失败
        return [
            {
                "title": f"关于{query}的基本信息",
                "url": "https://example.com",
                "content": f"{query}是一家公司，相关信息需要进一步调研。建议通过其他渠道获取更多详细信息。",
                "score": 0.3,
                "source": "fallback"
            },
            {
                "title": f"{query}投资分析",
                "url": "https://example.com/analysis",
                "content": f"对{query}的投资分析需要更多可靠数据源。请配置有效的搜索API以获取准确信息。",
                "score": 0.3,
                "source": "fallback"
            }
        ]
    
    async def search_specific_site(self, query: str, site: str) -> List[Dict[str, Any]]:
        """在特定网站搜索"""
        site_query = f"site:{site} {query}"
        return await self.search_multiple_sources(site_query, ["serper", "tavily"])
    
    async def search_financial_data(self, company_name: str) -> List[Dict[str, Any]]:
        """搜索财务相关数据"""
        queries = [
            f"{company_name} 融资 估值",
            f"{company_name} 财务报表 收入",
            f"{company_name} 投资 轮次"
        ]
        
        all_results = []
        for query in queries:
            results = await self.search_multiple_sources(query)
            all_results.extend(results)
            
        return all_results
    
    async def search_industry_data(self, industry: str, company_name: str) -> List[Dict[str, Any]]:
        """搜索行业相关数据"""
        queries = [
            f"{industry} 市场规模 增长率",
            f"{industry} 竞争格局 分析",
            f"{company_name} {industry} 市场份额"
        ]
        
        all_results = []
        for query in queries:
            results = await self.search_multiple_sources(query)
            all_results.extend(results)
            
        return all_results
    
    async def search_team_info(self, company_name: str, founders: List[str] = None) -> List[Dict[str, Any]]:
        """搜索团队信息"""
        queries = [f"{company_name} 创始人 团队 背景"]
        
        if founders:
            for founder in founders:
                queries.append(f"{founder} 履历 经验")
                
        all_results = []
        for query in queries:
            results = await self.search_multiple_sources(query)
            all_results.extend(results)
            
        return all_results
