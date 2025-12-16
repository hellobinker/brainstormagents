"""
动态专家生成器

根据问题自动生成最合适的专家团队，而非从固定目录中选择
"""
import json
from dataclasses import dataclass, field
from typing import List, Optional
from features.intent_analyzer import ProblemIntent


@dataclass
class DynamicExpert:
    """动态生成的专家"""
    name: str
    role: str
    expertise: str
    focus_area: str  # 针对当前问题的关注点
    approach: str    # 推荐的分析方法
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "expertise": self.expertise,
            "focus_area": self.focus_area,
            "approach": self.approach
        }


class DynamicExpertGenerator:
    """
    动态专家生成器
    
    根据问题的意图分析结果，自动生成最合适的专家团队
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def generate_experts(
        self, 
        problem: str, 
        intent: ProblemIntent,
        num_experts: int = 5
    ) -> List[DynamicExpert]:
        """
        根据问题动态生成专家团队
        
        Args:
            problem: 原始问题
            intent: 意图分析结果
            num_experts: 需要的专家数量
            
        Returns:
            动态生成的专家列表
        """
        prompt = f"""【专家团队生成】

请根据以下技术问题，生成最合适的专家团队。

【问题】
{problem}

【问题类型】{intent.problem_type}
【涉及领域】{', '.join(intent.domains)}
【子问题】
{chr(10).join(f'- {sp}' for sp in intent.sub_problems)}

【要求】
生成 {num_experts} 位专家，每位专家应该：
1. 有明确的专业定位，与问题高度相关
2. 专业互补，覆盖问题的不同方面
3. 包含至少1位跨领域/系统集成专家

请用JSON格式返回，只返回JSON数组：
[
  {{
    "name": "专家名称（如：热管理专家、振动分析专家）",
    "role": "角色定位（如：Thermal Engineer）",
    "expertise": "专业能力描述",
    "focus_area": "针对这个问题应关注的具体方面",
    "approach": "建议的分析方法和切入点"
  }},
  ...
]

请生成专家团队："""
        
        try:
            result = await self.llm_client.get_completion_async(
                system_prompt="你是技术团队组建专家，擅长根据问题特点组建最优专家团队。只返回JSON数组。",
                user_prompt=prompt,
                model="gemini-3-pro-preview"
            )
            
            # 解析JSON
            import re
            json_match = re.search(r'\[[\s\S]*\]', result)
            if json_match:
                experts_data = json.loads(json_match.group())
                return [
                    DynamicExpert(
                        name=e.get("name", "专家"),
                        role=e.get("role", "Expert"),
                        expertise=e.get("expertise", ""),
                        focus_area=e.get("focus_area", ""),
                        approach=e.get("approach", "")
                    )
                    for e in experts_data[:num_experts]
                ]
        except Exception as e:
            print(f"[WARN] Dynamic expert generation failed: {e}")
        
        # 降级：返回通用专家
        return self._fallback_experts(intent, num_experts)
    
    def _fallback_experts(self, intent: ProblemIntent, num_experts: int) -> List[DynamicExpert]:
        """降级方案：根据领域生成通用专家"""
        experts = []
        for i, domain in enumerate(intent.domains[:num_experts]):
            experts.append(DynamicExpert(
                name=f"{domain}专家",
                role=f"{domain} Expert",
                expertise=f"{domain}领域的技术分析和解决方案设计",
                focus_area=f"从{domain}角度分析问题",
                approach="系统分析法"
            ))
        
        # 补充系统集成专家
        if len(experts) < num_experts:
            experts.append(DynamicExpert(
                name="系统集成专家",
                role="System Integration Expert",
                expertise="跨领域系统集成和方案协调",
                focus_area="各专业方案的协调整合",
                approach="系统工程方法"
            ))
        
        return experts[:num_experts]
