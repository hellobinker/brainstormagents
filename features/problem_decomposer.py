"""
增强问题分解器

多层问题分解：
- 第一层：识别问题类型和主要矛盾
- 第二层：分解为技术子问题
- 第三层：识别子问题间的依赖关系
"""
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class SubProblem:
    """子问题"""
    id: str
    description: str
    domain: str
    priority: int  # 1=最高优先级
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他子问题ID
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "domain": self.domain,
            "priority": self.priority,
            "dependencies": self.dependencies
        }


@dataclass
class DecomposedProblem:
    """分解后的问题"""
    original: str
    problem_type: str
    main_contradiction: str  # 主要矛盾
    root_cause_hypothesis: str  # 根因假设
    sub_problems: List[SubProblem] = field(default_factory=list)
    solving_order: List[str] = field(default_factory=list)  # 建议的求解顺序
    
    def to_dict(self) -> dict:
        return {
            "original": self.original,
            "problem_type": self.problem_type,
            "main_contradiction": self.main_contradiction,
            "root_cause_hypothesis": self.root_cause_hypothesis,
            "sub_problems": [sp.to_dict() for sp in self.sub_problems],
            "solving_order": self.solving_order
        }


class EnhancedProblemDecomposer:
    """
    增强问题分解器
    
    使用 Chain-of-Thought 方法进行多层问题分解
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def decompose(self, problem: str) -> DecomposedProblem:
        """
        多层问题分解
        
        Returns:
            DecomposedProblem 包含问题类型、主要矛盾、子问题及依赖关系
        """
        prompt = f"""【问题深度分解】

请对以下技术问题进行深度分解分析。

【原始问题】
{problem}

请按以下步骤思考并输出 JSON：

**第一步：识别问题类型和主要矛盾**
- 这是什么类型的问题？（优化/故障排除/设计/决策/...）
- 问题的主要矛盾是什么？（核心冲突点）
- 根据问题描述，推测可能的根因假设

**第二步：分解为技术子问题**
- 将问题分解为3-5个可独立分析的技术子问题
- 每个子问题明确所属技术领域
- 评估每个子问题的优先级

**第三步：识别依赖关系**
- 哪些子问题之间有依赖？
- 建议的求解顺序是什么？

请输出JSON格式：
{{
    "problem_type": "问题类型",
    "main_contradiction": "主要矛盾描述",
    "root_cause_hypothesis": "根因假设",
    "sub_problems": [
        {{
            "id": "SP1",
            "description": "子问题描述",
            "domain": "所属技术领域",
            "priority": 1,
            "dependencies": []
        }},
        {{
            "id": "SP2",
            "description": "子问题描述",
            "domain": "所属技术领域", 
            "priority": 2,
            "dependencies": ["SP1"]
        }}
    ],
    "solving_order": ["SP1", "SP2", "SP3"]
}}

只返回JSON："""
        
        try:
            result = await self.llm_client.get_completion_async(
                system_prompt="你是问题分解专家，擅长将复杂问题拆解为可管理的子问题。只返回JSON。",
                user_prompt=prompt,
                model="gemini-3-pro-preview"
            )
            
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                data = json.loads(json_match.group())
                
                sub_problems = [
                    SubProblem(
                        id=sp.get("id", f"SP{i}"),
                        description=sp.get("description", ""),
                        domain=sp.get("domain", "通用"),
                        priority=sp.get("priority", i + 1),
                        dependencies=sp.get("dependencies", [])
                    )
                    for i, sp in enumerate(data.get("sub_problems", []))
                ]
                
                return DecomposedProblem(
                    original=problem,
                    problem_type=data.get("problem_type", "技术问题"),
                    main_contradiction=data.get("main_contradiction", ""),
                    root_cause_hypothesis=data.get("root_cause_hypothesis", ""),
                    sub_problems=sub_problems,
                    solving_order=data.get("solving_order", [sp.id for sp in sub_problems])
                )
        except Exception as e:
            print(f"[WARN] Problem decomposition failed: {e}")
        
        # 降级
        return DecomposedProblem(
            original=problem,
            problem_type="技术问题",
            main_contradiction="需要进一步分析",
            root_cause_hypothesis="待确定",
            sub_problems=[
                SubProblem(id="SP1", description=problem, domain="通用", priority=1)
            ],
            solving_order=["SP1"]
        )
    
    def get_expert_context(self, decomposed: DecomposedProblem, sub_problem_id: str) -> str:
        """
        为专家生成带上下文的问题描述
        
        包含主矛盾、依赖子问题等上下文信息
        """
        sp = next((s for s in decomposed.sub_problems if s.id == sub_problem_id), None)
        if not sp:
            return decomposed.original
        
        context = f"""【问题上下文】
主要矛盾：{decomposed.main_contradiction}
根因假设：{decomposed.root_cause_hypothesis}

【你负责的子问题】
{sp.description}

【技术领域】{sp.domain}
【优先级】{sp.priority}
"""
        
        if sp.dependencies:
            dep_descriptions = [
                s.description for s in decomposed.sub_problems 
                if s.id in sp.dependencies
            ]
            if dep_descriptions:
                context += f"\n【依赖的前置问题】\n" + "\n".join(f"- {d}" for d in dep_descriptions)
        
        return context
