"""
基础Agent类定义
所有Agent都继承自这个基类，确保接口一致
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import logging
import json
from datetime import datetime

from state import VentureLensState, SearchSource, update_state_timestamp
from services.utils import MultiSourceRetriever
from services.llm_inference_simple import LLMInferenceService
from services.toolkit import VentureLensToolkit

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """基础Agent类"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.retriever = MultiSourceRetriever(config)
        self.llm_service = LLMInferenceService(config)
        self.toolkit = None  # 工具包将在workflow中设置
        
    @abstractmethod
    async def _execute(self, state: VentureLensState) -> VentureLensState:
        """执行Agent的核心逻辑"""
        pass
    
    def invoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Langchain Runnable接口实现"""
        import asyncio
        
        if isinstance(input_data, dict) and "state" in input_data:
            state = input_data["state"]
        else:
            state = input_data
            
        # 运行异步逻辑
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果已经在事件循环中，创建新任务
            task = asyncio.create_task(self._execute_wrapper(state))
            return asyncio.run_coroutine_threadsafe(task, loop).result()
        else:
            # 如果没有事件循环，直接运行
            return asyncio.run(self._execute_wrapper(state))
    
    async def _execute_wrapper(self, state: VentureLensState) -> VentureLensState:
        """执行包装器，添加通用逻辑"""
        logger.info(f"Starting {self.name} agent for company: {state['company_name']}")
        
        try:
            # 更新当前执行的Agent
            state["current_agent"] = self.name
            
            # 执行具体逻辑
            updated_state = await self._execute(state)
            
            # 标记完成
            if self.name not in updated_state["completed_agents"]:
                updated_state["completed_agents"].append(self.name)
            
            # 更新时间戳
            updated_state = update_state_timestamp(updated_state)
            
            logger.info(f"Completed {self.name} agent")
            return updated_state
            
        except Exception as e:
            logger.error(f"Error in {self.name} agent: {e}")
            # 即使出错也要更新状态
            state["current_agent"] = f"{self.name}_error"
            return update_state_timestamp(state)
    
    async def search_and_record(self, query: str, state: VentureLensState, 
                               source_types: List[str] = None) -> List[Dict[str, Any]]:
        """搜索并记录来源信息"""
        results = await self.retriever.search_multiple_sources(query, source_types)
        
        # 记录搜索来源
        for result in results:
            source = SearchSource(
                query=query,
                result_snippet=result.get("content", "")[:200],
                url=result.get("url", ""),
                confidence=result.get("score", 0.7),
                source_type=result.get("source", "web")
            )
            state["sources"].append(source)
        
        return results
    
    async def llm_analyze(self, company_name: str, aspect: str, search_results: List[Dict[str, Any]], 
                         specific_questions: List[str] = None, use_tools: bool = True) -> Dict[str, Any]:
        """使用LLM分析数据（支持工具调用）"""
        
        if use_tools and self.toolkit:
            # 获取适合当前agent的工具
            tools = self.toolkit.get_tools_for_agent(self.name)
            tool_definitions = [tool.to_openai_format() for tool in tools]
            
            # 使用工具进行分析
            analysis = await self.llm_service.analyze_with_tools(
                company_name, aspect, search_results, tool_definitions, None, specific_questions
            )
            
            # 如果LLM返回了工具调用，执行这些工具
            if isinstance(analysis, dict) and "tool_calls" in analysis:
                await self._execute_tool_calls(analysis["tool_calls"], company_name)
                
                # 重新分析（现在有了工具调用的结果）
                analysis = await self.llm_service.analyze_investment_aspect(
                    company_name, aspect, search_results, specific_questions
                )
            
            return analysis
        else:
            # 不使用工具的传统分析
            return await self.llm_service.analyze_investment_aspect(
                company_name, aspect, search_results, specific_questions
            )
    
    async def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]], company_name: str) -> None:
        """执行工具调用"""
        if not self.toolkit:
            logger.warning("工具包未初始化，无法执行工具调用")
            return
            
        for tool_call in tool_calls:
            try:
                function_name = tool_call["function"]["name"]
                arguments = json.loads(tool_call["function"]["arguments"])
                
                # 确保公司名称参数存在
                if "company_name" not in arguments:
                    arguments["company_name"] = company_name
                
                # 执行工具
                result = await self.toolkit.execute_tool(function_name, **arguments)
                
                logger.info(f"Tool {function_name} executed: {result.get('success', False)}")
                
            except Exception as e:
                logger.error(f"Error executing tool call: {e}")
    
    async def llm_analyze_with_system_message(self, 
                                            company_name: str, 
                                            aspect: str, 
                                            search_results: List[Dict[str, Any]],
                                            system_message: str,
                                            specific_questions: List[str] = None,
                                            use_tools: bool = True) -> Dict[str, Any]:
        """使用自定义system message进行LLM分析"""
        
        if use_tools:
            tools = self.toolkit.get_tools_for_agent(self.name)
            tool_definitions = [tool.to_openai_format() for tool in tools]
            return await self.llm_service.analyze_with_tools(
                company_name, aspect, search_results, tool_definitions, system_message, specific_questions
            )
        else:
            return await self.llm_service.analyze_investment_aspect(
                company_name, aspect, search_results, specific_questions
            )
    
    async def llm_analyze_with_tools(self, 
                                   company_name: str, 
                                   aspect: str, 
                                   search_results: List[Dict[str, Any]],
                                   system_message: str,
                                   tools: List[str] = None) -> Dict[str, Any]:
        """使用工具进行LLM分析的简化接口"""
        
        if tools is None:
            tools = ["search_information", "get_company_info"]
        
        # 获取工具定义
        tool_definitions = self.toolkit.get_tools_as_openai_functions(self.name)
        
        # 使用LLM服务进行工具调用分析
        return await self.llm_service.analyze_with_tools(
            company_name, aspect, search_results, tool_definitions, system_message
        )
    
    def calculate_score(self, factors: Dict[str, float], weights: Dict[str, float] = None) -> float:
        """计算加权评分"""
        if weights is None:
            # 等权重
            weights = {key: 1.0 for key in factors.keys()}
        
        total_weight = sum(weights.values())
        if total_weight == 0:
            return 0.0
        
        weighted_sum = sum(factors.get(key, 0) * weight for key, weight in weights.items())
        return min(max(weighted_sum / total_weight, 0.0), 10.0)  # 限制在0-10范围内
    
    def extract_key_info(self, search_results: List[Dict[str, Any]], keywords: List[str]) -> str:
        """从搜索结果中提取关键信息"""
        relevant_content = []
        
        for result in search_results:
            content = result.get("content", "").lower()
            title = result.get("title", "").lower()
            
            # 检查是否包含关键词
            for keyword in keywords:
                if keyword.lower() in content or keyword.lower() in title:
                    relevant_content.append(result.get("content", ""))
                    break
        
        return " ".join(relevant_content)[:1000]  # 限制长度
    
    async def execute_with_tools(self, prompt: str, system_message: str, 
                                max_iterations: int = 3) -> Dict[str, Any]:
        """使用工具执行Agent任务"""
        
        # 获取适用于当前Agent的工具
        tools = self.toolkit.get_tools_for_agent(self.name)
        tool_definitions = [tool.to_openai_format() for tool in tools]
        
        messages = [{"role": "user", "content": prompt}]
        iteration = 0
        final_result = ""
        tool_results = []
        
        while iteration < max_iterations:
            # 调用LLM
            response = await self.llm_service.call_llm_with_tools(
                messages=messages,
                tools=tool_definitions,
                system_message=system_message
            )
            
            if response.get("error"):
                break
            
            # 如果有工具调用
            if response.get("tool_calls"):
                for tool_call in response["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    try:
                        # 解析参数
                        import json
                        arguments = json.loads(tool_call["function"]["arguments"])
                        
                        # 执行工具
                        tool_result = await self._execute_tool_by_function_name(tool_name, arguments)
                        tool_results.append({
                            "tool_name": tool_name,
                            "arguments": arguments,
                            "result": tool_result
                        })
                        
                        # 添加工具结果到消息历史
                        messages.append({
                            "role": "assistant",
                            "content": f"调用工具 {tool_name}",
                            "tool_calls": [tool_call]
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": json.dumps(tool_result, ensure_ascii=False)
                        })
                        
                    except Exception as e:
                        logger.error(f"Tool execution error: {e}")
                        messages.append({
                            "role": "tool", 
                            "tool_call_id": tool_call["id"],
                            "content": f"工具执行错误: {str(e)}"
                        })
            
            # 如果有文本响应，可能是最终答案
            if response.get("content") and not response.get("tool_calls"):
                final_result = response["content"]
                break
            
            iteration += 1
        
        return {
            "final_response": final_result,
            "tool_results": tool_results,
            "iterations": iteration,
            "messages": messages
        }
    
    async def _execute_tool_by_function_name(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """根据函数名执行工具"""
        # 工具名称映射
        tool_mapping = {
            "search_information": "search",
            "get_company_info": "company_info", 
            "analyze_industry": "industry_analysis",
            "get_financial_info": "financial_info",
            "assess_risks": "risk_assessment"
        }
        
        tool_name = tool_mapping.get(function_name, function_name)
        return await self.toolkit.execute_tool(tool_name, **arguments)
