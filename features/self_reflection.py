"""
自我反思机制

在生成方案后，让专家进行自我反思：
- 最大风险是什么？
- 如果失败，最可能的原因？
- 有没有更简单的替代方案？
"""
import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SelfReflection:
    """自我反思结果"""
    expert_name: str
    biggest_risk: str
    failure_reasons: List[str]
    alternative_approach: str
    confidence_level: int  # 1-10
    blind_spots: List[str]
    
    def to_dict(self) -> dict:
        return {
            "expert_name": self.expert_name,
            "biggest_risk": self.biggest_risk,
            "failure_reasons": self.failure_reasons,
            "alternative_approach": self.alternative_approach,
            "confidence_level": self.confidence_level,
            "blind_spots": self.blind_spots
        }


class SelfReflectionEngine:
    """
    自我反思引擎
    
    让专家对自己的方案进行批判性思考
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def reflect(
        self, 
        problem: str,
        expert_name: str,
        expert_role: str,
        solution: str
    ) -> SelfReflection:
        """
        对方案进行自我反思
        """
        prompt = f"""【自我反思】

你是{expert_name}（{expert_role}），刚刚给出了以下解决方案。
现在请进行**自我批判性反思**。

【原始问题】
{problem}

【你的解决方案摘要】
{solution[:800]}

请诚实回答以下问题，输出JSON：

{{
    "biggest_risk": "这个方案最大的风险是什么？可能导致什么后果？",
    "failure_reasons": [
        "如果这个方案失败，最可能的原因1",
        "最可能的原因2",
        "最可能的原因3"
    ],
    "alternative_approach": "有没有更简单或更稳妥的替代方案？如果有，请简述",
    "confidence_level": 1-10,  // 你对这个方案的把握程度
    "blind_spots": [
        "可能遗漏考虑的因素1",
        "可能遗漏考虑的因素2"
    ]
}}

请诚实、严格地自我审视，只返回JSON："""
        
        try:
            result = await self.llm_client.get_completion_async(
                system_prompt="你正在进行自我反思，请诚实面对方案的不足，不要过度自信。只返回JSON。",
                user_prompt=prompt,
                model="gemini-3-pro-preview"
            )
            
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                data = json.loads(json_match.group())
                return SelfReflection(
                    expert_name=expert_name,
                    biggest_risk=data.get("biggest_risk", ""),
                    failure_reasons=data.get("failure_reasons", []),
                    alternative_approach=data.get("alternative_approach", ""),
                    confidence_level=data.get("confidence_level", 5),
                    blind_spots=data.get("blind_spots", [])
                )
        except Exception as e:
            print(f"[WARN] Self reflection failed: {e}")
        
        return SelfReflection(
            expert_name=expert_name,
            biggest_risk="反思过程异常",
            failure_reasons=["需要更多分析"],
            alternative_approach="待探索",
            confidence_level=5,
            blind_spots=["待识别"]
        )
    
    async def aggregate_reflections(
        self, 
        reflections: List[SelfReflection]
    ) -> dict:
        """
        汇总所有专家的反思，识别共性问题
        """
        all_risks = [r.biggest_risk for r in reflections]
        all_failure_reasons = []
        for r in reflections:
            all_failure_reasons.extend(r.failure_reasons)
        
        all_blind_spots = []
        for r in reflections:
            all_blind_spots.extend(r.blind_spots)
        
        avg_confidence = sum(r.confidence_level for r in reflections) / len(reflections) if reflections else 5
        
        # 找出重复出现的风险和盲点
        from collections import Counter
        common_risks = [risk for risk, count in Counter(all_failure_reasons).items() if count > 1]
        common_blind_spots = [spot for spot, count in Counter(all_blind_spots).items() if count > 1]
        
        return {
            "average_confidence": avg_confidence,
            "all_risks": all_risks,
            "common_failure_reasons": common_risks if common_risks else all_failure_reasons[:3],
            "common_blind_spots": common_blind_spots if common_blind_spots else all_blind_spots[:3],
            "overall_assessment": "需要关注共性风险" if common_risks else "风险分散，需逐个应对"
        }
