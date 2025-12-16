"""
自适应迭代控制器

根据专家共识度自动决定是否继续迭代：
- 检测专家意见分歧程度
- 分歧大则继续讨论
- 达成共识则提前结束
"""
import json
from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass
class ConsensusResult:
    """共识检测结果"""
    consensus_score: float      # 共识度 0-100
    divergence_points: List[str]  # 分歧点
    agreement_points: List[str]   # 共识点
    should_continue: bool         # 是否需要继续迭代
    recommendation: str           # 建议


class AdaptiveIterationController:
    """
    自适应迭代控制器
    
    根据专家讨论的共识程度，自动决定是否继续迭代
    """
    
    def __init__(self, llm_client, consensus_threshold: float = 75.0):
        """
        Args:
            llm_client: LLM客户端
            consensus_threshold: 共识度阈值（达到则停止迭代）
        """
        self.llm_client = llm_client
        self.consensus_threshold = consensus_threshold
    
    async def check_consensus(
        self, 
        problem: str,
        solutions: List[Dict[str, str]],
        discussions: List[Dict[str, str]] = None
    ) -> ConsensusResult:
        """
        检测当前的共识程度
        
        Args:
            problem: 原问题
            solutions: 各专家的解决方案 [{"expert": name, "solution": content}]
            discussions: 讨论记录（可选）
            
        Returns:
            ConsensusResult
        """
        solutions_text = "\n\n".join([
            f"【{s['expert']}】\n{s['solution'][:400]}"
            for s in solutions
        ])
        
        discussions_text = ""
        if discussions:
            discussions_text = "\n".join([
                f"[{d['expert']}] {d.get('comment', '')[:200]}"
                for d in discussions
            ])
        
        prompt = f"""【共识度分析】

请分析以下专家讨论的共识程度。

【问题】{problem}

【各专家方案】
{solutions_text}

【讨论记录】
{discussions_text if discussions_text else '无'}

【分析要求】
请评估专家们的共识程度，输出JSON格式：

{{
    "consensus_score": 0-100,  // 共识度分数
    "agreement_points": [      // 专家们达成共识的点
        "共识点1",
        "共识点2"
    ],
    "divergence_points": [     // 专家们存在分歧的点
        "分歧点1",
        "分歧点2"
    ],
    "main_conflict": "主要矛盾描述",
    "recommendation": "是否需要继续讨论的建议"
}}

请只返回JSON："""
        
        try:
            result = await self.llm_client.get_completion_async(
                system_prompt="你是共识分析专家，擅长识别讨论中的共识和分歧。只返回JSON。",
                user_prompt=prompt,
                model="gemini-3-pro-preview"
            )
            
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                data = json.loads(json_match.group())
                score = float(data.get("consensus_score", 50))
                
                return ConsensusResult(
                    consensus_score=score,
                    divergence_points=data.get("divergence_points", []),
                    agreement_points=data.get("agreement_points", []),
                    should_continue=score < self.consensus_threshold,
                    recommendation=data.get("recommendation", "")
                )
        except Exception as e:
            print(f"[WARN] Consensus check failed: {e}")
        
        # 降级：简单的文本相似度检测
        return self._fallback_consensus(solutions)
    
    def _fallback_consensus(self, solutions: List[Dict]) -> ConsensusResult:
        """降级方案：基于关键词重叠的简单共识检测"""
        if len(solutions) < 2:
            return ConsensusResult(
                consensus_score=100,
                divergence_points=[],
                agreement_points=["单一专家，无需共识"],
                should_continue=False,
                recommendation="单一专家意见"
            )
        
        # 简单的关键词提取和比较
        all_words = []
        for s in solutions:
            words = set(s['solution'].split())
            all_words.append(words)
        
        # 计算共同词比例
        if all_words:
            common = all_words[0]
            for words in all_words[1:]:
                common = common & words
            
            total_unique = set()
            for words in all_words:
                total_unique |= words
            
            overlap_ratio = len(common) / max(len(total_unique), 1)
            score = min(100, overlap_ratio * 200)  # 放大到0-100
        else:
            score = 50
        
        return ConsensusResult(
            consensus_score=score,
            divergence_points=["无法详细分析"],
            agreement_points=["基础共识"],
            should_continue=score < self.consensus_threshold,
            recommendation="基于关键词分析"
        )
    
    async def suggest_focus(
        self,
        problem: str,
        divergence_points: List[str]
    ) -> str:
        """
        针对分歧点，建议下一轮讨论的焦点
        """
        if not divergence_points:
            return "已达成共识，无需进一步讨论"
        
        prompt = f"""【讨论焦点建议】

问题：{problem}
当前分歧点：
{chr(10).join(f'- {p}' for p in divergence_points)}

请建议下一轮讨论应该聚焦的核心问题（100字以内）："""
        
        try:
            result = await self.llm_client.get_completion_async(
                system_prompt="你是讨论引导专家",
                user_prompt=prompt,
                model="gemini-3-pro-preview"
            )
            return result
        except:
            return f"建议聚焦于：{divergence_points[0]}"


# 便捷函数
def should_continue_iteration(consensus_result: ConsensusResult, max_rounds: int, current_round: int) -> Tuple[bool, str]:
    """
    综合判断是否继续迭代
    
    Returns:
        (should_continue, reason)
    """
    if current_round >= max_rounds:
        return False, f"已达到最大迭代轮数 ({max_rounds})"
    
    if not consensus_result.should_continue:
        return False, f"已达成共识 (共识度: {consensus_result.consensus_score:.1f}%)"
    
    if consensus_result.consensus_score >= 90:
        return False, "高度共识，无需继续"
    
    return True, f"存在分歧 (共识度: {consensus_result.consensus_score:.1f}%)，继续讨论"
