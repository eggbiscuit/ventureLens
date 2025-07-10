"""
示例MCP服务器实现
用于演示MCP协议的基本功能
"""

import asyncio
import json
import sys
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class ExampleMCPServer:
    """示例MCP服务器"""
    
    def __init__(self):
        self.tools = {
            "get_current_time": {
                "name": "get_current_time",
                "description": "获取当前时间",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "calculate": {
                "name": "calculate",
                "description": "执行简单的数学计算",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "数学表达式，如 '2 + 3'"
                        }
                    },
                    "required": ["expression"]
                }
            }
        }
        
        self.resources = {
            "example://text": {
                "uri": "example://text",
                "name": "示例文本",
                "description": "一个示例文本资源",
                "mimeType": "text/plain"
            }
        }
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理接收到的消息"""
        method = message.get("method")
        params = message.get("params", {})
        msg_id = message.get("id")
        
        try:
            if method == "initialize":
                return self._handle_initialize(msg_id, params)
            elif method == "tools/list":
                return self._handle_tools_list(msg_id)
            elif method == "tools/call":
                return await self._handle_tools_call(msg_id, params)
            elif method == "resources/list":
                return self._handle_resources_list(msg_id)
            elif method == "resources/read":
                return await self._handle_resources_read(msg_id, params)
            else:
                return self._error_response(msg_id, f"未知方法: {method}")
        
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            return self._error_response(msg_id, str(e))
    
    def _handle_initialize(self, msg_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理初始化请求"""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {}
                },
                "serverInfo": {
                    "name": "ExampleMCPServer",
                    "version": "1.0.0"
                }
            }
        }
    
    def _handle_tools_list(self, msg_id: int) -> Dict[str, Any]:
        """处理工具列表请求"""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": list(self.tools.values())
            }
        }
    
    async def _handle_tools_call(self, msg_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具调用请求"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            return self._error_response(msg_id, f"工具 {tool_name} 不存在")
        
        try:
            if tool_name == "get_current_time":
                from datetime import datetime
                result = datetime.now().isoformat()
                
            elif tool_name == "calculate":
                expression = arguments.get("expression", "")
                # 简单的数学计算（生产环境需要更安全的实现）
                try:
                    result = str(eval(expression))
                except:
                    result = "计算错误"
            
            else:
                result = f"工具 {tool_name} 暂未实现"
            
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result
                        }
                    ]
                }
            }
            
        except Exception as e:
            return self._error_response(msg_id, f"工具执行失败: {e}")
    
    def _handle_resources_list(self, msg_id: int) -> Dict[str, Any]:
        """处理资源列表请求"""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "resources": list(self.resources.values())
            }
        }
    
    async def _handle_resources_read(self, msg_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理资源读取请求"""
        uri = params.get("uri")
        
        if uri not in self.resources:
            return self._error_response(msg_id, f"资源 {uri} 不存在")
        
        try:
            if uri == "example://text":
                content = "这是一个示例文本资源的内容"
            else:
                content = f"资源 {uri} 的内容"
            
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "text/plain",
                            "text": content
                        }
                    ]
                }
            }
            
        except Exception as e:
            return self._error_response(msg_id, f"资源读取失败: {e}")
    
    def _error_response(self, msg_id: int, error_message: str) -> Dict[str, Any]:
        """生成错误响应"""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32000,
                "message": error_message
            }
        }

async def main():
    """主函数"""
    server = ExampleMCPServer()
    
    # 读取标准输入的消息
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline
            )
            
            if not line:
                break
            
            message = json.loads(line.strip())
            response = await server.handle_message(message)
            
            # 输出响应到标准输出
            print(json.dumps(response, ensure_ascii=False))
            sys.stdout.flush()
            
        except json.JSONDecodeError:
            continue
        except EOFError:
            break
        except Exception as e:
            logger.error(f"服务器错误: {e}")
            break

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
