"""
技术问题求解协调器

协调整个问题求解流程：
1. 意图分析
2. 专家匹配
3. 并行求解
4. 整合答案
"""
import asyncio
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass, field, asdict
import json
import time

from .intent_analyzer import IntentAnalyzer, ProblemIntent
from .expert_matcher import ExpertMatcher, MatchedExpert


@dataclass
class SubProblemSolution:
    """子问题解决方案"""
    expert_name: str
    expert_role: str
    sub_problem: str
    solution: str
    model: str = ""  # 使用的模型
    confidence: float = 0.0
    duration_ms: float = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProblemSolution:
    """完整问题解决方案"""
    original_problem: str
    intent: ProblemIntent
    matched_experts: List[MatchedExpert]
    sub_solutions: List[SubProblemSolution]
    final_solution: str
    total_duration_ms: float = 0
    
    def to_dict(self) -> dict:
        return {
            "original_problem": self.original_problem,
            "intent": self.intent.to_dict(),
            "matched_experts": [
                {"name": e.name, "role": e.role, "domain": e.matched_domain, "sub_problem": e.assigned_sub_problem}
                for e in self.matched_experts
            ],
            "sub_solutions": [s.to_dict() for s in self.sub_solutions],
            "final_solution": self.final_solution,
            "total_duration_ms": self.total_duration_ms
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class TechnicalProblemSolver:
    """
    技术问题求解专家
    
    完整流程：
    1. 意图分析 - 理解问题，识别领域
    2. 问题分解 - 将复杂问题拆解
    3. 专家匹配 - 选择合适的专家
    4. 并行求解 - 各专家同时处理子问题
    5. 整合答案 - 综合形成最终方案
    
    使用示例:
        solver = TechnicalProblemSolver(llm_client)
        solution = await solver.solve("空调噪音大如何解决？")
        print(solution.final_solution)
    """
    
    def __init__(self, llm_client, expert_catalog: List = None):
        self.llm_client = llm_client
        self.intent_analyzer = IntentAnalyzer(llm_client)
        self.expert_matcher = ExpertMatcher(expert_catalog)
    
    async def solve(
        self, 
        problem: str,
        selected_expert_indices: List[int] = None,
        max_experts: int = 5
    ) -> ProblemSolution:
        """
        求解技术问题（完整流程）
        
        Args:
            problem: 技术问题描述
            selected_expert_indices: 用户预选的专家索引（可选）
            max_experts: 最多使用的专家数量
        
        Returns:
            完整的问题解决方案
        """
        start_time = time.time()
        
        # 1. 意图分析
        intent = await self.intent_analyzer.analyze(problem)
        
        # 2. 专家匹配
        if selected_expert_indices:
            # 使用用户指定的专家
            matched_experts = []
            for idx in selected_expert_indices[:max_experts]:
                expert = self.expert_matcher.get_expert_by_index(idx)
                if expert:
                    matched_experts.append(MatchedExpert(
                        index=idx,
                        name=expert.name,
                        role=expert.role,
                        expertise=expert.expertise,
                        matched_domain="用户指定",
                        relevance_score=1.0
                    ))
        else:
            # 自动匹配
            matched_experts = self.expert_matcher.match_with_sub_problems(
                domains=intent.domains,
                sub_problems=intent.sub_problems,
                limit=max_experts
            )
        
        if not matched_experts:
            # 回退到默认专家
            matched_experts = self.expert_matcher.match_by_domains(["产品规划"], limit=1)
        
        # 3. 并行求解
        sub_solutions = await self._solve_parallel(problem, intent, matched_experts)
        
        # 4. 整合答案
        final_solution = await self._integrate_solutions(problem, intent, sub_solutions)
        
        total_duration = (time.time() - start_time) * 1000
        
        return ProblemSolution(
            original_problem=problem,
            intent=intent,
            matched_experts=matched_experts,
            sub_solutions=sub_solutions,
            final_solution=final_solution,
            total_duration_ms=total_duration
        )
    
    async def solve_stream(
        self,
        problem: str,
        selected_expert_indices: List[int] = None,
        max_experts: int = 5,
        iteration_rounds: int = 1  # 迭代轮数，1=无迭代，2+=反思验证
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        流式求解 - 逐步返回结果，支持迭代反思
        
        Yields:
            {"stage": "analyzing", "data": {...}}
            {"stage": "matching", "data": {...}}
            {"stage": "solving", "expert": "...", "solution": "..."}
            {"stage": "reflection", "round": N, "feedback": "..."}  # 新增
            {"stage": "integrating", "data": {...}}
            {"stage": "complete", "data": {...}}
        """
        start_time = time.time()
        
        # 1. 意图分析
        yield {"stage": "analyzing", "message": "正在分析问题意图..."}
        intent = await self.intent_analyzer.analyze(problem)
        yield {
            "stage": "analyzed", 
            "data": {
                "problem_type": intent.problem_type,
                "domains": intent.domains,
                "sub_problems": intent.sub_problems,
                "complexity": intent.complexity
            }
        }
        
        # 2. 专家匹配
        yield {"stage": "matching", "message": "正在匹配专家..."}
        if selected_expert_indices:
            matched_experts = []
            for idx in selected_expert_indices[:max_experts]:
                expert = self.expert_matcher.get_expert_by_index(idx)
                if expert:
                    matched_experts.append(MatchedExpert(
                        index=idx,
                        name=expert.name,
                        role=expert.role,
                        expertise=expert.expertise,
                        matched_domain="用户指定",
                        relevance_score=1.0
                    ))
        else:
            matched_experts = self.expert_matcher.match_with_sub_problems(
                domains=intent.domains,
                sub_problems=intent.sub_problems,
                limit=max_experts
            )
        
        yield {
            "stage": "matched",
            "data": {
                "experts": [
                    {"name": e.name, "role": e.role, "domain": e.matched_domain}
                    for e in matched_experts
                ]
            }
        }
        
        # 3. 并行求解
        yield {"stage": "solving", "message": f"正在并行求解（{len(matched_experts)}位专家）..."}
        
        sub_solutions = []
        tasks = []
        
        for expert in matched_experts:
            task = self._solve_single(problem, intent, expert)
            tasks.append((expert, task))
        
        # 并行执行，逐个返回结果
        results = await asyncio.gather(*[t[1] for t in tasks])
        
        for i, (expert, _) in enumerate(tasks):
            solution = results[i]
            sub_solutions.append(solution)
            yield {
                "stage": "expert_done",
                "expert": expert.name,
                "role": expert.role,
                "model": solution.model,
                "domain": expert.matched_domain,
                "solution": solution.solution  # 完整输出，不截断
            }
        
        # 4. 迭代反思验证（如果 iteration_rounds > 1）
        current_solutions = sub_solutions
        for round_num in range(2, iteration_rounds + 1):
            yield {
                "stage": "reflection_start",
                "round": round_num,
                "message": f"🔄 开始第 {round_num} 轮反思验证..."
            }
            
            # 4a. 反思阶段 - 评估当前方案
            reflection = await self._reflect_on_solutions(problem, intent, current_solutions)
            yield {
                "stage": "reflection",
                "round": round_num,
                "feedback": reflection[:300] + "..." if len(reflection) > 300 else reflection
            }
            
            # 4b. 改进阶段 - 根据反思优化方案
            improved_solutions = await self._improve_solutions(
                problem, intent, current_solutions, reflection, matched_experts
            )
            
            for i, (expert, improved) in enumerate(zip(matched_experts, improved_solutions)):
                yield {
                    "stage": "improvement",
                    "round": round_num,
                    "expert": expert.name,
                    "improved": improved.solution[:150] + "..." if len(improved.solution) > 150 else improved.solution
                }
            
            current_solutions = improved_solutions
            
            # 4c. 验证阶段
            validation = await self._validate_solutions(problem, intent, current_solutions)
            yield {
                "stage": "validation",
                "round": round_num,
                "result": validation
            }
        
        # 5. 专家讨论轮（如果 iteration_rounds >= 2）
        all_discussions = []
        if iteration_rounds >= 2:
            yield {"stage": "discussion_start", "message": "💬 开始专家讨论..."}
            
            discussions = await self._run_discussion_round(
                problem, intent, current_solutions, matched_experts, round_num=1
            )
            all_discussions = discussions
            
            for d in discussions:
                yield {
                    "stage": "discussion",
                    "expert": d["expert"],
                    "role": d["role"],
                    "comment": d["comment"]
                }
        
        # 6. 批评与辩论轮
        critique_result = {}
        if iteration_rounds >= 2:
            yield {"stage": "critique_start", "message": "⚔️ 开始技术批评与辩论..."}
            
            critique_result = await self._run_critique_round(
                problem, intent, current_solutions, matched_experts
            )
            
            yield {
                "stage": "critique",
                "critique": critique_result["critique"]
            }
            
            for resp in critique_result.get("responses", []):
                yield {
                    "stage": "critique_response",
                    "expert": resp["expert"],
                    "response": resp["response"]
                }
        
        # 7. 多维度评估
        if iteration_rounds >= 2:
            yield {"stage": "evaluation_start", "message": "📊 开始多维度评估..."}
            
            evaluation = await self._run_evaluation(
                problem, intent, current_solutions, all_discussions, critique_result
            )
            
            yield {
                "stage": "evaluation",
                "data": evaluation
            }
        
        # 8. 整合最终答案
        yield {"stage": "integrating", "message": "正在整合最终解决方案..."}
        final_solution = await self._integrate_solutions(problem, intent, current_solutions)
        
        total_duration = (time.time() - start_time) * 1000
        
        yield {
            "stage": "complete",
            "data": {
                "final_solution": final_solution,
                "total_duration_ms": total_duration,
                "expert_count": len(matched_experts),
                "iteration_rounds": iteration_rounds
            }
        }
    
    async def _solve_single(
        self, 
        problem: str, 
        intent: ProblemIntent,
        expert: MatchedExpert
    ) -> SubProblemSolution:
        """单个专家求解"""
        start_time = time.time()
        
        sub_problem = expert.assigned_sub_problem or problem
        
        prompt = f"""【技术问题深度分析与求解】

你是{expert.name}，专业领域是{expert.expertise}。
请对以下问题进行**深入、全面、系统**的分析，展示完整的推理过程。

【原始问题】
{problem}

【问题类型】{intent.problem_type}
【你负责的子问题】
{sub_problem}

【分析要求】
请按以下结构输出，**不限制字数**，务必详尽完整：

## 1. 问题理解与推理过程
- 首先，阐述你对这个问题的理解
- 展示你的思考过程：为什么会出现这个问题？
- 列出关键的技术要素和约束条件
- 说明你的推理链条：从问题到解决方案的逻辑路径

## 2. 根因分析
- 从你的专业角度，深入分析问题产生的根本原因
- 涉及的技术原理、物理机制、系统机理
- 隐藏因素和容易被忽视的关键点
- 问题的相互关联性和系统性影响

## 3. 详细解决方案
针对每个可行方案，请详细说明：
- **方案描述**：具体做什么、怎么做
- **技术原理**：为什么这个方案有效
- **实施步骤**：详细的执行步骤，可操作
- **所需资源**：技术、设备、材料、人力
- **预期效果**：量化的改善预期
- **优缺点分析**：客观评估

## 4. 风险评估与应对
- 每个方案可能遇到的技术障碍
- 实施过程中的风险点及概率
- 应急预案和兜底措施
- 失败后的回退策略

## 5. 跨领域协作
- 需要哪些其他专业配合
- 具体的接口定义和交付物
- 协作时序和里程碑
- 沟通协调要点

## 6. 结论与建议
- 综合推荐的最优方案
- 实施优先级建议
- 长期优化方向

请给出你的完整专业解答，展示专家级的深度思考："""
        
        # 使用 gemini-3-pro-preview 作为默认模型
        model = "gemini-3-pro-preview"
        
        try:
            solution = await self.llm_client.get_completion_async(
                system_prompt=f"你是{expert.role}，擅长{expert.expertise}。请展示完整的推理过程，给出详尽、专业、可操作的解决方案。不要限制篇幅，确保方案完整。",
                user_prompt=prompt,
                model=model
            )
        except Exception as e:
            solution = f"[求解失败] {str(e)}"
        
        duration = (time.time() - start_time) * 1000
        
        return SubProblemSolution(
            expert_name=expert.name,
            expert_role=expert.role,
            sub_problem=sub_problem,
            solution=solution,
            model=model,
            confidence=0.8,
            duration_ms=duration
        )
    
    async def _solve_parallel(
        self,
        problem: str,
        intent: ProblemIntent,
        experts: List[MatchedExpert]
    ) -> List[SubProblemSolution]:
        """并行求解所有子问题"""
        tasks = [
            self._solve_single(problem, intent, expert)
            for expert in experts
        ]
        return await asyncio.gather(*tasks)
    
    async def _integrate_solutions(
        self,
        problem: str,
        intent: ProblemIntent,
        sub_solutions: List[SubProblemSolution]
    ) -> str:
        """整合各专家的解决方案"""
        solutions_text = "\n\n".join([
            f"【{s.expert_name}（{s.expert_role}）】\n{s.solution}"
            for s in sub_solutions
        ])
        
        prompt = f"""请整合以下各专家的解决方案，形成一份完整的技术解决方案。

【原始问题】
{problem}

【问题类型】{intent.problem_type}
【涉及领域】{", ".join(intent.domains)}

【各专家解答】
{solutions_text}

【整合要求】
请生成一份结构化的解决方案，包括：

## 📋 问题摘要
简述问题核心

## 🎯 解决方案
整合各专家建议，形成可执行的方案

## 📝 实施步骤
1. ...
2. ...

## ⚠️ 注意事项
关键风险和注意点

## 💡 后续优化建议
可选的进一步改进方向

请用中文输出："""
        
        try:
            result = await self.llm_client.get_completion_async(
                system_prompt="你是技术方案整合专家，擅长综合多个专业领域的意见形成可执行方案。",
                user_prompt=prompt,
                model="gemini-3-pro-preview"
            )
            return result
        except Exception as e:
            # 简单拼接
            return f"## 综合解决方案\n\n{solutions_text}"
    
    async def _reflect_on_solutions(
        self,
        problem: str,
        intent: ProblemIntent,
        solutions: List[SubProblemSolution]
    ) -> str:
        """反思评估当前方案"""
        solutions_text = "\n".join([
            f"【{s.expert_name}】{s.solution[:200]}"
            for s in solutions
        ])
        
        prompt = f"""请对以下技术问题的解决方案进行反思评估：

【原始问题】{problem}
【问题类型】{intent.problem_type}

【当前方案】
{solutions_text}

请从以下角度进行反思：
1. 方案的完整性 - 是否覆盖了所有关键点？
2. 可行性 - 实施难度和资源需求如何？
3. 潜在风险 - 可能存在什么问题？
4. 创新性 - 有没有更好的思路？
5. 协同性 - 各专家方案是否相互配合？

请给出具体的改进建议（200字以内）："""
        
        try:
            return await self.llm_client.get_completion_async(
                system_prompt="你是技术方案评审专家，擅长发现问题并提出改进建议。",
                user_prompt=prompt,
                model="gemini-3-pro-preview"
            )
        except Exception as e:
            return f"反思失败: {str(e)}"
    
    async def _improve_solutions(
        self,
        problem: str,
        intent: ProblemIntent,
        solutions: List[SubProblemSolution],
        reflection: str,
        experts: List[MatchedExpert]
    ) -> List[SubProblemSolution]:
        """根据反思改进方案"""
        improved = []
        
        for solution, expert in zip(solutions, experts):
            prompt = f"""根据反思意见，优化你之前的方案：

【原始问题】{problem}
【你之前的方案】{solution.solution}

【反思意见】{reflection}

请优化你的方案，提升完整性、可行性、消除风险（150字以内）："""
            
            try:
                improved_solution = await self.llm_client.get_completion_async(
                    system_prompt=f"你是{expert.role}，请根据反馈优化方案。",
                    user_prompt=prompt,
                    model="gemini-3-pro-preview"
                )
                improved.append(SubProblemSolution(
                    expert_name=solution.expert_name,
                    expert_role=solution.expert_role,
                    sub_problem=solution.sub_problem,
                    solution=improved_solution,
                    model="gemini-3-pro-preview",
                    confidence=0.9,
                    duration_ms=0
                ))
            except:
                improved.append(solution)
        
        return improved
    
    async def _validate_solutions(
        self,
        problem: str,
        intent: ProblemIntent,
        solutions: List[SubProblemSolution]
    ) -> dict:
        """验证改进后的方案"""
        solutions_text = "\n".join([
            f"【{s.expert_name}】{s.solution[:150]}"
            for s in solutions
        ])
        
        prompt = f"""验证以下技术方案是否满足要求：

【原始问题】{problem}
【方案】
{solutions_text}

请评估：
1. 是否解决了核心问题？（是/部分/否）
2. 实施可行性？（高/中/低）
3. 还有遗漏吗？（有/无）

请用JSON格式返回，只返回JSON：
{{"solved": "是/部分/否", "feasibility": "高/中/低", "gaps": "有/无", "score": 0-100}}"""
        
        try:
            result = await self.llm_client.get_completion_async(
                system_prompt="你是技术方案验证专家，只返回JSON。",
                user_prompt=prompt,
                model="gemini-3-pro-preview"
            )
            # Try to parse JSON
            import re
            json_match = re.search(r'\{[^}]+\}', result)
            if json_match:
                return json.loads(json_match.group())
            return {"solved": "部分", "feasibility": "中", "gaps": "有", "score": 70}
        except:
            return {"solved": "部分", "feasibility": "中", "gaps": "有", "score": 70}
    
    async def _run_discussion_round(
        self,
        problem: str,
        intent: ProblemIntent,
        solutions: List[SubProblemSolution],
        experts: List[MatchedExpert],
        round_num: int
    ) -> List[dict]:
        """
        专家讨论轮 - 每位专家看到其他专家的方案并评论
        
        Returns:
            List of discussion comments from each expert
        """
        # 构建所有方案摘要
        all_solutions_text = "\n\n".join([
            f"【{s.expert_name}的方案】\n{s.solution[:500]}"
            for s in solutions
        ])
        
        discussions = []
        
        for i, (expert, solution) in enumerate(zip(experts, solutions)):
            # 其他专家的方案
            other_solutions = [s for j, s in enumerate(solutions) if j != i]
            others_text = "\n\n".join([
                f"【{s.expert_name}】{s.solution[:400]}"
                for s in other_solutions
            ])
            
            prompt = f"""【专家讨论 - 第{round_num}轮】

你是{expert.name}，你已经给出了自己的初步方案。
现在请评论其他专家的方案，并完善你自己的思路。

【原始问题】{problem}

【你的方案摘要】
{solution.solution[:400]}

【其他专家的方案】
{others_text}

【讨论要求】
1. 对其他专家方案的**优点**进行肯定（50字）
2. 指出其他方案的**潜在问题或不足**（100字）
3. 提出**建设性补充建议**（100字）
4. 说明你的方案如何与其他方案**协同配合**（50字）

请直接输出你的评论："""
            
            try:
                comment = await self.llm_client.get_completion_async(
                    system_prompt=f"你是{expert.role}，正在与其他专家进行技术讨论。保持专业、客观、建设性。",
                    user_prompt=prompt,
                    model="gemini-3-pro-preview"
                )
                discussions.append({
                    "expert": expert.name,
                    "role": expert.role,
                    "comment": comment
                })
            except Exception as e:
                discussions.append({
                    "expert": expert.name,
                    "role": expert.role,
                    "comment": f"[讨论失败] {str(e)}"
                })
        
        return discussions
    
    async def _run_critique_round(
        self,
        problem: str,
        intent: ProblemIntent,
        solutions: List[SubProblemSolution],
        experts: List[MatchedExpert]
    ) -> dict:
        """
        批评与辩论轮 - 批评者挑战所有方案，专家回应
        
        Returns:
            {"critique": str, "responses": [{"expert": str, "response": str}]}
        """
        # 构建方案摘要
        solutions_text = "\n\n".join([
            f"【{s.expert_name}】\n{s.solution[:400]}"
            for s in solutions
        ])
        
        # 1. 批评者提出挑战
        critique_prompt = f"""【技术方案批评】

作为独立的技术评审专家，请对以下解决方案进行**严格、深入的技术批评**。

【原始问题】{problem}
【问题类型】{intent.problem_type}

【各专家方案】
{solutions_text}

【批评要求】
请从以下角度进行挑战性批评：
1. **技术可行性**：方案是否存在技术漏洞或不可行之处？
2. **完整性**：是否有重要因素被遗漏？
3. **成本效益**：方案的投入产出比是否合理？
4. **风险**：有哪些潜在风险没有被充分考虑？
5. **创新性**：是否有更好的替代方案？

请给出尖锐但专业的批评（300字）："""
        
        try:
            critique = await self.llm_client.get_completion_async(
                system_prompt="你是严格的技术评审专家，善于发现方案的问题和漏洞。请直接指出问题，不要客套。",
                user_prompt=critique_prompt,
                model="gemini-3-pro-preview"
            )
        except Exception as e:
            critique = f"[批评生成失败] {str(e)}"
        
        # 2. 各专家回应批评
        responses = []
        for expert, solution in zip(experts, solutions):
            response_prompt = f"""【回应技术批评】

你是{expert.name}，你的方案受到了以下批评：

【批评内容】
{critique}

【你的原方案摘要】
{solution.solution[:400]}

请回应这些批评，说明：
1. 哪些批评有道理，你会如何改进
2. 哪些批评可能存在误解，你如何解释
3. 补充任何之前遗漏的考虑

请给出你的回应（200字）："""
            
            try:
                response = await self.llm_client.get_completion_async(
                    system_prompt=f"你是{expert.role}，正在回应技术批评。保持专业，承认合理批评，但也要为合理的设计决策辩护。",
                    user_prompt=response_prompt,
                    model="gemini-3-pro-preview"
                )
                responses.append({
                    "expert": expert.name,
                    "response": response
                })
            except Exception as e:
                responses.append({
                    "expert": expert.name,
                    "response": f"[回应失败] {str(e)}"
                })
        
        return {
            "critique": critique,
            "responses": responses
        }
    
    async def _run_evaluation(
        self,
        problem: str,
        intent: ProblemIntent,
        solutions: List[SubProblemSolution],
        discussions: List[dict],
        critique_result: dict
    ) -> dict:
        """
        多维度评估 - 对讨论后的方案进行综合评估
        
        Returns:
            {
                "dimensions": {"feasibility": N, "risk": N, "cost": N, "innovation": N},
                "ranking": ["expert1", "expert2", ...],
                "summary": str
            }
        """
        # 构建完整上下文
        solutions_text = "\n".join([
            f"【{s.expert_name}】{s.solution[:300]}"
            for s in solutions
        ])
        
        discussions_text = "\n".join([
            f"【{d['expert']}讨论】{d['comment'][:200]}"
            for d in discussions
        ]) if discussions else "无讨论记录"
        
        prompt = f"""【技术方案综合评估】

请对以下技术方案进行多维度评估。

【问题】{problem}

【各专家方案】
{solutions_text}

【专家讨论要点】
{discussions_text}

【批评与回应】
{critique_result.get('critique', '无')[:300]}

【评估要求】
请输出JSON格式评估结果：
{{
    "feasibility": {{
        "score": 0-100,
        "comment": "可行性评价"
    }},
    "risk": {{
        "score": 0-100,  // 分数越高风险越低
        "comment": "风险评价"
    }},
    "cost": {{
        "score": 0-100,  // 分数越高成本越低
        "comment": "成本评价"
    }},
    "innovation": {{
        "score": 0-100,
        "comment": "创新性评价"
    }},
    "ranking": ["方案最优的专家名", "第二...", "..."],
    "overall_score": 0-100,
    "recommendation": "最终推荐意见（100字）"
}}

请只输出JSON："""
        
        try:
            result = await self.llm_client.get_completion_async(
                system_prompt="你是技术方案评估专家，请输出严格的JSON格式评估结果。",
                user_prompt=prompt,
                model="gemini-3-pro-preview"
            )
            # 尝试解析JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            return {
                "overall_score": 75,
                "recommendation": "方案总体可行，建议综合各专家意见实施。"
            }
        except Exception as e:
            return {
                "overall_score": 70,
                "recommendation": f"评估失败: {str(e)}"
            }

