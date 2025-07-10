"""
企业数据源管理器
参考ENScan_GO的runner设计
"""
import asyncio
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from . import EnterpriseDataSource, QueryResult
from .tianyancha import TianyanchaSource
from .aiqicha import AiqichaSource

logger = logging.getLogger(__name__)

class EnterpriseSourceManager:
    """企业数据源管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sources: Dict[str, EnterpriseDataSource] = {}
        self.initialize_sources()
        
    def initialize_sources(self):
        """初始化所有数据源"""
        sources_config = self.config.get('enterprise_sources', {})
        
        # 注册天眼查
        if sources_config.get('tianyancha', {}).get('enabled', False):
            self.sources['tianyancha'] = TianyanchaSource(sources_config.get('tianyancha', {}))
        
        # 注册爱企查
        if sources_config.get('aiqicha', {}).get('enabled', False):
            self.sources['aiqicha'] = AiqichaSource(sources_config.get('aiqicha', {}))
        
        logger.info(f"已注册 {len(self.sources)} 个企业数据源")
    
    async def health_check_all(self) -> Dict[str, bool]:
        """检查所有数据源健康状态"""
        results = {}
        
        tasks = []
        for name, source in self.sources.items():
            tasks.append(self._check_source_health(name, source))
        
        health_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, (name, _) in enumerate(self.sources.items()):
            results[name] = health_results[i] if not isinstance(health_results[i], Exception) else False
        
        return results
    
    async def _check_source_health(self, name: str, source: EnterpriseDataSource) -> bool:
        """检查单个数据源健康状态"""
        try:
            return await source.health_check()
        except Exception as e:
            logger.error(f"数据源 {name} 健康检查失败: {e}")
            return False
    
    async def query_company_info(self, company_name: str, 
                               info_type: str = 'basic',
                               preferred_sources: List[str] = None) -> List[QueryResult]:
        """查询企业信息"""
        
        # 确定要使用的数据源
        target_sources = preferred_sources if preferred_sources else list(self.sources.keys())
        target_sources = [name for name in target_sources if name in self.sources]
        
        if not target_sources:
            return []
        
        # 并行查询
        tasks = []
        for source_name in target_sources:
            source = self.sources[source_name]
            task = self._query_from_source(source, company_name, info_type)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤结果
        valid_results = []
        for result in results:
            if isinstance(result, QueryResult):
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"查询异常: {result}")
        
        return valid_results
    
    async def _query_from_source(self, source: EnterpriseDataSource, 
                               company_name: str, info_type: str) -> QueryResult:
        """从单个数据源查询"""
        try:
            if info_type == 'basic':
                return await source.query_basic_info(company_name)
            elif info_type == 'financial':
                return await source.query_financial_info(company_name)
            elif info_type == 'legal':
                return await source.query_legal_info(company_name)
            elif info_type == 'investment':
                return await source.query_investment_info(company_name)
            else:
                return QueryResult(
                    success=False,
                    data={},
                    source=source.name,
                    timestamp=datetime.now().isoformat(),
                    error=f"不支持的查询类型: {info_type}"
                )
        except Exception as e:
            logger.error(f"从 {source.name} 查询失败: {e}")
            return QueryResult(
                success=False,
                data={},
                source=source.name,
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )
    
    def get_available_sources(self) -> List[str]:
        """获取可用的数据源名称"""
        return list(self.sources.keys())
    
    async def merge_results(self, results: List[QueryResult]) -> Dict[str, Any]:
        """合并多个数据源的结果"""
        merged_data = {}
        sources_info = []
        
        for result in results:
            if result.success:
                # 合并数据
                merged_data.update(result.data)
                sources_info.append({
                    "source": result.source,
                    "timestamp": result.timestamp,
                    "success": True
                })
            else:
                sources_info.append({
                    "source": result.source,
                    "timestamp": result.timestamp,
                    "success": False,
                    "error": result.error
                })
        
        return {
            "merged_data": merged_data,
            "sources_info": sources_info,
            "total_sources": len(results),
            "successful_sources": len([r for r in results if r.success])
        }
