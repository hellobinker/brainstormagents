"""
多种协作模式

支持不同的专家协作方式：
- parallel: 并行求解（当前默认）
- sequential: 串行接力
- hierarchical: 分层决策
- debate: 对抗辩论
"""
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any, AsyncIterator
from enum import Enum


class CollaborationMode(Enum):
    """协作模式"""
    PARALLEL = "parallel"       # 并行：所有专家同时求解
    SEQUENTIAL = "sequential"   # 串行：专家依次接力
    HIERARCHICAL = "hierarchical"  # 分层：技术→评审→决策
    DEBATE = "debate"           # 对抗：正方vs反方辩论


@dataclass
class CollaborationConfig:
    """协作配置"""
    mode: CollaborationMode = CollaborationMode.PARALLEL
    sequential_order: List[str] = None  # 串行模式的专家顺序
    hierarchy_levels: List[str] = None  # 分层模式的层级定义
    debate_rounds: int = 2              # 辩论轮数


class CollaborationOrchestrator:
    """
    协作编排器
    
    根据不同的协作模式，编排专家的交互方式
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def orchestrate(
        self,
        mode: CollaborationMode,
        problem: str,
        experts: List[Any],
        solve_func,
        config: CollaborationConfig = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        编排专家协作
        
        Args:
            mode: 协作模式
            problem: 问题
            experts: 专家列表
            solve_func: 单专家求解函数
            config: 协作配置
        """
        if mode == CollaborationMode.PARALLEL:
            async for event in self._parallel_mode(problem, experts, solve_func):
                yield event
        elif mode == CollaborationMode.SEQUENTIAL:
            async for event in self._sequential_mode(problem, experts, solve_func):
                yield event
        elif mode == CollaborationMode.HIERARCHICAL:
            async for event in self._hierarchical_mode(problem, experts, solve_func):
                yield event
        elif mode == CollaborationMode.DEBATE:
            async for event in self._debate_mode(problem, experts, solve_func, config):
                yield event
    
    async def _parallel_mode(self, problem, experts, solve_func) -> AsyncIterator[Dict]:
        """并行模式：所有专家同时求解"""
        yield {"stage": "collab_mode", "mode": "parallel", "message": "⚡ 并行模式：所有专家同时分析"}
        
        tasks = [solve_func(expert) for expert in experts]
        results = await asyncio.gather(*tasks)
        
        for expert, result in zip(experts, results):
            yield {
                "stage": "expert_solution",
                "expert": expert.name,
                "solution": result
            }
    
    async def _sequential_mode(self, problem, experts, solve_func) -> AsyncIterator[Dict]:
        """串行模式：专家依次接力，后者可看到前者结论"""
        yield {"stage": "collab_mode", "mode": "sequential", "message": "🔗 串行模式：专家依次接力分析"}
        
        accumulated_context = ""
        
        for i, expert in enumerate(experts):
            yield {
                "stage": "sequential_turn",
                "expert": expert.name,
                "order": i + 1,
                "total": len(experts)
            }
            
            # 传递前序专家的结论
            result = await solve_func(expert, previous_context=accumulated_context)
            accumulated_context += f"\n\n【{expert.name}的结论】\n{result[:500]}"
            
            yield {
                "stage": "expert_solution",
                "expert": expert.name,
                "solution": result,
                "order": i + 1
            }
    
    async def _hierarchical_mode(self, problem, experts, solve_func) -> AsyncIterator[Dict]:
        """分层模式：技术层→评审层→决策层"""
        yield {"stage": "collab_mode", "mode": "hierarchical", "message": "📊 分层模式：技术→评审→决策"}
        
        # 分层
        tech_experts = experts[:-2] if len(experts) > 2 else experts
        reviewer = experts[-2] if len(experts) > 1 else None
        decision_maker = experts[-1] if len(experts) > 0 else None
        
        # 第一层：技术分析
        yield {"stage": "hierarchy_level", "level": "技术分析层", "experts": [e.name for e in tech_experts]}
        tech_results = await asyncio.gather(*[solve_func(e) for e in tech_experts])
        
        for expert, result in zip(tech_experts, tech_results):
            yield {"stage": "expert_solution", "expert": expert.name, "solution": result, "level": "技术"}
        
        # 第二层：技术评审
        if reviewer:
            yield {"stage": "hierarchy_level", "level": "技术评审层", "experts": [reviewer.name]}
            review_context = "\n".join([f"【{e.name}】{r[:300]}" for e, r in zip(tech_experts, tech_results)])
            review_result = await solve_func(reviewer, previous_context=f"请评审以下技术方案：\n{review_context}")
            yield {"stage": "expert_solution", "expert": reviewer.name, "solution": review_result, "level": "评审"}
        
        # 第三层：决策建议
        if decision_maker:
            yield {"stage": "hierarchy_level", "level": "决策建议层", "experts": [decision_maker.name]}
            decision_result = await solve_func(decision_maker, previous_context="请综合以上分析给出最终决策建议")
            yield {"stage": "expert_solution", "expert": decision_maker.name, "solution": decision_result, "level": "决策"}
    
    async def _debate_mode(self, problem, experts, solve_func, config) -> AsyncIterator[Dict]:
        """对抗辩论模式：正方vs反方"""
        yield {"stage": "collab_mode", "mode": "debate", "message": "⚔️ 辩论模式：正反方对抗论证"}
        
        rounds = config.debate_rounds if config else 2
        
        # 分成正反两方
        mid = len(experts) // 2
        pro_team = experts[:mid] if mid > 0 else [experts[0]]
        con_team = experts[mid:] if mid < len(experts) else [experts[-1]]
        
        yield {
            "stage": "debate_teams",
            "pro_team": [e.name for e in pro_team],
            "con_team": [e.name for e in con_team]
        }
        
        debate_history = ""
        
        for round_num in range(1, rounds + 1):
            yield {"stage": "debate_round", "round": round_num}
            
            # 正方论述
            for expert in pro_team:
                pro_prompt = f"【第{round_num}轮辩论-正方】\n请论证你的方案的优势和可行性。\n之前讨论：{debate_history[-500:]}"
                result = await solve_func(expert, previous_context=pro_prompt)
                debate_history += f"\n[正方-{expert.name}] {result[:300]}"
                yield {"stage": "debate_argument", "side": "pro", "expert": expert.name, "argument": result}
            
            # 反方质疑
            for expert in con_team:
                con_prompt = f"【第{round_num}轮辩论-反方】\n请指出对方方案的问题和风险。\n之前讨论：{debate_history[-500:]}"
                result = await solve_func(expert, previous_context=con_prompt)
                debate_history += f"\n[反方-{expert.name}] {result[:300]}"
                yield {"stage": "debate_argument", "side": "con", "expert": expert.name, "argument": result}
        
        # 辩论总结
        yield {"stage": "debate_summary", "message": "辩论结束，综合双方观点形成结论"}


# 便捷函数
def get_collaboration_mode(mode_str: str) -> CollaborationMode:
    """从字符串获取协作模式"""
    mode_map = {
        "parallel": CollaborationMode.PARALLEL,
        "sequential": CollaborationMode.SEQUENTIAL,
        "hierarchical": CollaborationMode.HIERARCHICAL,
        "debate": CollaborationMode.DEBATE
    }
    return mode_map.get(mode_str.lower(), CollaborationMode.PARALLEL)
