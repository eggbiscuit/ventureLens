"""
简化的LLM推理服务 - 只负责基础的LLM调用
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class LLMInferenceService:
    """简化的LLM推理服务"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get("llm", {}).get("openrouter_api_key", "") or config.get("openrouter_api_key", "")
        self.model = config.get("llm", {}).get("model", "anthropic/claude-3.5-sonnet")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.temperature = config.get("llm", {}).get("temperature", 0.1)
        self.max_tokens = config.get("llm", {}).get("max_tokens", 2000)
        self.timeout = config.get("llm", {}).get("timeout", 60)
        
    async def chat_completion(self, 
                            messages: List[Dict[str, str]], 
                            system_message: Optional[str] = None,
                            temperature: Optional[float] = None,
                            max_tokens: Optional[int] = None,
                            tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        基础聊天完成接口
        
        Args:
            messages: 消息列表
            system_message: 系统消息
            temperature: 温度参数
            max_tokens: 最大token数
            tools: 工具定义列表
        
        Returns:
            LLM响应结果
        """
        
        # 构建消息列表
        full_messages = []
        
        if system_message:
            full_messages.append({
                "role": "system",
                "content": system_message
            })
        
        full_messages.extend(messages)
        
        # 构建请求
        payload = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": False
        }
        
        # 添加工具支持
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://venturelens.ai",
            "X-Title": "VentureLens"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        choice = result["choices"][0]
                        message = choice["message"]
                        
                        return {
                            "success": True,
                            "content": message.get("content", ""),
                            "tool_calls": message.get("tool_calls", []),
                            "usage": result.get("usage", {}),
                            "model": result.get("model", self.model),
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"OpenRouter API error {response.status}: {error_text}")
                        return {
                            "success": False,
                            "error": f"API error {response.status}: {error_text}",
                            "timestamp": datetime.now().isoformat()
                        }
                        
        except asyncio.TimeoutError:
            logger.error("OpenRouter API timeout")
            return {
                "success": False,
                "error": "Request timeout",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"OpenRouter API exception: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def simple_analyze(self, prompt: str, system_message: str = None) -> Dict[str, Any]:
        """简单的文本分析接口"""
        messages = [{"role": "user", "content": prompt}]
        return await self.chat_completion(messages, system_message)
    
    def parse_json_response(self, content: str) -> Dict[str, Any]:
        """解析JSON响应"""
        try:
            # 尝试直接解析
            if content.strip().startswith('{'):
                return json.loads(content)
            
            # 尝试提取JSON部分
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            
            # 如果没有找到JSON，返回默认结构
            return {"error": "No valid JSON found", "raw_content": content}
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return {"error": f"JSON decode error: {e}", "raw_content": content}
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return {"error": f"Parse error: {e}", "raw_content": content}
