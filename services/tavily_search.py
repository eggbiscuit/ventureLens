"""
Tavily搜索服务模块
"""

import asyncio
from typing import List, Dict, Any, Optional
from tavily import TavilyClient
import logging

logger = logging.getLogger(__name__)


class TavilySearchService:
    """Tavily搜索服务"""
    
    def __init__(self, api_key: str):
        self.client = TavilyClient(api_key=api_key)
        
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """执行搜索"""
        try:
            # Tavily的搜索是同步的，我们在异步函数中运行
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=max_results,
                    include_images=False,
                    include_answer=True
                )
            )
            
            results = []
            for result in response.get("results", []):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0.0),
                    "source": "tavily"
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            return []
    
    async def get_answer(self, query: str) -> Optional[str]:
        """获取AI生成的答案"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.qna_search(query=query)
            )
            return response.get("answer", "")
        except Exception as e:
            logger.error(f"Tavily QnA error: {e}")
            return None
