"""
企业数据源统一接口
参考ENScan_GO的设计模式
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
    """查询结果统一格式"""
    success: bool
    data: Dict[str, Any]
    source: str
    timestamp: str
    error: Optional[str] = None

class EnterpriseDataSource(ABC):
    """企业数据源统一接口"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.get_name()
        self.enabled = config.get('enabled', True)
        
    @abstractmethod
    def get_name(self) -> str:
        """获取数据源名称"""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """检查数据源是否可用"""
        pass
    
    @abstractmethod
    async def query_basic_info(self, company_name: str) -> QueryResult:
        """查询基本信息"""
        pass
    
    @abstractmethod
    async def query_financial_info(self, company_name: str) -> QueryResult:
        """查询财务信息"""
        pass
    
    @abstractmethod
    async def query_legal_info(self, company_name: str) -> QueryResult:
        """查询法律信息"""
        pass
    
    @abstractmethod
    async def query_investment_info(self, company_name: str) -> QueryResult:
        """查询投资信息"""
        pass
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            return await self.is_available()
        except Exception:
            return False
