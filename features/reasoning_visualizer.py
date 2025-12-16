"""
推理可视化

生成专家推理链的可视化数据，支持前端展示
"""
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class ReasoningNode:
    """推理链节点"""
    id: str
    type: str  # "problem", "analysis", "solution", "risk", "decision"
    label: str
    content: str
    expert: Optional[str] = None
    confidence: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "content": self.content,
            "expert": self.expert,
            "confidence": self.confidence,
            "timestamp": self.timestamp
        }


@dataclass
class ReasoningEdge:
    """推理链边（关系）"""
    source: str
    target: str
    relation: str  # "leads_to", "supports", "contradicts", "refines"
    weight: float = 1.0
    
    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "weight": self.weight
        }


@dataclass
class ReasoningChain:
    """完整推理链"""
    problem_id: str
    nodes: List[ReasoningNode] = field(default_factory=list)
    edges: List[ReasoningEdge] = field(default_factory=list)
    
    def add_node(self, node: ReasoningNode):
        self.nodes.append(node)
    
    def add_edge(self, edge: ReasoningEdge):
        self.edges.append(edge)
    
    def to_dict(self) -> dict:
        return {
            "problem_id": self.problem_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges]
        }
    
    def to_mermaid(self) -> str:
        """生成Mermaid图表格式"""
        lines = ["graph TD"]
        
        # 节点
        for node in self.nodes:
            shape = {
                "problem": f"(({node.label}))",
                "analysis": f"[{node.label}]",
                "solution": f"[/{node.label}/]",
                "risk": f"{{{{{node.label}}}}}",
                "decision": f">{node.label}]"
            }.get(node.type, f"[{node.label}]")
            lines.append(f"    {node.id}{shape}")
        
        # 边
        for edge in self.edges:
            arrow = {
                "leads_to": "-->",
                "supports": "-.->",
                "contradicts": "--x",
                "refines": "==>"
            }.get(edge.relation, "-->")
            lines.append(f"    {edge.source} {arrow}|{edge.relation}| {edge.target}")
        
        return "\n".join(lines)


class ReasoningVisualizer:
    """
    推理可视化器
    
    从专家讨论中提取推理链，生成可视化数据
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self._node_counter = 0
    
    def _generate_node_id(self, prefix: str = "node") -> str:
        self._node_counter += 1
        return f"{prefix}_{self._node_counter}"
    
    def build_chain_from_solutions(
        self,
        problem: str,
        solutions: List[Dict[str, Any]]
    ) -> ReasoningChain:
        """
        从专家解决方案构建推理链
        
        Args:
            problem: 原问题
            solutions: [{"expert": name, "solution": content, ...}]
        """
        chain = ReasoningChain(problem_id=self._generate_node_id("problem"))
        
        # 添加问题节点
        problem_node = ReasoningNode(
            id=chain.problem_id,
            type="problem",
            label="原始问题",
            content=problem[:200]
        )
        chain.add_node(problem_node)
        
        # 为每个专家添加分析节点
        for sol in solutions:
            expert_name = sol.get("expert", "专家")
            solution_content = sol.get("solution", "")
            
            # 分析节点
            analysis_id = self._generate_node_id("analysis")
            analysis_node = ReasoningNode(
                id=analysis_id,
                type="analysis",
                label=f"{expert_name}分析",
                content=self._extract_analysis(solution_content),
                expert=expert_name,
                confidence=0.8
            )
            chain.add_node(analysis_node)
            chain.add_edge(ReasoningEdge(
                source=chain.problem_id,
                target=analysis_id,
                relation="leads_to"
            ))
            
            # 方案节点
            solution_id = self._generate_node_id("solution")
            solution_node = ReasoningNode(
                id=solution_id,
                type="solution",
                label=f"{expert_name}方案",
                content=self._extract_solution(solution_content),
                expert=expert_name,
                confidence=0.75
            )
            chain.add_node(solution_node)
            chain.add_edge(ReasoningEdge(
                source=analysis_id,
                target=solution_id,
                relation="leads_to"
            ))
            
            # 风险节点
            risk_content = self._extract_risk(solution_content)
            if risk_content:
                risk_id = self._generate_node_id("risk")
                risk_node = ReasoningNode(
                    id=risk_id,
                    type="risk",
                    label=f"{expert_name}风险",
                    content=risk_content,
                    expert=expert_name
                )
                chain.add_node(risk_node)
                chain.add_edge(ReasoningEdge(
                    source=solution_id,
                    target=risk_id,
                    relation="leads_to"
                ))
        
        return chain
    
    def _extract_analysis(self, content: str) -> str:
        """提取分析部分"""
        # 简单的启发式提取
        for marker in ["问题理解", "根因分析", "分析", "问题"]:
            if marker in content:
                start = content.find(marker)
                end = content.find("##", start + 1)
                if end == -1:
                    end = min(start + 500, len(content))
                return content[start:end].strip()[:300]
        return content[:200]
    
    def _extract_solution(self, content: str) -> str:
        """提取方案部分"""
        for marker in ["解决方案", "方案", "建议"]:
            if marker in content:
                start = content.find(marker)
                end = content.find("##", start + 1)
                if end == -1:
                    end = min(start + 500, len(content))
                return content[start:end].strip()[:300]
        return content[200:400] if len(content) > 200 else content
    
    def _extract_risk(self, content: str) -> str:
        """提取风险部分"""
        for marker in ["风险", "挑战", "障碍"]:
            if marker in content:
                start = content.find(marker)
                end = content.find("##", start + 1)
                if end == -1:
                    end = min(start + 300, len(content))
                return content[start:end].strip()[:200]
        return ""
    
    async def build_chain_with_llm(
        self,
        problem: str,
        solutions: List[Dict[str, Any]]
    ) -> ReasoningChain:
        """
        使用LLM智能提取推理链（更准确）
        """
        if not self.llm_client:
            return self.build_chain_from_solutions(problem, solutions)
        
        solutions_text = "\n\n".join([
            f"【{s.get('expert', '专家')}】\n{s.get('solution', '')[:600]}"
            for s in solutions
        ])
        
        prompt = f"""【推理链提取】

请从以下专家讨论中提取推理链结构。

【问题】{problem}

【专家分析】
{solutions_text}

请提取推理链，输出JSON格式：
{{
    "nodes": [
        {{"id": "p1", "type": "problem", "label": "问题描述", "content": "..."}},
        {{"id": "a1", "type": "analysis", "label": "分析1", "content": "...", "expert": "专家名"}},
        {{"id": "s1", "type": "solution", "label": "方案1", "content": "...", "expert": "专家名"}},
        {{"id": "r1", "type": "risk", "label": "风险1", "content": "...", "expert": "专家名"}}
    ],
    "edges": [
        {{"source": "p1", "target": "a1", "relation": "leads_to"}},
        {{"source": "a1", "target": "s1", "relation": "leads_to"}}
    ]
}}

请只返回JSON："""
        
        try:
            result = await self.llm_client.get_completion_async(
                system_prompt="你是推理链分析专家，擅长从讨论中提取结构化的推理路径。只返回JSON。",
                user_prompt=prompt,
                model="gemini-3-pro-preview"
            )
            
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                data = json.loads(json_match.group())
                chain = ReasoningChain(problem_id="p1")
                
                for n in data.get("nodes", []):
                    chain.add_node(ReasoningNode(
                        id=n.get("id", self._generate_node_id()),
                        type=n.get("type", "analysis"),
                        label=n.get("label", ""),
                        content=n.get("content", ""),
                        expert=n.get("expert")
                    ))
                
                for e in data.get("edges", []):
                    chain.add_edge(ReasoningEdge(
                        source=e.get("source", ""),
                        target=e.get("target", ""),
                        relation=e.get("relation", "leads_to")
                    ))
                
                return chain
        except Exception as e:
            print(f"[WARN] LLM reasoning extraction failed: {e}")
        
        return self.build_chain_from_solutions(problem, solutions)


# 便捷函数
def visualize_reasoning(problem: str, solutions: List[Dict]) -> Dict[str, Any]:
    """快速生成推理可视化数据"""
    visualizer = ReasoningVisualizer()
    chain = visualizer.build_chain_from_solutions(problem, solutions)
    return {
        "graph": chain.to_dict(),
        "mermaid": chain.to_mermaid()
    }
