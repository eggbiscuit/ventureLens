"""
MCP客户端实现
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class MCPClient:
    """MCP协议客户端"""
    
    def __init__(self, server_config: Dict[str, Any]):
        self.server_config = server_config
        self.server_name = server_config.get('name', 'unknown')
        self.server_command = server_config.get('command', [])
        self.server_args = server_config.get('args', [])
        self.connected = False
        self.process = None
        self.tools = {}
        self.resources = {}
        
    async def connect(self) -> bool:
        """连接到MCP服务器"""
        try:
            logger.info(f"正在连接到MCP服务器: {self.server_name}")
            
            # 启动服务器进程
            self.process = await asyncio.create_subprocess_exec(
                *self.server_command,
                *self.server_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 发送初始化消息
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {}
                    },
                    "clientInfo": {
                        "name": "VentureLens",
                        "version": "1.0.0"
                    }
                }
            }
            
            await self._send_message(init_message)
            response = await self._receive_message()
            
            if response and response.get("result"):
                self.connected = True
                # 获取服务器能力
                await self._discover_capabilities()
                logger.info(f"成功连接到MCP服务器: {self.server_name}")
                return True
            else:
                logger.error(f"MCP服务器初始化失败: {response}")
                return False
                
        except Exception as e:
            logger.error(f"连接MCP服务器失败: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except:
                pass
        self.connected = False
        logger.info(f"已断开MCP服务器连接: {self.server_name}")
    
    async def _send_message(self, message: Dict[str, Any]):
        """发送消息到服务器"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP服务器未连接")
        
        message_str = json.dumps(message) + "\n"
        self.process.stdin.write(message_str.encode())
        await self.process.stdin.drain()
    
    async def _receive_message(self) -> Optional[Dict[str, Any]]:
        """接收服务器消息"""
        if not self.process or not self.process.stdout:
            return None
        
        try:
            line = await self.process.stdout.readline()
            if line:
                return json.loads(line.decode().strip())
        except Exception as e:
            logger.error(f"接收MCP消息失败: {e}")
        return None
    
    async def _discover_capabilities(self):
        """发现服务器能力"""
        try:
            # 获取工具列表
            tools_message = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            }
            
            await self._send_message(tools_message)
            tools_response = await self._receive_message()
            
            if tools_response and tools_response.get("result"):
                self.tools = {
                    tool["name"]: tool 
                    for tool in tools_response["result"].get("tools", [])
                }
                logger.info(f"发现 {len(self.tools)} 个工具")
            
            # 获取资源列表
            resources_message = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "resources/list"
            }
            
            await self._send_message(resources_message)
            resources_response = await self._receive_message()
            
            if resources_response and resources_response.get("result"):
                self.resources = {
                    resource["uri"]: resource 
                    for resource in resources_response["result"].get("resources", [])
                }
                logger.info(f"发现 {len(self.resources)} 个资源")
                
        except Exception as e:
            logger.error(f"发现服务器能力失败: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        if not self.connected:
            raise RuntimeError("MCP服务器未连接")
        
        if tool_name not in self.tools:
            raise ValueError(f"工具 {tool_name} 不存在")
        
        try:
            message = {
                "jsonrpc": "2.0",
                "id": int(datetime.now().timestamp()),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            await self._send_message(message)
            response = await self._receive_message()
            
            if response and "result" in response:
                return {
                    "success": True,
                    "result": response["result"]
                }
            else:
                return {
                    "success": False,
                    "error": response.get("error", "Unknown error")
                }
                
        except Exception as e:
            logger.error(f"调用工具 {tool_name} 失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """读取资源"""
        if not self.connected:
            raise RuntimeError("MCP服务器未连接")
        
        try:
            message = {
                "jsonrpc": "2.0",
                "id": int(datetime.now().timestamp()),
                "method": "resources/read",
                "params": {
                    "uri": uri
                }
            }
            
            await self._send_message(message)
            response = await self._receive_message()
            
            if response and "result" in response:
                return {
                    "success": True,
                    "result": response["result"]
                }
            else:
                return {
                    "success": False,
                    "error": response.get("error", "Unknown error")
                }
                
        except Exception as e:
            logger.error(f"读取资源 {uri} 失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return list(self.tools.keys())
    
    def get_available_resources(self) -> List[str]:
        """获取可用资源列表"""
        return list(self.resources.keys())
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取工具信息"""
        return self.tools.get(tool_name)
    
    def get_resource_info(self, uri: str) -> Optional[Dict[str, Any]]:
        """获取资源信息"""
        return self.resources.get(uri)
