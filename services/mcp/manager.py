"""
MCP管理器
管理多个MCP服务器连接和工具调用
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .client import MCPClient
from .tools import MCPToolWrapper
from .resources import MCPResourceWrapper

logger = logging.getLogger(__name__)

class MCPManager:
    """MCP管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.clients: Dict[str, MCPClient] = {}
        self.tools: Dict[str, MCPToolWrapper] = {}
        self.resources: Dict[str, MCPResourceWrapper] = {}
        
    async def initialize(self):
        """初始化所有MCP连接"""
        mcp_config = self.config.get('mcp', {})
        servers = mcp_config.get('servers', {})
        
        for server_name, server_config in servers.items():
            if not server_config.get('enabled', False):
                continue
            
            client = MCPClient(server_config)
            if await client.connect():
                self.clients[server_name] = client
                await self._register_server_capabilities(server_name, client)
                logger.info(f"MCP服务器 {server_name} 初始化成功")
            else:
                logger.error(f"MCP服务器 {server_name} 初始化失败")
    
    async def _register_server_capabilities(self, server_name: str, client: MCPClient):
        """注册服务器能力"""
        # 注册工具
        for tool_name in client.get_available_tools():
            tool_info = client.get_tool_info(tool_name)
            wrapper = MCPToolWrapper(
                name=f"{server_name}_{tool_name}",
                server_name=server_name,
                tool_name=tool_name,
                tool_info=tool_info,
                client=client
            )
            self.tools[wrapper.name] = wrapper
        
        # 注册资源
        for resource_uri in client.get_available_resources():
            resource_info = client.get_resource_info(resource_uri)
            wrapper = MCPResourceWrapper(
                uri=resource_uri,
                server_name=server_name,
                resource_info=resource_info,
                client=client
            )
            self.resources[resource_uri] = wrapper
    
    async def shutdown(self):
        """关闭所有连接"""
        for client in self.clients.values():
            await client.disconnect()
        
        self.clients.clear()
        self.tools.clear()
        self.resources.clear()
        logger.info("所有MCP连接已关闭")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"工具 {tool_name} 不存在"
            }
        
        try:
            result = await self.tools[tool_name].execute(arguments)
            return result
        except Exception as e:
            logger.error(f"调用工具 {tool_name} 失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """读取资源"""
        if uri not in self.resources:
            return {
                "success": False,
                "error": f"资源 {uri} 不存在"
            }
        
        try:
            result = await self.resources[uri].read()
            return result
        except Exception as e:
            logger.error(f"读取资源 {uri} 失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取所有可用工具"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "server": tool.server_name,
                "parameters": tool.parameters
            }
            for tool in self.tools.values()
        ]
    
    def get_available_resources(self) -> List[Dict[str, Any]]:
        """获取所有可用资源"""
        return [
            {
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "server": resource.server_name,
                "mimeType": resource.mime_type
            }
            for resource in self.resources.values()
        ]
    
    def get_tools_for_openai(self) -> List[Dict[str, Any]]:
        """获取OpenAI格式的工具定义"""
        return [tool.to_openai_format() for tool in self.tools.values()]
    
    def is_tool_available(self, tool_name: str) -> bool:
        """检查工具是否可用"""
        return tool_name in self.tools
    
    def is_resource_available(self, uri: str) -> bool:
        """检查资源是否可用"""
        return uri in self.resources
    
    async def health_check(self) -> Dict[str, bool]:
        """健康检查"""
        results = {}
        
        for server_name, client in self.clients.items():
            try:
                # 简单的连接检查
                results[server_name] = client.connected
            except Exception as e:
                logger.error(f"MCP服务器 {server_name} 健康检查失败: {e}")
                results[server_name] = False
        
        return results
    
    async def refresh_capabilities(self):
        """刷新所有服务器能力"""
        for server_name, client in self.clients.items():
            try:
                await client._discover_capabilities()
                # 重新注册能力
                # 清理旧的工具和资源
                old_tools = [k for k in self.tools.keys() if k.startswith(f"{server_name}_")]
                old_resources = [k for k in self.resources.keys() if k.startswith(f"{server_name}_")]
                
                for tool_name in old_tools:
                    del self.tools[tool_name]
                for resource_uri in old_resources:
                    del self.resources[resource_uri]
                
                # 重新注册
                await self._register_server_capabilities(server_name, client)
                logger.info(f"已刷新MCP服务器 {server_name} 的能力")
                
            except Exception as e:
                logger.error(f"刷新MCP服务器 {server_name} 能力失败: {e}")
