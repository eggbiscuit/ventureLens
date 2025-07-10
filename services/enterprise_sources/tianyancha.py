"""
天眼查数据源实现
参考ENScan_GO的天眼查模块
"""
import aiohttp
import asyncio
from typing import Dict, Any
from datetime import datetime
import logging

from . import EnterpriseDataSource, QueryResult

logger = logging.getLogger(__name__)

class TianyanchaSource(EnterpriseDataSource):
    """天眼查数据源"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('tianyancha_api_key')
        self.base_url = config.get('tianyancha_base_url', 'https://api.tianyancha.com')
        self.timeout = config.get('timeout', 30)
        
    def get_name(self) -> str:
        return "tianyancha"
    
    async def is_available(self) -> bool:
        """检查天眼查API是否可用"""
        if not self.api_key:
            return False
            
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                async with session.get(
                    f"{self.base_url}/health", 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"天眼查可用性检查失败: {e}")
            return False
    
    async def query_basic_info(self, company_name: str) -> QueryResult:
        """查询基本信息"""
        if not self.enabled or not self.api_key:
            return QueryResult(
                success=False,
                data={},
                source=self.name,
                timestamp=datetime.now().isoformat(),
                error="天眼查未启用或缺少API密钥"
            )
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                params = {"company_name": company_name}
                
                async with session.get(
                    f"{self.base_url}/company/basic",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return QueryResult(
                            success=True,
                            data=self._format_basic_info(data),
                            source=self.name,
                            timestamp=datetime.now().isoformat()
                        )
                    else:
                        error_text = await response.text()
                        return QueryResult(
                            success=False,
                            data={},
                            source=self.name,
                            timestamp=datetime.now().isoformat(),
                            error=f"API错误: {response.status} - {error_text}"
                        )
                        
        except Exception as e:
            logger.error(f"天眼查基本信息查询失败: {e}")
            return QueryResult(
                success=False,
                data={},
                source=self.name,
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )
    
    async def query_financial_info(self, company_name: str) -> QueryResult:
        """查询财务信息"""
        # 模拟实现，实际需要根据天眼查API文档实现
        return QueryResult(
            success=False,
            data={},
            source=self.name,
            timestamp=datetime.now().isoformat(),
            error="财务信息查询功能待实现"
        )
    
    async def query_legal_info(self, company_name: str) -> QueryResult:
        """查询法律信息"""
        # 模拟实现，实际需要根据天眼查API文档实现
        return QueryResult(
            success=False,
            data={},
            source=self.name,
            timestamp=datetime.now().isoformat(),
            error="法律信息查询功能待实现"
        )
    
    async def query_investment_info(self, company_name: str) -> QueryResult:
        """查询投资信息"""
        # 模拟实现，实际需要根据天眼查API文档实现
        return QueryResult(
            success=False,
            data={},
            source=self.name,
            timestamp=datetime.now().isoformat(),
            error="投资信息查询功能待实现"
        )
    
    def _format_basic_info(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化基本信息"""
        return {
            "company_name": raw_data.get("company_name"),
            "registered_capital": raw_data.get("registered_capital"),
            "establishment_date": raw_data.get("establishment_date"),
            "legal_person": raw_data.get("legal_person"),
            "business_scope": raw_data.get("business_scope"),
            "company_status": raw_data.get("status"),
            "address": raw_data.get("address"),
            "industry": raw_data.get("industry"),
            "raw_data": raw_data  # 保留原始数据
        }
