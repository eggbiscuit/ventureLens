"""
MCP资源包装器
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class MCPResourceWrapper:
    """MCP资源包装器"""
    
    def __init__(self, uri: str, server_name: str, resource_info: Dict[str, Any], client):
        self.uri = uri
        self.server_name = server_name
        self.resource_info = resource_info or {}
        self.client = client
        
        # 提取资源信息
        self.name = self.resource_info.get('name', uri)
        self.description = self.resource_info.get('description', f'MCP资源: {uri}')
        self.mime_type = self.resource_info.get('mimeType', 'text/plain')
    
    async def read(self) -> Dict[str, Any]:
        """读取资源"""
        try:
            result = await self.client.read_resource(self.uri)
            return result
        except Exception as e:
            logger.error(f"读取MCP资源 {self.uri} 失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def __str__(self):
        return f"MCPResource({self.uri}, server={self.server_name})"
