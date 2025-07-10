"""
报告生成器Agent
汇总所有分析结果生成最终的Markdown报告
"""

import asyncio
from typing import Dict, Any, List
import logging
from datetime import datetime

from agents.base import BaseAgent
from state import VentureLensState

logger = logging.getLogger(__name__)


class ReportGeneratorAgent(BaseAgent):
    """报告生成Agent"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("report_generator", config)
        
    async def _execute(self, state: VentureLensState) -> VentureLensState:
        """生成最终报告"""
        
        company_name = state["company_name"]
        
        # 如果预筛选未通过，直接返回拒绝报告
        if not state.get("prescreen_passed", False):
            if not state.get("final_report"):
                state["final_report"] = self._generate_simple_rejection_report(
                    company_name, 
                    state.get("prescreen_reason", "未通过预筛选")
                )
            return state
        
        # 生成完整的尽调报告
        report = await self._generate_comprehensive_report(state)
        state["final_report"] = report
        
        return state
    
    def _generate_simple_rejection_report(self, company_name: str, reason: str) -> str:
        """生成简单的拒绝报告"""
        return f"""# {company_name} 投资尽职调查报告

## 总体结论：❌ 不建议投资

### 预筛选结果
{reason}

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    async def _generate_comprehensive_report(self, state: VentureLensState) -> str:
        """生成完整的尽调报告"""
        
        company_name = state["company_name"]
        scores = state.get("scores", {})
        rationale = state.get("rationale", {})
        sources = state.get("sources", [])
        bp_data = state.get("bp_extracted_data", {})
        cross_check = state.get("cross_check_results", {})
        
        # 计算总体评分
        overall_score = self._calculate_overall_score(scores)
        recommendation = self._get_investment_recommendation(overall_score)
        
        # 构建报告
        report_sections = []
        
        # 标题和概要
        report_sections.append(f"# {company_name} 投资尽职调查报告")
        report_sections.append("")
        report_sections.append(f"## 总体结论：{recommendation['emoji']} {recommendation['text']}")
        report_sections.append("")
        report_sections.append(f"**综合评分：{overall_score:.1f}/10**")
        report_sections.append("")
        report_sections.append(f"**投资建议：** {recommendation['advice']}")
        report_sections.append("")
        
        # 评分总览
        report_sections.append("## 📊 评分总览")
        report_sections.append("")
        if scores:
            report_sections.append("| 维度 | 评分 | 权重 |")
            report_sections.append("|------|------|------|")
            
            weights = {"industry": 0.3, "team": 0.25, "financial": 0.25, "risk": 0.2}
            for category, weight in weights.items():
                if category in scores and "overall" in scores[category]:
                    score = scores[category]["overall"]
                    report_sections.append(f"| {self._get_category_name(category)} | {score:.1f}/10 | {weight:.0%} |")
        
        report_sections.append("")
        
        # 详细分析
        if "industry" in scores:
            report_sections.append(self._generate_industry_section(scores["industry"], rationale.get("industry", {})))
        
        if "team" in scores:
            report_sections.append(self._generate_team_section(scores["team"], rationale.get("team", {})))
        
        if "financial" in scores:
            report_sections.append(self._generate_financial_section(scores["financial"], rationale.get("financial", {})))
        
        if "risk" in scores:
            report_sections.append(self._generate_risk_section(scores["risk"], rationale.get("risk", {})))
        
        # BP分析（如果有）
        if bp_data and not bp_data.get("error"):
            report_sections.append(self._generate_bp_section(bp_data))
        
        # 交叉验证（如果有）
        if cross_check and cross_check.get("consistency_score"):
            report_sections.append(self._generate_cross_check_section(cross_check))
        
        # 信息来源
        report_sections.append(self._generate_sources_section(sources))
        
        # 报告元信息
        report_sections.append("---")
        report_sections.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        report_sections.append(f"*分析的信息来源: {len(sources)} 个*")
        
        return "\n".join(report_sections)
    
    def _calculate_overall_score(self, scores: Dict[str, Any]) -> float:
        """计算总体评分"""
        weights = {
            "industry": 0.3,
            "team": 0.25,
            "financial": 0.25,
            "risk": 0.2
        }
        
        weighted_sum = 0
        total_weight = 0
        
        for category, weight in weights.items():
            if category in scores and "overall" in scores[category]:
                weighted_sum += scores[category]["overall"] * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return weighted_sum / total_weight
    
    def _get_investment_recommendation(self, score: float) -> Dict[str, str]:
        """根据评分获取投资建议"""
        if score >= 8.0:
            return {
                "emoji": "🎯",
                "text": "强烈推荐投资",
                "advice": "该项目展现出优秀的投资价值，建议优先考虑投资。"
            }
        elif score >= 6.5:
            return {
                "emoji": "✅",
                "text": "建议投资",
                "advice": "该项目具有良好的投资潜力，建议进一步深入尽调后投资。"
            }
        elif score >= 5.0:
            return {
                "emoji": "⚠️",
                "text": "谨慎考虑",
                "advice": "该项目存在一定风险，需要谨慎评估后决定是否投资。"
            }
        else:
            return {
                "emoji": "❌",
                "text": "不建议投资",
                "advice": "该项目风险较高或投资价值不明确，不建议投资。"
            }
    
    def _get_category_name(self, category: str) -> str:
        """获取类别中文名称"""
        names = {
            "industry": "行业分析",
            "team": "团队分析", 
            "financial": "财务分析",
            "risk": "风险分析"
        }
        return names.get(category, category)
    
    def _generate_industry_section(self, scores: Dict[str, float], rationale: Dict[str, str]) -> str:
        """生成行业分析章节"""
        section = ["## 🏭 行业分析", ""]
        
        if "overall" in scores:
            section.append(f"**综合评分：{scores['overall']:.1f}/10**")
            section.append("")
        
        # 细分评分
        if len(scores) > 1:
            section.append("### 细分评分")
            for key, score in scores.items():
                if key != "overall":
                    name = self._get_metric_name("industry", key)
                    section.append(f"- **{name}：** {score:.1f}/10")
            section.append("")
        
        # 分析依据
        section.append("### 分析依据")
        for key, analysis in rationale.items():
            if key != "overall" and analysis:
                name = self._get_metric_name("industry", key)
                section.append(f"**{name}：** {analysis}")
                section.append("")
        
        return "\n".join(section)
    
    def _generate_team_section(self, scores: Dict[str, float], rationale: Dict[str, str]) -> str:
        """生成团队分析章节"""
        section = ["## 👥 团队分析", ""]
        
        if "overall" in scores:
            section.append(f"**综合评分：{scores['overall']:.1f}/10**")
            section.append("")
        
        # 细分评分
        if len(scores) > 1:
            section.append("### 细分评分")
            for key, score in scores.items():
                if key != "overall":
                    name = self._get_metric_name("team", key)
                    section.append(f"- **{name}：** {score:.1f}/10")
            section.append("")
        
        # 分析依据
        section.append("### 分析依据")
        for key, analysis in rationale.items():
            if key != "overall" and analysis:
                name = self._get_metric_name("team", key)
                section.append(f"**{name}：** {analysis}")
                section.append("")
        
        return "\n".join(section)
    
    def _generate_financial_section(self, scores: Dict[str, float], rationale: Dict[str, str]) -> str:
        """生成财务分析章节"""
        section = ["## 💰 财务分析", ""]
        
        if "overall" in scores:
            section.append(f"**综合评分：{scores['overall']:.1f}/10**")
            section.append("")
        
        # 细分评分
        if len(scores) > 1:
            section.append("### 细分评分")
            for key, score in scores.items():
                if key != "overall":
                    name = self._get_metric_name("financial", key)
                    section.append(f"- **{name}：** {score:.1f}/10")
            section.append("")
        
        # 分析依据
        section.append("### 分析依据")
        for key, analysis in rationale.items():
            if key != "overall" and analysis:
                name = self._get_metric_name("financial", key)
                section.append(f"**{name}：** {analysis}")
                section.append("")
        
        return "\n".join(section)
    
    def _generate_risk_section(self, scores: Dict[str, float], rationale: Dict[str, str]) -> str:
        """生成风险分析章节"""
        section = ["## ⚠️ 风险分析", ""]
        
        if "overall" in scores:
            section.append(f"**综合评分：{scores['overall']:.1f}/10** (分数越高风险越低)")
            section.append("")
        
        # 细分评分
        if len(scores) > 1:
            section.append("### 细分评分")
            for key, score in scores.items():
                if key != "overall":
                    name = self._get_metric_name("risk", key)
                    section.append(f"- **{name}：** {score:.1f}/10")
            section.append("")
        
        # 分析依据
        section.append("### 分析依据")
        for key, analysis in rationale.items():
            if key != "overall" and analysis:
                name = self._get_metric_name("risk", key)
                section.append(f"**{name}：** {analysis}")
                section.append("")
        
        return "\n".join(section)
    
    def _generate_bp_section(self, bp_data: Dict[str, Any]) -> str:
        """生成BP分析章节"""
        section = ["## 📋 商业计划书分析", ""]
        
        if "company_info" in bp_data:
            company_info = bp_data["company_info"]
            section.append("### 公司基本信息")
            for key, value in company_info.items():
                if value:
                    section.append(f"- **{key}：** {value}")
            section.append("")
        
        if "financial_info" in bp_data:
            financial_info = bp_data["financial_info"]
            section.append("### 财务信息")
            for key, value in financial_info.items():
                if value:
                    section.append(f"- **{key}：** {value}")
            section.append("")
        
        return "\n".join(section)
    
    def _generate_cross_check_section(self, cross_check: Dict[str, Any]) -> str:
        """生成交叉验证章节"""
        section = ["## 🔍 信息交叉验证", ""]
        
        consistency_score = cross_check.get("consistency_score", 0)
        section.append(f"**一致性评分：{consistency_score:.1f}/10**")
        section.append("")
        
        if cross_check.get("major_discrepancies"):
            section.append("### 主要差异点")
            for discrepancy in cross_check["major_discrepancies"]:
                section.append(f"- {discrepancy}")
            section.append("")
        
        if cross_check.get("verified_facts"):
            section.append("### 已验证事实")
            for fact in cross_check["verified_facts"]:
                section.append(f"- ✅ {fact}")
            section.append("")
        
        return "\n".join(section)
    
    def _generate_sources_section(self, sources: List[Any]) -> str:
        """生成信息来源章节"""
        section = ["## 📚 信息来源", ""]
        
        if not sources:
            section.append("无外部信息来源")
            return "\n".join(section)
        
        # 按查询分组
        queries = {}
        for source in sources:
            query = source.query
            if query not in queries:
                queries[query] = []
            queries[query].append(source)
        
        for query, query_sources in queries.items():
            section.append(f"### {query}")
            for i, source in enumerate(query_sources[:3], 1):  # 限制每个查询最多3个来源
                section.append(f"{i}. [{source.url}]({source.url}) (置信度: {source.confidence:.1f})")
            section.append("")
        
        return "\n".join(section)
    
    def _get_metric_name(self, category: str, metric: str) -> str:
        """获取指标中文名称"""
        names = {
            "industry": {
                "market_size": "市场规模",
                "growth_rate": "增长率",
                "competition_level": "竞争水平",
                "entry_barriers": "准入门槛"
            },
            "team": {
                "founder_background": "创始人背景",
                "team_experience": "团队经验",
                "past_achievements": "过往成就",
                "team_completeness": "团队完整性"
            },
            "financial": {
                "revenue_status": "营收状况",
                "profitability": "盈利能力",
                "funding_history": "融资历史",
                "financial_health": "财务健康度"
            },
            "risk": {
                "market_risk": "市场风险",
                "competition_risk": "竞争风险",
                "operational_risk": "运营风险",
                "regulatory_risk": "政策风险"
            }
        }
        
        return names.get(category, {}).get(metric, metric)
