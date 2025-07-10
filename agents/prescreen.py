"""
预筛选Agent
判断公司是否具有基本投资价值
"""

import asyncio
from typing import Dict, Any, List
import logging
import json
from datetime import datetime

from agents.base import BaseAgent
from state import VentureLensState

logger = logging.getLogger(__name__)


class PreScreenAgent(BaseAgent):
    """预筛选Agent - 判断公司基本投资价值"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("prescreen", config)
        
    async def _execute(self, state: VentureLensState) -> VentureLensState:
        """执行预筛选逻辑"""
        company_name = state["company_name"]
        logger.info(f"开始预筛选分析：{company_name}")
        
        try:
            # 1. 搜索公司基本信息
            search_results = await self._search_company_info(company_name, state)
            
            # 2. 使用LLM进行分析
            analysis_result = await self._analyze_with_llm(company_name, search_results)
            
            # 3. 更新状态
            self._update_state(state, analysis_result)
            
            logger.info(f"预筛选完成，结果: {'通过' if state.get('prescreen_passed') else '未通过'}")
            
        except Exception as e:
            logger.error(f"预筛选分析失败: {e}")
            self._set_default_result(state, company_name, str(e))
        
        return state
    
    async def _search_company_info(self, company_name: str, state: VentureLensState) -> List[Dict[str, Any]]:
        """搜索公司信息"""
        # 基础查询
        base_queries = [
            f"{company_name} 公司 基本信息",
            f"{company_name} 业务 产品 服务",
            f"{company_name} 融资 投资 估值",
            f"{company_name} 风险 争议 问题"
        ]
        
        # 扩展查询（适用于小公司或信息稀缺场景）
        extended_queries = [
            f"{company_name} 成立时间 注册资本",
            f"{company_name} 创始人 团队",
            f"{company_name} 官网 联系方式",
            f"{company_name} 新闻 动态",
            f"{company_name} 竞争对手 行业地位",
            f"{company_name} 专利 技术",
        ]
        
        all_results = []
        
        # 执行基础搜索
        for query in base_queries:
            try:
                results = await self.search_and_record(query, state)
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"基础搜索失败 {query}: {e}")
        
        # 如果基础搜索结果不足，执行扩展搜索
        if len(all_results) < 10:
            logger.info(f"基础搜索结果不足({len(all_results)}条)，执行扩展搜索...")
            for query in extended_queries[:3]:  # 限制扩展搜索数量
                try:
                    results = await self.search_and_record(query, state)
                    all_results.extend(results)
                    if len(all_results) >= 15:  # 达到目标数量就停止
                        break
                except Exception as e:
                    logger.warning(f"扩展搜索失败 {query}: {e}")
        
        logger.info(f"搜索到 {len(all_results)} 条信息")
        return all_results
    
    async def _analyze_with_llm(self, company_name: str, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """使用LLM分析公司信息"""
        
        # 构建prompt
        prompt = self._build_analysis_prompt(company_name, search_results)
        
        # 系统消息
        system_message = f"""你是一位经验丰富的投资顾问，负责对公司进行专业的投资预筛选。

你的任务是基于搜索到的信息，判断公司 "{company_name}" 是否值得进一步尽职调查。

评估框架：
1. **公司真实性与合规性**：
   - 是否为合法注册的真实公司
   - 有无实际业务运营
   - 是否存在重大违法违规记录

2. **基本投资价值**：
   - 业务模式是否清晰可行
   - 市场规模和增长潜力
   - 竞争优势和差异化
   - 财务状况和盈利能力

3. **风险评估**：
   - 法律纠纷和争议
   - 行业风险和政策风险
   - 团队稳定性
   - 资金链状况

4. **信息质量评估**：
   - 信息来源的可信度
   - 信息的完整性和时效性
   - 是否存在相互矛盾的信息

请基于以上框架进行客观、专业的分析，并严格按照JSON格式回复。
对于信息不足的情况，可以谨慎通过，由后续Agent进行更深入的调查。"""
        
        try:
            # 调用LLM
            response = await self.llm_service.simple_analyze(prompt, system_message)
            
            if response.get("success"):
                # 解析JSON响应
                content = response.get("content", "")
                parsed_result = self.llm_service.parse_json_response(content)
                
                if "error" not in parsed_result:
                    return parsed_result
                else:
                    logger.warning(f"LLM响应解析失败: {parsed_result}")
                    return self._create_default_analysis(company_name, "响应解析失败")
            else:
                logger.error(f"LLM调用失败: {response.get('error')}")
                return self._create_default_analysis(company_name, response.get('error', '未知错误'))
                
        except Exception as e:
            logger.error(f"LLM分析异常: {e}")
            return self._create_default_analysis(company_name, str(e))
    
    def _build_analysis_prompt(self, company_name: str, search_results: List[Dict[str, Any]]) -> str:
        """构建分析prompt"""
        
        # 整理搜索结果
        search_content = "\n".join([
            f"来源: {result.get('url', 'unknown')}\n"
            f"标题: {result.get('title', '')}\n"
            f"内容: {result.get('content', '')[:300]}...\n"
            f"---"
            for result in search_results[:10]  # 限制数量
        ])
        
        if not search_content.strip():
            search_content = "未找到相关信息"
        
        return f"""请对公司 "{company_name}" 进行投资预筛选分析。

基于以下搜索信息：
{search_content}

请从以下角度进行评估：

**1. 公司真实性与合规性**
- 公司是否合法注册并实际运营
- 基本工商信息是否完整
- 是否存在违法违规记录

**2. 基本投资价值**
- 业务模式和主营业务是否清晰
- 所在行业的市场前景如何
- 公司是否具备核心竞争优势
- 财务状况和盈利能力

**3. 风险信号识别**
- 是否存在法律纠纷、违规行为
- 经营风险和行业风险
- 团队稳定性和资金状况
- 负面新闻和争议事件

**4. 信息质量评估**
- 搜索到的信息是否充分、可信
- 信息来源的权威性
- 信息的时效性和一致性

请以以下JSON格式严格回复：
{{
    "passed": true/false,
    "confidence": 0.0-1.0,
    "reason": "详细的判断理由（150字以内）",
    "positive_factors": ["积极因素1", "积极因素2", "积极因素3"],
    "negative_factors": ["风险因素1", "风险因素2"],
    "information_quality": "high/medium/low",
    "recommendation": "具体投资建议（80字以内）",
    "key_findings": {{
        "business_model": "业务模式描述",
        "market_position": "市场地位评估", 
        "financial_health": "财务健康度",
        "risk_level": "low/medium/high"
    }}
}}

注意：
- passed字段决定是否继续后续分析
- confidence表示判断的可信度（0.0-1.0）
- 对于知名大公司，confidence应该较高
- 对于信息不足的小公司，可以谨慎通过，由后续Agent深入调查"""
    
    def _update_state(self, state: VentureLensState, analysis: Dict[str, Any]) -> None:
        """更新状态"""
        
        # 设置预筛选结果
        state["prescreen_passed"] = analysis.get("passed", False)
        state["prescreen_reason"] = analysis.get("reason", "未提供具体理由")
        state["prescreen_confidence"] = analysis.get("confidence", 0.5)
        
        # 设置评分和分析依据
        if "scores" not in state:
            state["scores"] = {}
        if "rationale" not in state:
            state["rationale"] = {}
        
        state["scores"]["prescreen"] = {
            "overall": 8.0 if analysis.get("passed") else 3.0,
            "confidence": analysis.get("confidence", 0.5)
        }
        
        state["rationale"]["prescreen"] = {
            "reason": analysis.get("reason", ""),
            "positive_factors": analysis.get("positive_factors", []),
            "negative_factors": analysis.get("negative_factors", []),
            "information_quality": analysis.get("information_quality", "medium"),
            "recommendation": analysis.get("recommendation", ""),
            "key_findings": analysis.get("key_findings", {})
        }
        
        # 如果未通过预筛选，生成拒绝报告
        if not analysis.get("passed", False):
            state["final_report"] = self._generate_rejection_report(
                state["company_name"], 
                analysis.get("reason", "未通过预筛选"), 
                analysis
            )
    
    def _set_default_result(self, state: VentureLensState, company_name: str, error_msg: str) -> None:
        """设置默认结果"""
        state["prescreen_passed"] = False
        state["prescreen_reason"] = f"分析过程出错: {error_msg}"
        state["prescreen_confidence"] = 0.3
        
        if "scores" not in state:
            state["scores"] = {}
        if "rationale" not in state:
            state["rationale"] = {}
        
        state["scores"]["prescreen"] = {
            "overall": 3.0,
            "confidence": 0.3
        }
        
        state["rationale"]["prescreen"] = {
            "reason": f"无法完成对{company_name}的预筛选分析",
            "positive_factors": [],
            "negative_factors": ["分析过程出现技术问题"],
            "information_quality": "low",
            "recommendation": "建议重新分析或寻找更多信息来源"
        }
    
    def _create_default_analysis(self, company_name: str, error_reason: str) -> Dict[str, Any]:
        """创建默认分析结果"""
        return {
            "passed": False,
            "confidence": 0.3,
            "reason": f"无法完成分析: {error_reason}",
            "positive_factors": [],
            "negative_factors": ["信息不足", "分析过程出现问题"],
            "information_quality": "low",
            "recommendation": f"建议重新搜索{company_name}的更多信息后再次评估"
        }
    
    def _generate_rejection_report(self, company_name: str, reason: str, analysis: Dict[str, Any] = None) -> str:
        """生成拒绝报告"""
        positive_factors = analysis.get("positive_factors", []) if analysis else []
        negative_factors = analysis.get("negative_factors", []) if analysis else []
        confidence = analysis.get("confidence", 0.0) if analysis else 0.0
        
        positive_section = ""
        if positive_factors:
            positive_section = f"""
### 发现的积极因素
{chr(10).join([f"- {factor}" for factor in positive_factors])}
"""
        
        negative_section = ""
        if negative_factors:
            negative_section = f"""
### 发现的风险因素
{chr(10).join([f"- {factor}" for factor in negative_factors])}
"""
        
        return f"""# {company_name} 投资尽职调查报告

## 预筛选结果：❌ 未通过

### 拒绝原因
{reason}

### 分析可信度
{confidence:.1%}
{positive_section}{negative_section}
### 建议
不建议进行进一步的尽职调查投入。建议：
1. 重新核实公司信息的准确性
2. 寻找更多可靠的信息来源
3. 考虑其他投资标的

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
