"""
VentureLens工具包系统
为各个Agent提供可调用的工具集合
"""

import asyncio
import logging
from typing import Dict, Any, List, Callable, Optional
import json
from abc import ABC, abstractmethod

# 新增MCP和企业数据源集成
from .mcp.manager import MCPManager
from .enterprise_sources.manager import EnterpriseSourceManager

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """基础工具类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        pass
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI工具格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_parameters_schema()
            }
        }
    
    @abstractmethod
    def get_parameters_schema(self) -> Dict[str, Any]:
        """获取参数schema"""
        pass


class SearchTool(BaseTool):
    """搜索工具"""
    
    def __init__(self, retriever):
        super().__init__(
            name="search_information",
            description="搜索指定主题的相关信息，返回搜索结果"
        )
        self.retriever = retriever
    
    async def execute(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """执行搜索"""
        try:
            results = await self.retriever.search_multiple_sources(query)
            
            # 格式化结果
            formatted_results = []
            for result in results[:max_results]:
                formatted_results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", "")[:500],  # 限制内容长度
                    "source": result.get("source", "unknown")
                })
            
            return {
                "success": True,
                "results": formatted_results,
                "query": query,
                "total_found": len(formatted_results)
            }
            
        except Exception as e:
            logger.error(f"Search tool error: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询字符串"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回结果数",
                    "default": 5
                }
            },
            "required": ["query"]
        }


class CompanyInfoTool(BaseTool):
    """公司信息工具"""
    
    def __init__(self, retriever):
        super().__init__(
            name="get_company_info",
            description="获取指定公司的基本信息，包括成立时间、业务领域、注册信息等"
        )
        self.retriever = retriever
    
    async def execute(self, company_name: str) -> Dict[str, Any]:
        """获取公司信息"""
        try:
            queries = [
                f"{company_name} 公司基本信息 成立时间",
                f"{company_name} 业务范围 主营业务",
                f"{company_name} 注册资本 法人代表"
            ]
            
            all_results = []
            for query in queries:
                results = await self.retriever.search_multiple_sources(query)
                all_results.extend(results)
            
            # 提取关键信息
            info = {
                "company_name": company_name,
                "basic_info": self._extract_basic_info(all_results),
                "business_scope": self._extract_business_scope(all_results),
                "registration_info": self._extract_registration_info(all_results)
            }
            
            return {
                "success": True,
                "company_info": info,
                "source_count": len(all_results)
            }
            
        except Exception as e:
            logger.error(f"Company info tool error: {e}")
            return {
                "success": False,
                "error": str(e),
                "company_name": company_name
            }
    
    def _extract_basic_info(self, results: List[Dict[str, Any]]) -> str:
        """提取基本信息"""
        content = " ".join([r.get("content", "") for r in results])
        return content[:500]  # 简化版本，实际可以用NLP提取
    
    def _extract_business_scope(self, results: List[Dict[str, Any]]) -> str:
        """提取业务范围"""
        content = " ".join([r.get("content", "") for r in results])
        return content[:300]
    
    def _extract_registration_info(self, results: List[Dict[str, Any]]) -> str:
        """提取注册信息"""
        content = " ".join([r.get("content", "") for r in results])
        return content[:300]
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "公司名称"
                }
            },
            "required": ["company_name"]
        }


class IndustryAnalysisTool(BaseTool):
    """行业分析工具"""
    
    def __init__(self, retriever):
        super().__init__(
            name="analyze_industry",
            description="分析指定行业的市场规模、增长趋势、竞争格局等"
        )
        self.retriever = retriever
    
    async def execute(self, industry: str, company_name: str = "") -> Dict[str, Any]:
        """执行行业分析"""
        try:
            queries = [
                f"{industry} 市场规模 增长率 2024",
                f"{industry} 竞争格局 主要公司",
                f"{industry} 发展趋势 前景分析"
            ]
            
            if company_name:
                queries.append(f"{company_name} {industry} 市场份额 竞争地位")
            
            all_results = []
            for query in queries:
                results = await self.retriever.search_multiple_sources(query)
                all_results.extend(results)
            
            analysis = {
                "industry": industry,
                "market_overview": self._analyze_market_overview(all_results),
                "competition_analysis": self._analyze_competition(all_results),
                "growth_trends": self._analyze_growth_trends(all_results)
            }
            
            return {
                "success": True,
                "industry_analysis": analysis,
                "source_count": len(all_results)
            }
            
        except Exception as e:
            logger.error(f"Industry analysis tool error: {e}")
            return {
                "success": False,
                "error": str(e),
                "industry": industry
            }
    
    def _analyze_market_overview(self, results: List[Dict[str, Any]]) -> str:
        """分析市场概况"""
        content = " ".join([r.get("content", "") for r in results])
        return content[:400]
    
    def _analyze_competition(self, results: List[Dict[str, Any]]) -> str:
        """分析竞争格局"""
        content = " ".join([r.get("content", "") for r in results])
        return content[:400]
    
    def _analyze_growth_trends(self, results: List[Dict[str, Any]]) -> str:
        """分析增长趋势"""
        content = " ".join([r.get("content", "") for r in results])
        return content[:400]
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "industry": {
                    "type": "string",
                    "description": "行业名称"
                },
                "company_name": {
                    "type": "string",
                    "description": "公司名称（可选）",
                    "default": ""
                }
            },
            "required": ["industry"]
        }


class FinancialInfoTool(BaseTool):
    """财务信息工具"""
    
    def __init__(self, retriever):
        super().__init__(
            name="get_financial_info",
            description="获取公司的财务信息，包括融资历史、估值、营收等"
        )
        self.retriever = retriever
    
    async def execute(self, company_name: str) -> Dict[str, Any]:
        """获取财务信息"""
        try:
            queries = [
                f"{company_name} 融资 投资 估值",
                f"{company_name} 营收 收入 财务报表",
                f"{company_name} 投资方 融资轮次",
                f"{company_name} 盈利 亏损 财务状况"
            ]
            
            all_results = []
            for query in queries:
                results = await self.retriever.search_multiple_sources(query)
                all_results.extend(results)
            
            financial_info = {
                "company_name": company_name,
                "funding_info": self._extract_funding_info(all_results),
                "revenue_info": self._extract_revenue_info(all_results),
                "valuation_info": self._extract_valuation_info(all_results)
            }
            
            return {
                "success": True,
                "financial_info": financial_info,
                "source_count": len(all_results)
            }
            
        except Exception as e:
            logger.error(f"Financial info tool error: {e}")
            return {
                "success": False,
                "error": str(e),
                "company_name": company_name
            }
    
    def _extract_funding_info(self, results: List[Dict[str, Any]]) -> str:
        """提取融资信息"""
        content = " ".join([r.get("content", "") for r in results])
        return content[:400]
    
    def _extract_revenue_info(self, results: List[Dict[str, Any]]) -> str:
        """提取营收信息"""
        content = " ".join([r.get("content", "") for r in results])
        return content[:400]
    
    def _extract_valuation_info(self, results: List[Dict[str, Any]]) -> str:
        """提取估值信息"""
        content = " ".join([r.get("content", "") for r in results])
        return content[:400]
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "公司名称"
                }
            },
            "required": ["company_name"]
        }


class RiskAssessmentTool(BaseTool):
    """风险评估工具"""
    
    def __init__(self, retriever):
        super().__init__(
            name="assess_risks",
            description="评估公司的各类风险，包括市场风险、竞争风险、运营风险等"
        )
        self.retriever = retriever
    
    async def execute(self, company_name: str, focus_areas: List[str] = None) -> Dict[str, Any]:
        """执行风险评估"""
        try:
            if focus_areas is None:
                focus_areas = ["市场风险", "竞争风险", "运营风险", "政策风险"]
            
            queries = [
                f"{company_name} 风险 问题 争议",
                f"{company_name} 竞争对手 威胁",
                f"{company_name} 政策 监管 合规",
                f"{company_name} 运营 管理 团队风险"
            ]
            
            all_results = []
            for query in queries:
                results = await self.retriever.search_multiple_sources(query)
                all_results.extend(results)
            
            risk_assessment = {
                "company_name": company_name,
                "risk_overview": self._assess_overall_risk(all_results),
                "specific_risks": self._identify_specific_risks(all_results),
                "mitigation_suggestions": self._suggest_mitigations(all_results)
            }
            
            return {
                "success": True,
                "risk_assessment": risk_assessment,
                "source_count": len(all_results)
            }
            
        except Exception as e:
            logger.error(f"Risk assessment tool error: {e}")
            return {
                "success": False,
                "error": str(e),
                "company_name": company_name
            }
    
    def _assess_overall_risk(self, results: List[Dict[str, Any]]) -> str:
        """评估整体风险"""
        content = " ".join([r.get("content", "") for r in results])
        return content[:400]
    
    def _identify_specific_risks(self, results: List[Dict[str, Any]]) -> str:
        """识别具体风险"""
        content = " ".join([r.get("content", "") for r in results])
        return content[:400]
    
    def _suggest_mitigations(self, results: List[Dict[str, Any]]) -> str:
        """建议风险缓解措施"""
        content = " ".join([r.get("content", "") for r in results])
        return content[:400]
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "公司名称"
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "重点关注的风险领域（可选）"
                }
            },
            "required": ["company_name"]
        }


# 新增MCP工具适配器
class MCPToolAdapter(BaseTool):
    """MCP工具适配器"""
    
    def __init__(self, tool_info: Dict[str, Any], mcp_manager):
        super().__init__(
            name=tool_info["name"],
            description=tool_info["description"]
        )
        self.tool_info = tool_info
        self.mcp_manager = mcp_manager
        self.parameters = tool_info.get("parameters", {})
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行MCP工具"""
        try:
            result = await self.mcp_manager.call_tool(self.name, kwargs)
            return result
        except Exception as e:
            logger.error(f"MCP工具 {self.name} 执行失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        """获取参数schema"""
        return self.parameters


# 新增企业数据源工具
class EnterpriseSourceTool(BaseTool):
    """企业数据源工具"""
    
    def __init__(self, enterprise_manager):
        super().__init__(
            name="query_enterprise_data",
            description="查询企业数据源信息（天眼查、爱企查等）"
        )
        self.enterprise_manager = enterprise_manager
    
    async def execute(self, company_name: str, info_type: str = "basic", 
                     preferred_sources: List[str] = None) -> Dict[str, Any]:
        """查询企业数据"""
        try:
            results = await self.enterprise_manager.query_company_info(
                company_name, info_type, preferred_sources
            )
            
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "source": result.source,
                    "success": result.success,
                    "data": result.data,
                    "timestamp": result.timestamp.isoformat()
                })
            
            return {
                "success": True,
                "results": formatted_results,
                "company_name": company_name,
                "info_type": info_type
            }
            
        except Exception as e:
            logger.error(f"企业数据源工具错误: {e}")
            return {
                "success": False,
                "error": str(e),
                "company_name": company_name
            }
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "公司名称"
                },
                "info_type": {
                    "type": "string",
                    "enum": ["basic", "financial", "legal", "investment"],
                    "description": "信息类型",
                    "default": "basic"
                },
                "preferred_sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "首选数据源列表"
                }
            },
            "required": ["company_name"]
        }


class VentureLensToolkit:
    """VentureLens工具包管理器"""
    
    def __init__(self, config: Dict[str, Any], retriever):
        self.config = config
        self.retriever = retriever
        self.tools = {}
        self.mcp_manager = None
        self.enterprise_manager = None
        self._initialize_tools()
    
    def _initialize_tools(self):
        """初始化工具"""
        self.tools = {
            "search": SearchTool(self.retriever),
            "company_info": CompanyInfoTool(self.retriever),
            "industry_analysis": IndustryAnalysisTool(self.retriever),
            "financial_info": FinancialInfoTool(self.retriever),
            "risk_assessment": RiskAssessmentTool(self.retriever)
        }
        
        # 如果有企业数据源管理器，添加企业数据源工具
        if self.enterprise_manager:
            self.tools["enterprise_data"] = EnterpriseSourceTool(self.enterprise_manager)
    
    async def initialize_external_tools(self):
        """初始化外部工具（MCP和企业数据源）"""
        try:
            # 初始化MCP管理器
            self.mcp_manager = MCPManager(self.config)
            await self.mcp_manager.initialize()
            
            # 初始化企业数据源管理器
            self.enterprise_manager = EnterpriseSourceManager(self.config)
            
            # 将MCP工具集成到工具包中
            self._integrate_mcp_tools()
            
            logger.info("外部工具初始化完成")
            
        except Exception as e:
            logger.error(f"外部工具初始化失败: {e}")
    
    def _integrate_mcp_tools(self):
        """集成MCP工具"""
        if self.mcp_manager:
            mcp_tools = self.mcp_manager.get_available_tools()
            for tool_info in mcp_tools:
                # 创建MCP工具包装器
                mcp_tool = MCPToolAdapter(tool_info, self.mcp_manager)
                self.tools[tool_info["name"]] = mcp_tool
                logger.info(f"集成MCP工具: {tool_info['name']}")
    
    async def shutdown(self):
        """关闭工具包"""
        if self.mcp_manager:
            await self.mcp_manager.shutdown()
        logger.info("工具包已关闭")
    
    def get_tools_for_agent(self, agent_type: str) -> List[BaseTool]:
        """根据Agent类型获取相应的工具"""
        tool_mappings = {
            "prescreen": ["search", "company_info", "enterprise_data"],
            "industry_dd": ["search", "industry_analysis", "company_info", "enterprise_data"],
            "team_dd": ["search", "company_info", "enterprise_data"],
            "fin_dd": ["search", "financial_info", "company_info", "enterprise_data"],
            "risk_dd": ["search", "risk_assessment", "company_info", "enterprise_data"],
            "cross_check": ["search", "company_info", "enterprise_data"]
        }
        
        tool_names = tool_mappings.get(agent_type, ["search"])
        return [self.tools[name] for name in tool_names if name in self.tools]
    
    def get_tools_openai_format(self, agent_type: str = None) -> List[Dict[str, Any]]:
        """获取OpenAI格式的工具定义"""
        if agent_type:
            tools_to_format = self.get_tools_for_agent(agent_type)
        else:
            tools_to_format = self.tools.values()
        
        return [tool.to_openai_format() for tool in tools_to_format]
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """执行指定的工具"""
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"工具 {tool_name} 不存在"
            }
        
        try:
            result = await self.tools[tool_name].execute(**kwargs)
            return result
        except Exception as e:
            logger.error(f"执行工具 {tool_name} 失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
