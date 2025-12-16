"""
多轮追问机制

支持在求解过程中的追问和澄清：
- 系统自动识别模糊点并追问
- 专家可请求更多细节
- 用户可在过程中补充信息
"""
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


@dataclass
class ClarificationRequest:
    """澄清请求"""
    source: str  # "system", "expert", "user"
    question: str
    context: str
    importance: str  # "critical", "helpful", "optional"
    answered: bool = False
    answer: str = ""
    
    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "question": self.question,
            "context": self.context,
            "importance": self.importance,
            "answered": self.answered,
            "answer": self.answer
        }


class ClarificationEngine:
    """
    澄清问询引擎
    
    识别问题中的模糊点并生成澄清问题
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.pending_clarifications: List[ClarificationRequest] = []
    
    async def identify_ambiguities(self, problem: str) -> List[ClarificationRequest]:
        """
        识别问题中的模糊点
        
        Returns:
            需要澄清的问题列表
        """
        prompt = f"""【问题模糊点识别】

请分析以下技术问题，识别其中可能需要澄清的模糊点。

【问题】
{problem}

请识别：
1. **关键信息缺失**：哪些重要信息没有提供？
2. **表述模糊**：哪些描述可能有多种理解？
3. **量化需求不明**：哪些需要具体数值但未给出？
4. **边界条件不清**：约束条件是否明确？

请输出需要追问的问题，JSON格式：
{{
    "clarifications": [
        {{
            "question": "需要追问的具体问题",
            "context": "为什么需要这个信息",
            "importance": "critical/helpful/optional"
        }}
    ],
    "can_proceed": true/false  // 是否有足够信息可以先开始分析
}}

只返回JSON："""
        
        try:
            result = await self.llm_client.get_completion_async(
                system_prompt="你是问题分析专家，擅长识别信息缺失和模糊点。只返回JSON。",
                user_prompt=prompt,
                model="gemini-3-pro-preview"
            )
            
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                data = json.loads(json_match.group())
                
                clarifications = [
                    ClarificationRequest(
                        source="system",
                        question=c.get("question", ""),
                        context=c.get("context", ""),
                        importance=c.get("importance", "helpful")
                    )
                    for c in data.get("clarifications", [])
                ]
                
                self.pending_clarifications.extend(clarifications)
                return clarifications
        except Exception as e:
            print(f"[WARN] Ambiguity identification failed: {e}")
        
        return []
    
    async def expert_request_clarification(
        self,
        expert_name: str,
        problem: str,
        current_analysis: str
    ) -> Optional[ClarificationRequest]:
        """
        专家在分析过程中请求更多信息
        """
        prompt = f"""【专家追问】

你是{expert_name}，正在分析以下问题：
{problem}

你当前的分析：
{current_analysis[:400]}

在继续深入分析之前，你是否需要更多信息？
如果需要，请提出**一个**最关键的问题。
如果信息足够，返回空。

请输出JSON：
{{
    "needs_clarification": true/false,
    "question": "如果需要追问，你的问题是什么",
    "reason": "为什么需要这个信息"
}}

只返回JSON："""
        
        try:
            result = await self.llm_client.get_completion_async(
                system_prompt=f"你是{expert_name}，如果确实需要更多信息才能给出好的分析，请提问。只返回JSON。",
                user_prompt=prompt,
                model="gemini-3-pro-preview"
            )
            
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                data = json.loads(json_match.group())
                
                if data.get("needs_clarification"):
                    req = ClarificationRequest(
                        source=expert_name,
                        question=data.get("question", ""),
                        context=data.get("reason", ""),
                        importance="helpful"
                    )
                    self.pending_clarifications.append(req)
                    return req
        except Exception as e:
            print(f"[WARN] Expert clarification request failed: {e}")
        
        return None
    
    def add_user_clarification(self, question: str, answer: str):
        """用户回答追问"""
        for req in self.pending_clarifications:
            if req.question == question:
                req.answered = True
                req.answer = answer
                break
    
    def get_pending_questions(self, importance_filter: str = None) -> List[ClarificationRequest]:
        """获取待回答的问题"""
        pending = [q for q in self.pending_clarifications if not q.answered]
        if importance_filter:
            pending = [q for q in pending if q.importance == importance_filter]
        return pending
    
    def get_answered_context(self) -> str:
        """获取已回答问题的上下文，用于增强后续分析"""
        answered = [q for q in self.pending_clarifications if q.answered]
        if not answered:
            return ""
        
        context = "【补充信息】\n"
        for q in answered:
            context += f"Q: {q.question}\nA: {q.answer}\n\n"
        return context
    
    def get_summary(self) -> Dict:
        """获取澄清状态摘要"""
        total = len(self.pending_clarifications)
        answered = sum(1 for q in self.pending_clarifications if q.answered)
        critical_pending = sum(
            1 for q in self.pending_clarifications 
            if not q.answered and q.importance == "critical"
        )
        
        return {
            "total_questions": total,
            "answered": answered,
            "pending": total - answered,
            "critical_pending": critical_pending,
            "ready_to_proceed": critical_pending == 0
        }
