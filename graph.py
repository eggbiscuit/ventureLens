"""
VentureLens主工作流图
使用LangGraph协调各个Agent的执行
"""

import asyncio
import logging
import json
import os
from typing import Dict, Any, List
from datetime import datetime

from state import VentureLensState, create_initial_state
from agents.prescreen import PreScreenAgent
from agents.industry_dd import IndustryDDAgent  
from agents.team_dd import TeamDDAgent
from agents.fin_dd import FinDDAgent
from agents.risk_dd import RiskDDAgent
from agents.bp_parser import BPParserAgent
from agents.cross_check import CrossCheckAgent
from report.report_generator import ReportGeneratorAgent

# 新增工具包集成
from services.toolkit import VentureLensToolkit
from services.utils import MultiSourceRetriever

logger = logging.getLogger(__name__)


class VentureLensWorkflow:
    """VentureLens工作流管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # 初始化工具包
        self.retriever = MultiSourceRetriever(config)
        self.toolkit = VentureLensToolkit(config, self.retriever)
        
        # 初始化所有Agent
        self.agents = {
            "prescreen": PreScreenAgent(config),
            "bp_parser": BPParserAgent(config),
            "industry_dd": IndustryDDAgent(config),
            "team_dd": TeamDDAgent(config),
            "fin_dd": FinDDAgent(config),
            "risk_dd": RiskDDAgent(config),
            "cross_check": CrossCheckAgent(config),
            "report_generator": ReportGeneratorAgent(config)
        }
        
        # 为每个Agent设置工具包
        for agent in self.agents.values():
            agent.toolkit = self.toolkit
        
        # 定义执行顺序
        self.execution_order = [
            "prescreen",      # 预筛选
            "bp_parser",      # BP解析（如果有BP文件）
            "industry_dd",    # 行业尽调
            "team_dd",        # 团队尽调
            "fin_dd",         # 财务尽调
            "risk_dd",        # 风险尽调
            "cross_check",    # 交叉验证
            "report_generator"  # 报告生成
        ]
        
        # 检查点配置
        self.checkpoint_enabled = config.get("checkpoints", {}).get("enabled", True)
        self.checkpoint_dir = config.get("checkpoints", {}).get("directory", "./checkpoints")
        
        if self.checkpoint_enabled:
            os.makedirs(self.checkpoint_dir, exist_ok=True)
    
    async def run(self, company_name: str, bp_file_path: str = None, run_id: str = None) -> VentureLensState:
        """运行完整的尽调流程"""
        
        # 初始化外部工具
        await self.toolkit.initialize_external_tools()
        
        # 创建或恢复状态
        if run_id and self.checkpoint_enabled:
            state = await self._load_checkpoint(run_id)
            if state:
                logger.info(f"Resumed workflow from checkpoint for run_id: {run_id}")
            else:
                state = create_initial_state(company_name, bp_file_path, run_id)
        else:
            state = create_initial_state(company_name, bp_file_path, run_id)
        
        logger.info(f"Starting VentureLens workflow for {company_name}")
        
        try:
            # 顺序执行各个Agent
            for agent_name in self.execution_order:
                # 检查是否已经完成
                if agent_name in state["completed_agents"]:
                    logger.info(f"Agent {agent_name} already completed, skipping")
                    continue
                
                # 特殊处理：如果没有BP文件，跳过BP解析
                if agent_name == "bp_parser" and not bp_file_path:
                    logger.info("No BP file provided, skipping BP parser")
                    continue
                
                # 执行Agent
                logger.info(f"Executing agent: {agent_name}")
                agent = self.agents[agent_name]
                state = await agent._execute_wrapper(state)
                
                # 保存检查点
                if self.checkpoint_enabled:
                    await self._save_checkpoint(state)
                
                # 如果预筛选未通过，提前结束
                if agent_name == "prescreen" and not state.get("prescreen_passed", False):
                    logger.info("Prescreen failed, completing workflow early")
                    # 直接跳到报告生成
                    state = await self.agents["report_generator"]._execute_wrapper(state)
                    break
            
            logger.info(f"VentureLens workflow completed for {company_name}")
            
            # 保存最终结果
            await self._save_final_result(state)
            
            return state
            
        except Exception as e:
            logger.error(f"Error in VentureLens workflow: {e}")
            raise
    
    async def _save_checkpoint(self, state: VentureLensState) -> None:
        """保存检查点"""
        if not self.checkpoint_enabled:
            return
        
        try:
            checkpoint_file = os.path.join(
                self.checkpoint_dir, 
                f"{state['run_id']}_checkpoint.json"
            )
            
            # 序列化状态（需要处理datetime等特殊类型）
            serializable_state = self._serialize_state(state)
            
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_state, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"Checkpoint saved: {checkpoint_file}")
            
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
    
    async def _load_checkpoint(self, run_id: str) -> VentureLensState:
        """加载检查点"""
        try:
            checkpoint_file = os.path.join(
                self.checkpoint_dir,
                f"{run_id}_checkpoint.json"
            )
            
            if not os.path.exists(checkpoint_file):
                return None
            
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                serializable_state = json.load(f)
            
            # 反序列化状态
            state = self._deserialize_state(serializable_state)
            
            logger.info(f"Checkpoint loaded: {checkpoint_file}")
            return state
            
        except Exception as e:
            logger.error(f"Error loading checkpoint: {e}")
            return None
    
    async def _save_final_result(self, state: VentureLensState) -> None:
        """保存最终结果"""
        try:
            # 确保输出目录存在
            output_dir = self.config.get("output", {}).get("report_directory", "./report")
            os.makedirs(output_dir, exist_ok=True)
            
            # 保存Markdown报告
            report_file = os.path.join(
                output_dir,
                f"{state['company_name']}_{state['run_id']}_report.md"
            )
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(state.get("final_report", ""))
            
            # 保存完整状态JSON
            state_file = os.path.join(
                output_dir,
                f"{state['company_name']}_{state['run_id']}_state.json"
            )
            
            serializable_state = self._serialize_state(state)
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_state, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Final results saved: {report_file}, {state_file}")
            
        except Exception as e:
            logger.error(f"Error saving final result: {e}")
    
    def _serialize_state(self, state: VentureLensState) -> Dict[str, Any]:
        """序列化状态以便JSON保存"""
        serializable = {}
        
        for key, value in state.items():
            if key in ["created_at", "updated_at"]:
                # 转换datetime为字符串
                serializable[key] = value.isoformat() if value else None
            elif key == "sources":
                # 序列化SearchSource对象
                serializable[key] = [
                    {
                        "query": source.query,
                        "result_snippet": source.result_snippet,
                        "url": source.url,
                        "confidence": source.confidence,
                        "timestamp": source.timestamp.isoformat() if source.timestamp else None,
                        "source_type": source.source_type
                    }
                    for source in value
                ]
            else:
                serializable[key] = value
        
        return serializable
    
    def _deserialize_state(self, serializable_state: Dict[str, Any]) -> VentureLensState:
        """反序列化状态"""
        from state import SearchSource
        
        state = serializable_state.copy()
        
        # 转换datetime字段
        for key in ["created_at", "updated_at"]:
            if state.get(key):
                state[key] = datetime.fromisoformat(state[key])
        
        # 转换SearchSource对象
        if "sources" in state:
            sources = []
            for source_data in state["sources"]:
                timestamp = None
                if source_data.get("timestamp"):
                    timestamp = datetime.fromisoformat(source_data["timestamp"])
                
                source = SearchSource(
                    query=source_data["query"],
                    result_snippet=source_data["result_snippet"],
                    url=source_data["url"],
                    confidence=source_data["confidence"],
                    timestamp=timestamp,
                    source_type=source_data.get("source_type", "web")
                )
                sources.append(source)
            
            state["sources"] = sources
        
        return state
    
    def get_agent_status(self, state: VentureLensState) -> Dict[str, str]:
        """获取各Agent的执行状态"""
        status = {}
        
        for agent_name in self.execution_order:
            if agent_name in state["completed_agents"]:
                status[agent_name] = "completed"
            elif agent_name == state.get("current_agent"):
                status[agent_name] = "running"
            else:
                status[agent_name] = "pending"
        
        return status
