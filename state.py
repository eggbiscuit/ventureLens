"""
VentureLens State Management Module

定义了投资尽职调查系统的共享状态结构
"""

from typing import TypedDict, Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SearchSource:
    """搜索来源信息"""
    query: str
    result_snippet: str
    url: str
    confidence: float = 0.7
    timestamp: datetime = field(default_factory=datetime.now)
    source_type: str = "web"  # web, api, document


class ScoreDict(TypedDict, total=False):
    """评分字典类型"""
    market_size: float
    growth_rate: float
    competition_level: float
    entry_barriers: float
    overall: float


class RationaleDict(TypedDict, total=False):
    """分析依据字典类型"""
    market_size: str
    growth_rate: str
    competition_level: str
    entry_barriers: str
    overall: str


class AgentScores(TypedDict, total=False):
    """各Agent的评分结构"""
    industry: ScoreDict
    team: ScoreDict
    financial: ScoreDict
    risk: ScoreDict
    overall: float


class AgentRationale(TypedDict, total=False):
    """各Agent的分析依据"""
    industry: RationaleDict
    team: RationaleDict
    financial: RationaleDict
    risk: RationaleDict


class VentureLensState(TypedDict):
    """VentureLens系统主状态"""
    # 基本信息
    company_name: str
    bp_file_path: Optional[str]
    run_id: str
    
    # 预筛选结果
    prescreen_passed: bool
    prescreen_reason: str
    
    # 各维度评分
    scores: AgentScores
    
    # 分析依据
    rationale: AgentRationale
    
    # 搜索来源
    sources: List[SearchSource]
    
    # BP解析结果（如果有）
    bp_extracted_data: Dict[str, Any]
    
    # 交叉验证结果
    cross_check_results: Dict[str, Any]
    
    # 流程状态
    completed_agents: List[str]
    current_agent: str
    
    # 最终报告
    final_report: Optional[str]
    
    # 元数据
    created_at: datetime
    updated_at: datetime


def create_initial_state(company_name: str, bp_file_path: Optional[str] = None, run_id: Optional[str] = None) -> VentureLensState:
    """创建初始状态"""
    import uuid
    
    if run_id is None:
        run_id = str(uuid.uuid4())
    
    now = datetime.now()
    
    return VentureLensState(
        company_name=company_name,
        bp_file_path=bp_file_path,
        run_id=run_id,
        prescreen_passed=False,
        prescreen_reason="",
        scores={},
        rationale={},
        sources=[],
        bp_extracted_data={},
        cross_check_results={},
        completed_agents=[],
        current_agent="",
        final_report=None,
        created_at=now,
        updated_at=now
    )


def update_state_timestamp(state: VentureLensState) -> VentureLensState:
    """更新状态时间戳"""
    state["updated_at"] = datetime.now()
    return state
