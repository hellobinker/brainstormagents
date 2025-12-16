"""
对抗验证机制

专门设置"挑战者"角色：
- 专门找方案的漏洞
- 提出极端场景测试
- 从不同角度质疑
"""
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class Challenge:
    """挑战点"""
    category: str  # "technical", "cost", "risk", "feasibility", "edge_case"
    challenge: str
    severity: str  # "high", "medium", "low"
    suggested_test: str  # 建议的验证方法
    
    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "challenge": self.challenge,
            "severity": self.severity,
            "suggested_test": self.suggested_test
        }


@dataclass
class ChallengeReport:
    """挑战报告"""
    overall_robustness: int  # 1-10 方案稳健性评分
    critical_flaws: List[str]
    challenges: List[Challenge]
    edge_cases: List[str]
    unanswered_questions: List[str]
    verdict: str  # "pass", "conditional_pass", "fail"
    
    def to_dict(self) -> dict:
        return {
            "overall_robustness": self.overall_robustness,
            "critical_flaws": self.critical_flaws,
            "challenges": [c.to_dict() for c in self.challenges],
            "edge_cases": self.edge_cases,
            "unanswered_questions": self.unanswered_questions,
            "verdict": self.verdict
        }


class AdversarialValidator:
    """
    对抗验证器
    
    扮演"魔鬼代言人"角色，专门挑战和质疑方案
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def challenge(
        self,
        problem: str,
        solutions: List[Dict[str, str]]
    ) -> ChallengeReport:
        """
        对方案进行对抗性验证
        
        Args:
            problem: 原问题
            solutions: [{"expert": name, "solution": content}]
        """
        solutions_text = "\n\n".join([
            f"【{s['expert']}的方案】\n{s['solution'][:500]}"
            for s in solutions
        ])
        
        prompt = f"""【对抗验证 - 魔鬼代言人】

你是一位严格的技术评审专家，你的任务是**尽可能找出方案的问题**。
不要客气，不要给面子，要像对手一样挑战这些方案。

【原问题】
{problem}

【待验证方案】
{solutions_text}

请从以下角度进行严格审查：

1. **技术可行性**：方案在技术上是否真的可行？有无理论或实践漏洞？
2. **极端场景**：在最坏情况下会怎样？有没有考虑边界条件？
3. **成本现实性**：成本估计是否过于乐观？隐藏成本有哪些？
4. **实施障碍**：实际执行时会遇到什么障碍？
5. **竞争视角**：竞争对手/反对者会如何攻击这个方案？

请输出JSON格式的挑战报告：

{{
    "overall_robustness": 1-10,  // 方案稳健性评分
    "critical_flaws": [
        "致命缺陷1（如果有）",
        "致命缺陷2（如果有）"
    ],
    "challenges": [
        {{
            "category": "technical/cost/risk/feasibility/edge_case",
            "challenge": "具体挑战描述",
            "severity": "high/medium/low",
            "suggested_test": "建议如何验证或规避"
        }}
    ],
    "edge_cases": [
        "需要考虑的极端场景1",
        "需要考虑的极端场景2"
    ],
    "unanswered_questions": [
        "方案中未回答的关键问题1",
        "未回答的关键问题2"
    ],
    "verdict": "pass/conditional_pass/fail"  // 总体判定
}}

请严格审查，只返回JSON："""
        
        try:
            result = await self.llm_client.get_completion_async(
                system_prompt="你是魔鬼代言人，专门找问题和漏洞。保持严格、挑剔、不留情面的态度。只返回JSON。",
                user_prompt=prompt,
                model="gemini-3-pro-preview"
            )
            
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                data = json.loads(json_match.group())
                
                challenges = [
                    Challenge(
                        category=c.get("category", "technical"),
                        challenge=c.get("challenge", ""),
                        severity=c.get("severity", "medium"),
                        suggested_test=c.get("suggested_test", "")
                    )
                    for c in data.get("challenges", [])
                ]
                
                return ChallengeReport(
                    overall_robustness=data.get("overall_robustness", 5),
                    critical_flaws=data.get("critical_flaws", []),
                    challenges=challenges,
                    edge_cases=data.get("edge_cases", []),
                    unanswered_questions=data.get("unanswered_questions", []),
                    verdict=data.get("verdict", "conditional_pass")
                )
        except Exception as e:
            print(f"[WARN] Adversarial validation failed: {e}")
        
        return ChallengeReport(
            overall_robustness=5,
            critical_flaws=["验证过程异常"],
            challenges=[],
            edge_cases=["待分析"],
            unanswered_questions=["待确认"],
            verdict="conditional_pass"
        )
    
    async def generate_counter_proposal(
        self,
        problem: str,
        original_solutions: List[Dict[str, str]],
        challenge_report: ChallengeReport
    ) -> str:
        """
        基于挑战结果，生成改进建议或替代方案
        """
        challenges_text = "\n".join([
            f"- [{c.severity}] {c.challenge}"
            for c in challenge_report.challenges[:5]
        ])
        
        prompt = f"""【基于挑战的改进建议】

原方案受到了以下挑战：

【稳健性评分】{challenge_report.overall_robustness}/10
【判定】{challenge_report.verdict}

【主要挑战】
{challenges_text}

【未回答问题】
{', '.join(challenge_report.unanswered_questions[:3])}

请针对这些挑战，给出：
1. 如何弥补发现的缺陷
2. 如何应对极端场景
3. 是否需要备选方案

改进建议（200字内）："""
        
        try:
            return await self.llm_client.get_completion_async(
                system_prompt="你是方案改进顾问，根据发现的问题给出务实的改进建议。",
                user_prompt=prompt,
                model="gemini-3-pro-preview"
            )
        except:
            return "建议针对发现的问题进行逐项改进"
