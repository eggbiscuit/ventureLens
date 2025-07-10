"""
爱企查数据源实现
"""
import aiohttp
from typing import Dict, Any
from datetime import datetime
import logging

from . import EnterpriseDataSource, QueryResult

logger = logging.getLogger(__name__)

class AiqichaSource(EnterpriseDataSource):
    """爱企查数据源"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('aiqicha_api_key')
        self.base_url = config.get('aiqicha_base_url', 'https://api.aiqicha.com')
        self.timeout = config.get('timeout', 30)
        
    def get_name(self) -> str:
        return "aiqicha"
    
    async def is_available(self) -> bool:
        """检查爱企查API是否可用"""
        if not self.api_key:
            return False
            
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-API-Key": self.api_key}
                async with session.get(
                    f"{self.base_url}/ping", 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"爱企查可用性检查失败: {e}")
            return False
    
    async def query_basic_info(self, company_name: str) -> QueryResult:
        """查询基本信息"""
        if not self.enabled or not self.api_key:
            return QueryResult(
                success=False,
                data={},
                source=self.name,
                timestamp=datetime.now().isoformat(),
                error="爱企查未启用或缺少API密钥"
            )
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-API-Key": self.api_key}
                data = {"keyword": company_name}
                
                async with session.post(
                    f"{self.base_url}/company/info",
                    headers=headers,
                    json=data,
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
            logger.error(f"爱企查基本信息查询失败: {e}")
            return QueryResult(
                success=False,
                data={},
                source=self.name,
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )
    
    async def query_financial_info(self, company_name: str) -> QueryResult:
        """查询财务信息"""
        return QueryResult(
            success=False,
            data={},
            source=self.name,
            timestamp=datetime.now().isoformat(),
            error="财务信息查询功能待实现"
        )
    
    async def query_legal_info(self, company_name: str) -> QueryResult:
        """查询法律信息"""
        return QueryResult(
            success=False,
            data={},
            source=self.name,
            timestamp=datetime.now().isoformat(),
            error="法律信息查询功能待实现"
        )
    
    async def query_investment_info(self, company_name: str) -> QueryResult:
        """查询投资信息"""
        return QueryResult(
            success=False,
            data={},
            source=self.name,
            timestamp=datetime.now().isoformat(),
            error="投资信息查询功能待实现"
        )
    
    def _format_basic_info(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化基本信息"""
        # 爱企查的数据格式可能与天眼查不同，需要适配
        return {
            "company_name": raw_data.get("entName"),
            "registered_capital": raw_data.get("regCap"),
            "establishment_date": raw_data.get("startDate"),
            "legal_person": raw_data.get("legalPersonName"),
            "business_scope": raw_data.get("businessScope"),
            "company_status": raw_data.get("entStatus"),
            "address": raw_data.get("address"),
            "industry": raw_data.get("industry"),
            "raw_data": raw_data
        }
