"""
LLM推理服务模块 - 使用OpenRouter API
简化版本，主要用于向后兼容
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from services.llm_inference_simple import LLMInferenceService as SimpleLLMService

logger = logging.getLogger(__name__)


class LLMInferenceService:
    """LLM推理服务 - 向后兼容包装器，内部使用简化版本"""
    
    def __init__(self, config: Dict[str, Any]):
        # 使用简化版本的LLM服务
        self.simple_service = SimpleLLMService(config)
        self.config = config
        self.api_key = config.get("llm", {}).get("openrouter_api_key", "")
        self.model = config.get("llm", {}).get("model", "anthropic/claude-3.5-sonnet")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.temperature = config.get("llm", {}).get("temperature", 0.1)
        self.max_tokens = config.get("llm", {}).get("max_tokens", 2000)
        self.timeout = config.get("llm", {}).get("timeout", 60)
        
    async def chat_completion(self, 
                            messages: List[Dict[str, str]], 
                            system_message: Optional[str] = None,
                            temperature: Optional[float] = None,
                            max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        基础聊天完成接口 - 委托给简化版本
        """
        return await self.simple_service.chat_completion(
            messages=messages,
            system_message=system_message,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    async def simple_analyze(self, prompt: str, system_message: str = None) -> Dict[str, Any]:
        """简单的文本分析接口 - 委托给简化版本"""
        return await self.simple_service.simple_analyze(prompt, system_message)
    
    def parse_json_response(self, content: str) -> Dict[str, Any]:
        """解析JSON响应 - 委托给简化版本"""
        return self.simple_service.parse_json_response(content)
    
    async def call_llm_with_tools(self, 
                                  messages: List[Dict[str, str]], 
                                  tools: Optional[List[Dict[str, Any]]] = None,
                                  system_message: Optional[str] = None) -> Dict[str, Any]:
        """调用LLM并支持工具调用 - 委托给简化版本"""
        return await self.simple_service.chat_completion(
            messages=messages,
            system_message=system_message,
            tools=tools
        )
    
    # 为了向后兼容，保留一些旧的方法签名，但内部简化实现
    async def analyze_with_tools(self, 
                                company_name: str,
                                aspect: str, 
                                search_results: List[Dict[str, Any]], 
                                tools: List[Dict[str, Any]] = None,
                                system_message: str = None,
                                specific_questions: List[str] = None) -> Dict[str, Any]:
        """向后兼容的分析方法 - 已废弃，建议使用Agent内部的分析逻辑"""
        logger.warning("analyze_with_tools方法已废弃，建议Agent直接使用simple_analyze")
        
        # 构建简化的prompt
        search_content = "\n".join([
            f"来源: {result.get('url', 'unknown')}\n标题: {result.get('title', '')}\n内容: {result.get('content', '')}\n"
            for result in search_results[:5]
        ])
        
        prompt = f"请对公司 {company_name} 进行{aspect}分析。\n\n搜索信息：\n{search_content}"
        
        if specific_questions:
            questions_text = "\n".join([f"- {q}" for q in specific_questions])
            prompt += f"\n\n特别关注：\n{questions_text}"
        
        # 使用简化服务
        response = await self.simple_service.simple_analyze(prompt, system_message)
        
        if response.get("success"):
            return self.simple_service.parse_json_response(response["content"])
        else:
            return {
                "scores": {"overall": 5.0},
                "rationale": {"overall": f"分析失败: {response.get('error', 'Unknown error')}"},
                "confidence": 0.3
            }
    
    async def generate_cross_check_analysis(self, 
                                          bp_data: Dict[str, Any], 
                                          external_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成交叉验证分析"""
        prompt = f"""
请对以下BP信息和外部调研信息进行交叉验证分析：

BP中的信息：
{json.dumps(bp_data, ensure_ascii=False, indent=2)}

外部调研信息：
{json.dumps(external_data, ensure_ascii=False, indent=2)}

请分析信息的一致性，识别差异点，并评估信息的可信度。

请以以下JSON格式回复：
{{
    "consistency_score": 7.5,
    "major_discrepancies": ["差异点1", "差异点2"], 
    "verified_facts": ["已验证的事实1", "已验证的事实2"],
    "unverified_claims": ["未验证的声明1", "未验证的声明2"],
    "credibility_assessment": "整体可信度评估",
    "recommendations": ["建议1", "建议2"]
}}
"""
        
        try:
            response = await self.simple_service.simple_analyze(prompt)
            if response.get("success"):
                return self.simple_service.parse_json_response(response["content"])
            else:
                raise Exception(response.get("error", "Unknown error"))
        except Exception as e:
            logger.error(f"Cross-check analysis error: {e}")
            return {
                "consistency_score": 5.0,
                "major_discrepancies": [],
                "verified_facts": [],
                "unverified_claims": [],
                "credibility_assessment": f"分析错误: {str(e)}",
                "recommendations": []
            }
    
    def _build_tool_analysis_prompt(self, 
                                  company_name: str,
                                  aspect: str, 
                                  search_results: List[Dict[str, Any]], 
                                  specific_questions: List[str] = None,
                                  system_message: str = None) -> str:
        """构建支持工具的分析提示词"""
        
        # 整理搜索结果
        search_content = "\n".join([
            f"来源: {result.get('url', 'unknown')}\n标题: {result.get('title', '')}\n内容: {result.get('content', '')}\n"
            for result in search_results[:8]  # 限制数量
        ])
        
        base_prompt = f"""
请对公司 "{company_name}" 进行{aspect}分析。

已有的搜索信息：
{search_content}

你可以使用提供的工具来获取更多相关信息，然后进行分析。
"""
        
        if system_message:
            base_prompt = f"{system_message}\n\n{base_prompt}"
        
        if specific_questions:
            questions_text = "\n".join([f"- {q}" for q in specific_questions])
            base_prompt += f"\n请特别关注以下问题：\n{questions_text}\n"
        
        if aspect == "prescreen":
            base_prompt += self._get_prescreen_instructions()
        elif aspect == "industry":
            base_prompt += self._get_industry_instructions()
        elif aspect == "team":
            base_prompt += self._get_team_instructions()
        elif aspect == "financial":
            base_prompt += self._get_financial_instructions()
        elif aspect == "risk":
            base_prompt += self._get_risk_instructions()
        
        base_prompt += """

请先使用可用的工具收集必要的信息，然后基于收集到的所有信息进行分析。
最终请以JSON格式返回分析结果。
"""
        
        return base_prompt
    
    def _get_prescreen_instructions(self) -> str:
        """获取预筛选指令"""
        return """
请分析以下几个方面：
1. 公司是否真实存在且有实际业务
2. 是否存在重大负面信息（违法、诈骗、重大争议等）
3. 是否具备基本的投资价值指标
4. 信息的可信度和完整性

建议使用工具搜索公司基本信息和风险评估。

请以以下JSON格式回复：
{
    "passed": true/false,
    "confidence": 0.0-1.0,
    "reason": "详细的分析理由",
    "positive_factors": ["积极因素1", "积极因素2"],
    "negative_factors": ["风险因素1", "风险因素2"],
    "recommendation": "是否建议继续尽调"
}
"""
    
    def _get_industry_instructions(self) -> str:
        """获取行业分析指令"""
        return """
请从以下四个维度进行评分（0-10分）：
1. 市场规模 (market_size): 目标市场的规模大小
2. 增长率 (growth_rate): 行业的增长速度和发展趋势  
3. 竞争水平 (competition_level): 市场竞争的激烈程度（分数越高表示竞争越适中）
4. 准入门槛 (entry_barriers): 行业准入的技术和监管门槛

建议使用行业分析工具获取更详细的行业数据。

请以以下JSON格式回复：
{
    "scores": {
        "market_size": 7.5,
        "growth_rate": 8.0,
        "competition_level": 6.5,
        "entry_barriers": 7.0,
        "overall": 7.25
    },
    "rationale": {
        "market_size": "市场规模分析依据",
        "growth_rate": "增长率分析依据",
        "competition_level": "竞争水平分析依据", 
        "entry_barriers": "准入门槛分析依据",
        "overall": "综合评价"
    },
    "industry_identified": "识别出的具体行业",
    "confidence": 0.8
}
"""
    
    def _get_team_instructions(self) -> str:
        """获取团队分析指令"""
        return """
请从以下四个维度进行评分（0-10分）：
1. 创始人背景 (founder_background): 创始人的教育背景、工作经历、行业经验
2. 团队经验 (team_experience): 核心团队的相关经验和专业能力
3. 过往成就 (past_achievements): 团队或创始人的历史成就和成功案例
4. 团队完整性 (team_completeness): 团队结构是否完整，关键岗位是否齐备

建议使用团队调研工具获取更详细的团队信息。

请以以下JSON格式回复：
{
    "scores": {
        "founder_background": 7.5,
        "team_experience": 8.0,
        "past_achievements": 6.5,
        "team_completeness": 7.0,
        "overall": 7.25
    },
    "rationale": {
        "founder_background": "创始人背景分析",
        "team_experience": "团队经验分析",
        "past_achievements": "过往成就分析",
        "team_completeness": "团队完整性分析",
        "overall": "团队综合评价"
    },
    "key_people": ["识别出的关键人员"],
    "confidence": 0.8
}
"""
    
    def _get_financial_instructions(self) -> str:
        """获取财务分析指令"""
        return """
请从以下四个维度进行评分（0-10分）：
1. 营收状况 (revenue_status): 营收规模、增长趋势、商业模式清晰度
2. 盈利能力 (profitability): 盈利状况、利润率、成本控制
3. 融资历史 (funding_history): 融资轮次、估值、投资方质量
4. 财务健康度 (financial_health): 现金流、负债率、财务可持续性

建议使用财务数据工具获取更详细的财务信息。

请以以下JSON格式回复：
{
    "scores": {
        "revenue_status": 7.5,
        "profitability": 6.0,
        "funding_history": 8.0,
        "financial_health": 7.0,
        "overall": 7.1
    },
    "rationale": {
        "revenue_status": "营收状况分析",
        "profitability": "盈利能力分析", 
        "funding_history": "融资历史分析",
        "financial_health": "财务健康度分析",
        "overall": "财务综合评价"
    },
    "key_metrics": {
        "latest_valuation": "最新估值",
        "revenue_growth": "营收增长率",
        "funding_rounds": "融资轮次"
    },
    "confidence": 0.8
}
"""
    
    def _get_risk_instructions(self) -> str:
        """获取风险分析指令"""
        return """
请从以下四个维度进行评分（0-10分，分数越高表示风险越低）：
1. 市场风险 (market_risk): 市场变化、需求波动、技术替代风险
2. 竞争风险 (competition_risk): 竞争对手威胁、市场份额风险
3. 运营风险 (operational_risk): 团队风险、执行风险、供应链风险
4. 政策风险 (regulatory_risk): 监管变化、政策风险、合规风险

建议使用风险评估工具获取更全面的风险信息。

请以以下JSON格式回复：
{
    "scores": {
        "market_risk": 7.0,
        "competition_risk": 6.5,
        "operational_risk": 7.5,
        "regulatory_risk": 8.0,
        "overall": 7.25
    },
    "rationale": {
        "market_risk": "市场风险分析",
        "competition_risk": "竞争风险分析",
        "operational_risk": "运营风险分析", 
        "regulatory_risk": "政策风险分析",
        "overall": "风险综合评价"
    },
    "major_risks": ["主要风险点1", "主要风险点2"],
    "mitigation_suggestions": ["风险缓解建议1", "风险缓解建议2"],
    "confidence": 0.8
}
"""
    
    async def _call_llm(self, prompt: str) -> str:
        """调用OpenRouter API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://venturelens.ai",  # OpenRouter要求
            "X-Title": "VentureLens"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位专业的投资分析师，擅长对初创公司进行尽职调查分析。请基于提供的信息进行客观、专业的分析，并给出结构化的评分和分析依据。"
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenRouter API error {response.status}: {error_text}")
    
    def _build_analysis_prompt(self, 
                             company_name: str,
                             aspect: str, 
                             search_results: List[Dict[str, Any]], 
                             specific_questions: List[str] = None) -> str:
        """构建分析提示词"""
        
        # 整理搜索结果
        search_content = "\n".join([
            f"来源: {result.get('url', 'unknown')}\n标题: {result.get('title', '')}\n内容: {result.get('content', '')}\n"
            for result in search_results[:10]  # 限制数量避免token过多
        ])
        
        if aspect == "prescreen":
            return self._build_prescreen_prompt(company_name, search_content)
        elif aspect == "industry":
            return self._build_industry_prompt(company_name, search_content, specific_questions)
        elif aspect == "team":
            return self._build_team_prompt(company_name, search_content, specific_questions)
        elif aspect == "financial":
            return self._build_financial_prompt(company_name, search_content, specific_questions)
        elif aspect == "risk":
            return self._build_risk_prompt(company_name, search_content, specific_questions)
        else:
            return f"请分析公司 {company_name} 的 {aspect} 方面:\n\n{search_content}"
    
    def _build_prescreen_prompt(self, company_name: str, search_content: str) -> str:
        """构建预筛选提示词"""
        return f"""
请对公司 "{company_name}" 进行投资预筛选分析。

基于以下搜索到的信息：
{search_content}

请分析以下几个方面：
1. 公司是否真实存在且有实际业务
2. 是否存在重大负面信息（违法、诈骗、重大争议等）
3. 是否具备基本的投资价值指标
4. 信息的可信度和完整性

请以以下JSON格式回复：
{{
    "passed": true/false,
    "confidence": 0.0-1.0,
    "reason": "详细的分析理由",
    "positive_factors": ["积极因素1", "积极因素2"],
    "negative_factors": ["风险因素1", "风险因素2"],
    "recommendation": "是否建议继续尽调"
}}
"""
    
    def _build_industry_prompt(self, company_name: str, search_content: str, questions: List[str] = None) -> str:
        """构建行业分析提示词"""
        return f"""
请对公司 "{company_name}" 所在行业进行深度分析。

基于以下搜索到的信息：
{search_content}

请从以下四个维度进行详细分析并评分（0-10分）：

1. **市场规模** (market_size)：
   - 分析目标市场的总体规模（TAM、SAM、SOM）
   - 考虑市场的绝对大小和相对价值
   - 评估市场的可及性

2. **增长率** (growth_rate)：
   - 分析历史增长趋势和未来预期
   - 识别增长驱动因素
   - 评估增长的可持续性

3. **竞争水平** (competition_level)：
   - 分析市场集中度和竞争格局
   - 评估竞争的激烈程度（适中竞争得分最高）
   - 识别主要竞争对手和差异化机会

4. **准入门槛** (entry_barriers)：
   - 分析技术、资金、监管等壁垒
   - 评估新进入者的难易程度
   - 考虑壁垒对投资的影响

请以以下JSON格式严格回复：
{{
    "scores": {{
        "market_size": 0.0-10.0,
        "growth_rate": 0.0-10.0,
        "competition_level": 0.0-10.0,
        "entry_barriers": 0.0-10.0,
        "overall": 0.0-10.0
    }},
    "rationale": {{
        "market_size": "详细的市场规模分析依据",
        "growth_rate": "详细的增长率分析依据",
        "competition_level": "详细的竞争水平分析依据",
        "entry_barriers": "详细的准入门槛分析依据",
        "overall": "综合评价和投资建议"
    }},
    "industry_identified": "识别出的具体行业名称",
    "key_trends": ["关键趋势1", "关键趋势2"],
    "confidence": 0.0-1.0
}}"""
    
    def _build_team_prompt(self, company_name: str, search_content: str, questions: List[str] = None) -> str:
        """构建团队分析提示词"""
        return f"""
请对公司 "{company_name}" 的创始团队和核心管理层进行评估。

基于以下搜索到的信息：
{search_content}

额外上下文：
{additional_context}

分析日期：{current_date}

请从以下四个维度进行详细分析并评分（0-10分）：

1. **创始人背景** (founder_background)：
   - 教育背景和专业资质
   - 相关行业工作经验
   - 领导力和企业家精神

2. **团队经验** (team_experience)：
   - 核心团队的专业能力
   - 相关项目和工作经验
   - 技术和商业技能匹配度

3. **过往成就** (past_achievements)：
   - 历史成功案例和项目
   - 行业认可和声誉
   - 失败经历和学习能力

4. **团队完整性** (team_completeness)：
   - 关键岗位覆盖情况
   - 技能互补性和协作能力
   - 团队稳定性和扩张能力

请以以下JSON格式严格回复：
{{
    "scores": {{
        "founder_background": 0.0-10.0,
        "team_experience": 0.0-10.0,
        "past_achievements": 0.0-10.0,
        "team_completeness": 0.0-10.0,
        "overall": 0.0-10.0
    }},
    "rationale": {{
        "founder_background": "详细的创始人背景分析",
        "team_experience": "详细的团队经验分析",
        "past_achievements": "详细的过往成就分析",
        "team_completeness": "详细的团队完整性分析",
        "overall": "团队综合评价和投资建议"
    }},
    "key_people": ["识别出的关键人员名单"],
    "team_strengths": ["团队优势1", "团队优势2"],
    "team_risks": ["团队风险1", "团队风险2"],
    "confidence": 0.0-1.0
}}"""
    
    def _build_financial_prompt(self, company_name: str, search_content: str, questions: List[str] = None) -> str:
        """构建财务分析提示词"""
        return f"""
请对公司 "{company_name}" 的财务状况进行分析。

基于以下搜索到的信息：
{search_content}

额外上下文：
{additional_context}

分析日期：{current_date}

请从以下四个维度进行详细分析并评分（0-10分）：

1. **营收状况** (revenue_status)：
   - 营收规模和增长趋势
   - 商业模式的清晰度和可行性
   - 客户基础和市场验证情况

2. **盈利能力** (profitability)：
   - 当前盈利状况（如果有）
   - 毛利率和成本结构
   - 盈利路径和时间预期

3. **融资历史** (funding_history)：
   - 历史融资轮次和金额
   - 投资方的质量和声誉
   - 估值发展趋势和合理性

4. **财务健康度** (financial_health)：
   - 现金流状况
   - 资金使用效率
   - 财务可持续性和风险

请以以下JSON格式严格回复：
{{
    "scores": {{
        "revenue_status": 0.0-10.0,
        "profitability": 0.0-10.0,
        "funding_history": 0.0-10.0,
        "financial_health": 0.0-10.0,
        "overall": 0.0-10.0
    }},
    "rationale": {{
        "revenue_status": "详细的营收状况分析",
        "profitability": "详细的盈利能力分析",
        "funding_history": "详细的融资历史分析",
        "financial_health": "详细的财务健康度分析",
        "overall": "财务综合评价和投资建议"
    }},
    "key_metrics": {{
        "latest_valuation": "最新估值（如果有）",
        "revenue_growth": "营收增长率",
        "funding_amount": "总融资金额",
        "burn_rate": "资金消耗率（如果有）"
    }},
    "financial_risks": ["财务风险1", "财务风险2"],
    "confidence": 0.0-1.0
}}"""
    
    def _build_risk_prompt(self, company_name: str, search_content: str, questions: List[str] = None) -> str:
        """构建风险分析提示词"""
        return f"""
请对公司 "{company_name}" 的投资风险进行全面评估。

基于以下搜索到的信息：
{search_content}

额外上下文：
{additional_context}

分析日期：{current_date}

请从以下四个维度进行详细分析并评分（0-10分，分数越高表示风险越低）：

1. **市场风险** (market_risk)：
   - 市场需求变化风险
   - 技术替代和颠覆风险
   - 经济周期影响
   - 客户集中度风险

2. **竞争风险** (competition_risk)：
   - 现有竞争对手威胁
   - 新进入者风险
   - 大公司进入风险
   - 价格竞争风险

3. **运营风险** (operational_risk)：
   - 团队执行能力风险
   - 技术实现风险
   - 供应链和合作伙伴风险
   - 人才流失风险

4. **监管风险** (regulatory_risk)：
   - 政策变化风险
   - 合规要求风险
   - 法律纠纷风险
   - 国际贸易风险

请以以下JSON格式严格回复：
{{
    "scores": {{
        "market_risk": 0.0-10.0,
        "competition_risk": 0.0-10.0,
        "operational_risk": 0.0-10.0,
        "regulatory_risk": 0.0-10.0,
        "overall": 0.0-10.0
    }},
    "rationale": {{
        "market_risk": "详细的市场风险分析",
        "competition_risk": "详细的竞争风险分析",
        "operational_risk": "详细的运营风险分析", 
        "regulatory_risk": "详细的监管风险分析",
        "overall": "综合风险评价和缓解建议"
    }},
    "major_risks": ["主要风险点1", "主要风险点2", "主要风险点3"],
    "risk_mitigation": ["风险缓解措施1", "风险缓解措施2"],
    "exit_risks": ["退出相关风险1", "退出相关风险2"],
    "confidence": 0.0-1.0
}}"""
    
    def _parse_analysis_response(self, response: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """解析LLM分析响应"""
        try:
            # 如果response是字典类型（来自工具调用），直接处理
            if isinstance(response, dict):
                if "content" in response:
                    response_text = response["content"]
                else:
                    return {
                        "scores": {"overall": 5.0},
                        "rationale": {"overall": "无法解析响应"},
                        "confidence": 0.3
                    }
            else:
                response_text = str(response)
            
            # 确保response_text是字符串
            if not response_text or not isinstance(response_text, str):
                return {
                    "scores": {"overall": 5.0},
                    "rationale": {"overall": "响应为空或格式错误"},
                    "confidence": 0.3
                }
            
            # 尝试从响应中提取JSON
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # 如果没有找到JSON，返回默认结构
                return {
                    "scores": {"overall": 5.0},
                    "rationale": {"overall": response_text},
                    "confidence": 0.5
                }
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response: {response}")
            return {
                "scores": {"overall": 5.0},
                "rationale": {"overall": f"解析错误，原始响应: {str(response)[:200]}"},
                "confidence": 0.3
            }
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return {
                "scores": {"overall": 5.0},
                "rationale": {"overall": f"响应解析异常: {str(e)}"},
                "confidence": 0.3
            }
    
    async def generate_cross_check_analysis(self, 
                                          bp_data: Dict[str, Any], 
                                          external_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成交叉验证分析"""
        prompt = f"""
请对以下BP信息和外部调研信息进行交叉验证分析：

BP中的信息：
{json.dumps(bp_data, ensure_ascii=False, indent=2)}

外部调研信息：
{json.dumps(external_data, ensure_ascii=False, indent=2)}

请分析信息的一致性，识别差异点，并评估信息的可信度。

请以以下JSON格式回复：
{{
    "consistency_score": 7.5,
    "major_discrepancies": ["差异点1", "差异点2"], 
    "verified_facts": ["已验证的事实1", "已验证的事实2"],
    "unverified_claims": ["未验证的声明1", "未验证的声明2"],
    "credibility_assessment": "整体可信度评估",
    "recommendations": ["建议1", "建议2"]
}}
"""
        
        try:
            response = await self._call_llm(prompt)
            return self._parse_analysis_response(response)
        except Exception as e:
            logger.error(f"Cross-check analysis error: {e}")
            return {
                "consistency_score": 5.0,
                "major_discrepancies": [],
                "verified_facts": [],
                "unverified_claims": [],
                "credibility_assessment": f"分析错误: {str(e)}",
                "recommendations": []
            }
    
    async def chat_completion(self, 
                            messages: List[Dict[str, str]], 
                            system_message: Optional[str] = None,
                            temperature: Optional[float] = None,
                            max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        执行聊天完成请求
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            system_message: 系统消息（可选）
            temperature: 温度参数（可选）
            max_tokens: 最大令牌数（可选）
        
        Returns:
            LLM响应结果
        """
        
        # 构建完整的消息列表
        full_messages = []
        
        # 添加系统消息（如果提供）
        if system_message:
            full_messages.append({
                "role": "system",
                "content": system_message
            })
        
        # 添加用户消息
        full_messages.extend(messages)
        
        # 构建请求负载
        payload = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": False
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://venturelens.ai",  # OpenRouter要求
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
                        
                        # 提取响应内容
                        content = result["choices"][0]["message"]["content"]
                        
                        return {
                            "success": True,
                            "content": content,
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
    
    async def analyze_with_prompt_template(self, 
                                         prompt_template: str,
                                         variables: Dict[str, Any],
                                         system_message: str,
                                         temperature: Optional[float] = None) -> Dict[str, Any]:
        """
        使用提示模板进行分析
        
        Args:
            prompt_template: 提示模板
            variables: 模板变量
            system_message: 系统消息
            temperature: 温度参数
        
        Returns:
            分析结果
        """
        
        # 格式化提示模板
        try:
            formatted_prompt = prompt_template.format(**variables)
        except KeyError as e:
            return {
                "success": False,
                "error": f"Missing template variable: {e}",
                "timestamp": datetime.now().isoformat()
            }
        
        # 构建消息
        messages = [
            {
                "role": "user",
                "content": formatted_prompt
            }
        ]
        
        # 执行推理
        return await self.chat_completion(
            messages=messages,
            system_message=system_message,
            temperature=temperature
        )
    
    async def structured_investment_analysis(self,
                                          analysis_type: str,
                                          company_name: str,
                                          search_results: List[Dict[str, Any]],
                                          additional_context: str = "") -> Dict[str, Any]:
        """
        结构化投资分析
        
        Args:
            analysis_type: 分析类型（prescreen, industry, team, financial, risk）
            company_name: 公司名称
            search_results: 搜索结果数据
            additional_context: 额外上下文信息
        
        Returns:
            结构化分析结果
        """
        
        # 获取分析模板
        templates = self._get_investment_analysis_templates()
        
        if analysis_type not in templates:
            return {
                "success": False,
                "error": f"Unsupported analysis type: {analysis_type}",
                "timestamp": datetime.now().isoformat()
            }
        
        template_info = templates[analysis_type]
        
        # 准备搜索结果文本
        search_content = "\n".join([
            f"来源: {result.get('url', 'unknown')}\n"
            f"标题: {result.get('title', '')}\n"
            f"内容: {result.get('content', '')}\n"
            f"可信度: {result.get('score', 0.7)}\n"
            "---"
            for result in search_results[:10]  # 限制数量避免token过多
        ])
        
        # 准备变量
        variables = {
            "company_name": company_name,
            "search_content": search_content,
            "additional_context": additional_context,
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "analysis_type": analysis_type
        }
        
        # 执行分析
        result = await self.analyze_with_prompt_template(
            prompt_template=template_info["prompt"],
            variables=variables,
            system_message=template_info["system_message"],
            temperature=0.1  # 分析任务使用较低温度
        )
        
        if result["success"]:
            # 尝试解析结构化输出
            try:
                structured_result = self._parse_structured_output(result["content"], analysis_type)
                result["structured_data"] = structured_result
                result["analysis_type"] = analysis_type
            except Exception as e:
                logger.warning(f"Failed to parse structured output for {analysis_type}: {e}")
                result["structured_data"] = self._create_fallback_structure(analysis_type, result["content"])
        
        return result

    def _get_investment_analysis_templates(self) -> Dict[str, Dict[str, str]]:
        """获取投资分析模板"""
        return {
            "prescreen": {
                "system_message": """你是一位经验丰富的投资顾问，专门负责对潜在投资标的进行初步筛选。你的任务是基于搜索到的公开信息，快速判断一家公司是否值得进一步进行尽职调查。

你需要特别关注：
1. 公司的真实性和可信度
2. 是否存在重大风险信号
3. 基本的商业价值指标
4. 信息的完整性和质量

请严格按照要求的JSON格式输出，确保你的分析客观、专业且有依据。""",
                "prompt": """请对公司"{company_name}"进行投资预筛选分析。

基于以下搜索信息：
{search_content}

额外上下文：
{additional_context}

分析日期：{current_date}

请从以下角度进行评估：
1. **公司真实性**：是否为真实存在的公司，有实际业务运营
2. **信息质量**：搜索到的信息是否充分、可信
3. **风险信号**：是否存在重大负面信息（法律纠纷、违规、失败记录等）
4. **投资价值**：是否展现出基本的投资价值指标

请以以下JSON格式严格回复：
{{
    "passed": true/false,
    "confidence": 0.0-1.0,
    "reason": "详细的判断理由",
    "positive_factors": ["积极因素1", "积极因素2"],
    "negative_factors": ["风险因素1", "风险因素2"],
    "information_quality": "high/medium/low",
    "recommendation": "是否建议继续尽调的具体建议"
}}"""
            },
            
            "industry": {
                "system_message": """你是一位资深的行业分析专家，拥有多年的市场研究和投资分析经验。你精通各个行业的发展趋势、竞争格局和投资价值评估。

你的分析应该：
1. 基于客观数据和市场事实
2. 考虑行业的长期发展趋势
3. 评估投资机会和风险
4. 提供量化的评分依据

评分标准（0-10分）：
- 0-3分：较差，不建议投资
- 4-6分：一般，需谨慎考虑
- 7-8分：良好，有投资价值
- 9-10分：优秀，强烈推荐

请确保你的分析有理有据，评分公正客观。""",
                "prompt": """请对公司"{company_name}"所在行业进行深度分析。

基于以下搜索到的信息：
{search_content}

额外上下文：
{additional_context}

分析日期：{current_date}

请从以下四个维度进行详细分析并评分（0-10分）：

1. **市场规模** (market_size)：
   - 分析目标市场的总体规模（TAM、SAM、SOM）
   - 计算市场的绝对大小和相对价值
   - 评估市场的可及性

2. **增长率** (growth_rate)：
   - 分析历史增长趋势和未来预期
   - 识别增长驱动因素
   - 评估增长的可持续性

3. **竞争水平** (competition_level)：
   - 分析市场集中度和竞争格局
   - 评估竞争的激烈程度（适中竞争得分最高）
   - 识别主要竞争对手和差异化机会

4. **准入门槛** (entry_barriers)：
   - 分析技术、资金、监管等壁垒
   - 评估新进入者的难易程度
   - 考虑壁垒对投资的影响

请以以下JSON格式严格回复：
{{
    "scores": {{
        "market_size": 0.0-10.0,
        "growth_rate": 0.0-10.0,
        "competition_level": 0.0-10.0,
        "entry_barriers": 0.0-10.0,
        "overall": 0.0-10.0
    }},
    "rationale": {{
        "market_size": "详细的市场规模分析依据",
        "growth_rate": "详细的增长率分析依据",
        "competition_level": "详细的竞争水平分析依据",
        "entry_barriers": "详细的准入门槛分析依据",
        "overall": "综合评价和投资建议"
    }},
    "industry_identified": "识别出的具体行业名称",
    "key_trends": ["关键趋势1", "关键趋势2"],
    "confidence": 0.0-1.0
}}"""
            },
            
            "team": {
                "system_message": """你是一位专业的人才评估和团队分析专家，擅长评估创业团队的能力和潜力。你深知团队是早期投资成功的关键因素。

你的评估应该关注：
1. 创始人和核心团队的背景匹配度
2. 团队的执行力和历史成就
3. 团队结构的完整性和互补性
4. 领导力和行业声誉

评分时请考虑：
- 相关行业经验的重要性
- 成功创业或管理经验
- 技术背景与业务的匹配
- 团队的稳定性和凝聚力

请基于客观信息进行专业评估。""",
                "prompt": """请对公司"{company_name}"的创始团队和核心管理层进行评估。

基于以下搜索到的信息：
{search_content}

额外上下文：
{additional_context}

分析日期：{current_date}

请从以下四个维度进行详细分析并评分（0-10分）：

1. **创始人背景** (founder_background)：
   - 教育背景和专业资质
   - 相关行业工作经验
   - 领导力和企业家精神

2. **团队经验** (team_experience)：
   - 核心团队的专业能力
   - 相关项目和工作经验
   - 技术和商业技能匹配度

3. **过往成就** (past_achievements)：
   - 历史成功案例和项目
   - 行业认可和声誉
   - 失败经历和学习能力

4. **团队完整性** (team_completeness)：
   - 关键岗位覆盖情况
   - 技能互补性和协作能力
   - 团队稳定性和扩张能力

请以以下JSON格式严格回复：
{{
    "scores": {{
        "founder_background": 0.0-10.0,
        "team_experience": 0.0-10.0,
        "past_achievements": 0.0-10.0,
        "team_completeness": 0.0-10.0,
        "overall": 0.0-10.0
    }},
    "rationale": {{
        "founder_background": "详细的创始人背景分析",
        "team_experience": "详细的团队经验分析",
        "past_achievements": "详细的过往成就分析",
        "team_completeness": "详细的团队完整性分析",
        "overall": "团队综合评价和投资建议"
    }},
    "key_people": ["识别出的关键人员名单"],
    "team_strengths": ["团队优势1", "团队优势2"],
    "team_risks": ["团队风险1", "团队风险2"],
    "confidence": 0.0-1.0
}}"""
            },
            
            "financial": {
                "system_message": """你是一位专业的财务分析师，专门从事早期投资的财务尽职调查。你深谙初创公司财务分析的特点和挑战。

你的分析重点：
1. 商业模式的财务可行性
2. 营收增长的质量和可持续性
3. 成本结构和效率
4. 融资需求和资金使用效率

对于早期公司，你会：
- 更关注营收增长而非当前盈利
- 重视商业模式的可扩展性
- 评估融资历史和估值合理性
- 分析现金流和资金使用效率

请基于有限的公开信息做出专业判断。""",
                "prompt": """请对公司"{company_name}"的财务状况进行分析。

基于以下搜索信息：
{search_content}

额外上下文：
{additional_context}

分析日期：{current_date}

请从以下四个维度进行详细分析并评分（0-10分）：

1. **营收状况** (revenue_status)：
   - 营收规模和增长趋势
   - 商业模式的清晰度和可行性
   - 客户基础和市场验证情况

2. **盈利能力** (profitability)：
   - 当前盈利状况（如果有）
   - 毛利率和成本结构
   - 盈利路径和时间预期

3. **融资历史** (funding_history)：
   - 历史融资轮次和金额
   - 投资方的质量和声誉
   - 估值发展趋势和合理性

4. **财务健康度** (financial_health)：
   - 现金流状况
   - 资金使用效率
   - 财务可持续性和风险

请以以下JSON格式严格回复：
{{
    "scores": {{
        "revenue_status": 0.0-10.0,
        "profitability": 0.0-10.0,
        "funding_history": 0.0-10.0,
        "financial_health": 0.0-10.0,
        "overall": 0.0-10.0
    }},
    "rationale": {{
        "revenue_status": "详细的营收状况分析",
        "profitability": "详细的盈利能力分析",
        "funding_history": "详细的融资历史分析",
        "financial_health": "详细的财务健康度分析",
        "overall": "财务综合评价和投资建议"
    }},
    "key_metrics": {{
        "latest_valuation": "最新估值（如果有）",
        "revenue_growth": "营收增长率",
        "funding_amount": "总融资金额",
        "burn_rate": "资金消耗率（如果有）"
    }},
    "financial_risks": ["财务风险1", "财务风险2"],
    "confidence": 0.0-1.0
}}"""
            },
            
            "risk": {
                "system_message": """你是一位专业的投资风险评估专家，专门识别和评估早期投资的各类风险。你的经验涵盖市场风险、技术风险、团队风险、监管风险等多个维度。

风险评估原则：
1. 识别所有可能的风险点
2. 评估风险的概率和影响程度
3. 考虑风险的可控性和缓解措施
4. 平衡风险与回报的关系

评分说明（0-10分，分数越高表示风险越低）：
- 0-3分：高风险，不建议投资
- 4-6分：中等风险，需要风险缓解措施
- 7-8分：低风险，可接受的投资风险
- 9-10分：极低风险，理想的投资标的

请客观评估，不遗漏重要风险点。""",
                "prompt": """请对公司"{company_name}"的投资风险进行全面评估。

基于以下搜索信息：
{search_content}

额外上下文：
{additional_context}

分析日期：{current_date}

请从以下四个维度进行详细分析并评分（0-10分，分数越高表示风险越低）：

1. **市场风险** (market_risk)：
   - 市场需求变化风险
   - 技术替代和颠覆风险
   - 经济周期影响
   - 客户集中度风险

2. **竞争风险** (competition_risk)：
   - 现有竞争对手威胁
   - 新进入者风险
   - 大公司进入风险
   - 价格竞争风险

3. **运营风险** (operational_risk)：
   - 团队执行能力风险
   - 技术实现风险
   - 供应链和合作伙伴风险
   - 人才流失风险

4. **监管风险** (regulatory_risk)：
   - 政策变化风险
   - 合规要求风险
   - 法律纠纷风险
   - 国际贸易风险

请以以下JSON格式严格回复：
{{
    "scores": {{
        "market_risk": 0.0-10.0,
        "competition_risk": 0.0-10.0,
        "operational_risk": 0.0-10.0,
        "regulatory_risk": 0.0-10.0,
        "overall": 0.0-10.0
    }},
    "rationale": {{
        "market_risk": "详细的市场风险分析",
        "competition_risk": "详细的竞争风险分析",
        "operational_risk": "详细的运营风险分析",
        "regulatory_risk": "详细的监管风险分析",
        "overall": "综合风险评价和缓解建议"
    }},
    "major_risks": ["主要风险点1", "主要风险点2", "主要风险点3"],
    "risk_mitigation": ["风险缓解措施1", "风险缓解措施2"],
    "exit_risks": ["退出相关风险1", "退出相关风险2"],
    "confidence": 0.0-1.0
}}"""
            }
        }
    
    async def call_llm_with_tools(self, 
                                  messages: List[Dict[str, str]], 
                                  tools: Optional[List[Dict[str, Any]]] = None,
                                  system_message: Optional[str] = None) -> Dict[str, Any]:
        """调用LLM并支持工具调用"""
        
        # 构建消息列表
        formatted_messages = []
        
        # 添加系统消息
        if system_message:
            formatted_messages.append({
                "role": "system",
                "content": system_message
            })
        
        # 添加用户消息
        for message in messages:
            formatted_messages.append(message)
        
        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        # 如果有工具，添加工具定义
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        try:
            response = await self._call_openrouter_api(payload)
            return self._parse_tool_response(response)
        except Exception as e:
            logger.error(f"LLM tool call error: {e}")
            return {
                "content": f"调用LLM时出现错误: {str(e)}",
                "tool_calls": [],
                "error": True
            }
    
    async def _call_openrouter_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """调用OpenRouter API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://venturelens.ai",
            "X-Title": "VentureLens"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenRouter API error {response.status}: {error_text}")
    
    def _parse_tool_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """解析工具调用响应"""
        try:
            choice = response["choices"][0]
            message = choice["message"]
            
            result = {
                "content": message.get("content", ""),
                "tool_calls": [],
                "error": False
            }
            
            # 解析工具调用
            if "tool_calls" in message:
                for tool_call in message["tool_calls"]:
                    result["tool_calls"].append({
                        "id": tool_call.get("id"),
                        "function": {
                            "name": tool_call["function"]["name"],
                            "arguments": tool_call["function"]["arguments"]
                        }
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing tool response: {e}")
            return {
                "content": f"解析响应时出错: {str(e)}",
                "tool_calls": [],
                "error": True
            }
    
    async def structured_investment_analysis_with_tools(self,
                                                      analysis_type: str,
                                                      company_name: str,
                                                      tools: List[Dict[str, Any]] = None,
                                                      max_iterations: int = 3) -> Dict[str, Any]:
        """
        带工具调用的结构化投资分析
        
        Args:
            analysis_type: 分析类型（industry, team, financial, risk）
            company_name: 公司名称
            tools: 可用工具列表
            max_iterations: 最大迭代次数
        
        Returns:
            结构化分析结果
        """
        
        # 获取分析模板
        templates = self._get_investment_analysis_templates()
        
        if analysis_type not in templates:
            return {
                "success": False,
                "error": f"Unsupported analysis type: {analysis_type}",
                "timestamp": datetime.now().isoformat()
            }
        
        template_info = templates[analysis_type]
        
        # 构建初始prompt
        prompt = f"""请对公司 "{company_name}" 进行{analysis_type}分析。

你可以使用提供的工具来获取相关信息。请先调用适当的工具收集必要信息，然后基于收集到的信息进行分析。

{template_info['prompt'].replace('{company_name}', company_name).replace('{search_content}', '请使用工具搜索相关信息').replace('{additional_context}', '').replace('{current_date}', datetime.now().strftime('%Y-%m-%d'))}
"""
        
        messages = [{"role": "user", "content": prompt}]
        iteration = 0
        tool_results = []
        
        try:
            while iteration < max_iterations:
                # 调用LLM with tools
                response = await self.call_llm_with_tools(
                    messages=messages,
                    tools=tools or [],
                    system_message=template_info["system_message"]
                )
                
                if response.get("error"):
                    break
                
                # 如果有工具调用
                if response.get("tool_calls"):
                    # 添加助手消息
                    messages.append({
                        "role": "assistant",
                        "content": response.get("content", ""),
                        "tool_calls": response["tool_calls"]
                    })
                    
                    # 处理工具调用（这里简化处理，实际应该调用toolkit）
                    for tool_call in response["tool_calls"]:
                        tool_results.append({
                            "tool_name": tool_call["function"]["name"],
                            "arguments": tool_call["function"]["arguments"]
                        })
                        
                        # 添加工具结果（模拟）
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": f"工具 {tool_call['function']['name']} 执行完成"
                        })
                
                # 如果有文本响应且没有工具调用，说明分析完成
                if response.get("content") and not response.get("tool_calls"):
                    # 解析结构化结果
                    try:
                        parsed_result = self._parse_structured_output(response["content"], analysis_type)
                        return {
                            "success": True,
                            "content": response["content"],
                            "parsed_result": parsed_result,
                            "tool_results": tool_results,
                            "iterations": iteration,
                            "timestamp": datetime.now().isoformat()
                        }
                    except Exception as e:
                        return {
                            "success": True,
                            "content": response["content"],
                            "parsed_result": self._create_fallback_structure(analysis_type, response["content"]),
                            "tool_results": tool_results,
                            "iterations": iteration,
                            "timestamp": datetime.now().isoformat()
                        }
                
                iteration += 1
            
            # 如果达到最大迭代次数，返回默认结果
            return {
                "success": False,
                "error": "达到最大迭代次数",
                "tool_results": tool_results,
                "iterations": iteration,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Structured analysis with tools error: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_results": tool_results,
                "timestamp": datetime.now().isoformat()
            }
