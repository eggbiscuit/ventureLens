"""
MCP工具包装器
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class MCPToolWrapper:
    """MCP工具包装器"""
    
    def __init__(self, name: str, server_name: str, tool_name: str, 
                 tool_info: Dict[str, Any], client):
        self.name = name
        self.server_name = server_name
        self.tool_name = tool_name
        self.tool_info = tool_info or {}
        self.client = client
        
        # 提取工具信息
        self.description = self.tool_info.get('description', f'MCP工具: {tool_name}')
        self.parameters = self.tool_info.get('inputSchema', {})
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        try:
            result = await self.client.call_tool(self.tool_name, arguments)
            return result
        except Exception as e:
            logger.error(f"执行MCP工具 {self.name} 失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI工具格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
    
    def __str__(self):
        return f"MCPTool({self.name}, server={self.server_name})"
