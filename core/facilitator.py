"""
Facilitator Agent - 协作主持人
负责引导头脑风暴的各个阶段
"""
from typing import List, Dict
from enum import Enum

class BrainstormPhase(Enum):
    OPENING = "opening"           # 启动会话
    DEFINE_TOPIC = "define_topic" # 定义主题
    DIVERGE = "diverge"           # 发散阶段
    DEEPEN = "deepen"             # 深化阶段
    EVALUATE = "evaluate"         # 评估阶段
    INTEGRATE = "integrate"       # 整合阶段
    OUTPUT = "output"             # 输出方案

PHASE_CONFIG = {
    BrainstormPhase.OPENING: {
        "name": "启动会话",
        "emoji": "🎬",
        "rounds": 0,
        "facilitator_prompt": """你是头脑风暴的主持人。请用热情、专业的方式开场：
1. 欢迎所有参与的专家
2. 简要介绍今天的讨论主题
3. 说明头脑风暴的规则和流程
4. 鼓励大家畅所欲言

请用中文发言，保持简洁有力（100字以内）。"""
    },
    BrainstormPhase.DEFINE_TOPIC: {
        "name": "定义主题",
        "emoji": "🎯",
        "rounds": 1,
        "facilitator_prompt": """现在进入【定义主题】阶段。请：
1. 明确今天要解决的核心问题
2. 分解问题的关键维度
3. 邀请专家们从各自角度理解这个主题

请用中文发言，引导大家聚焦问题本质。""",
        "agent_prompt": """【定义主题阶段】
请从你的专业角度，分析这个主题的关键问题和挑战。
- 你认为这个主题的核心是什么？
- 有哪些关键维度需要考虑？
请简洁回答（150字以内）。"""
    },
    BrainstormPhase.DIVERGE: {
        "name": "发散阶段",
        "emoji": "💡",
        "rounds": 2,
        "facilitator_prompt": """现在进入【发散阶段】，这是头脑风暴最重要的环节！请：
1. 鼓励大家自由联想，打破常规
2. 强调"量大于质"，先不要评判
3. 引导跨领域思考

让我们开始头脑风暴！""",
        "agent_prompt": """【发散阶段】🧠
现在是自由发散环节！请：
1. 大胆提出创新想法，不用担心可行性
2. 可以从你的专业领域借鉴灵感
3. 越多越好，越新奇越好

请提出1-2个创新想法（每个想法50字以内）。"""
    },
    BrainstormPhase.DEEPEN: {
        "name": "深化阶段",
        "emoji": "🔍",  
        "rounds": 2,
        "facilitator_prompt": """现在进入【深化阶段】。请：
1. 挑选前面提出的有潜力的想法
2. 深入讨论其可行性和实现路径
3. 引导专家们相互补充和完善

让我们把好点子变成可落地的方案！""",
        "agent_prompt": """【深化阶段】🔍
请选择之前提出的1-2个最有潜力的想法：
1. 分析其技术可行性
2. 提出具体实现思路
3. 指出可能的障碍和解决方案

请结合你的专业给出深化建议（150字以内）。"""
    },
    BrainstormPhase.EVALUATE: {
        "name": "评估阶段",
        "emoji": "⚖️",
        "rounds": 1,
        "facilitator_prompt": """现在进入【评估阶段】。请：
1. 引导大家客观评估各个方案
2. 考虑成本、风险、收益
3. 识别最有价值的创新点

请大家理性评估！""",
        "agent_prompt": """【评估阶段】⚖️
请对讨论中的核心方案进行评估：
1. 创新性（1-5分）
2. 可行性（1-5分）
3. 商业价值（1-5分）
4. 风险评估

请给出你的专业评估（100字以内）。"""
    },
    BrainstormPhase.INTEGRATE: {
        "name": "整合阶段",
        "emoji": "🔗",
        "rounds": 1,
        "facilitator_prompt": """现在进入【整合阶段】。请：
1. 汇总核心创新点
2. 构建完整解决方案框架
3. 明确分工和下一步行动

让我们把碎片化的想法整合成完整方案！""",
        "agent_prompt": """【整合阶段】🔗
基于前面的讨论，请：
1. 指出你认为最值得采纳的创新点
2. 说明你的专业领域能贡献什么
3. 建议下一步如何推进

请给出整合建议（100字以内）。"""
    },
    BrainstormPhase.OUTPUT: {
        "name": "输出方案",
        "emoji": "📋",
        "rounds": 0,
        "facilitator_prompt": """头脑风暴进入【收尾阶段】。
请总结本次讨论的核心成果，形成可执行的创新方案。

感谢各位专家的精彩贡献！"""
    }
}

class Facilitator:
    """协作主持人"""
    
    def __init__(self, llm_client, model_name: str = "gpt-5.1", custom_rounds: Dict[str, int] = None):
        self.llm_client = llm_client
        self.model_name = model_name
        self.current_phase = BrainstormPhase.OPENING
        # Allow custom rounds per phase
        self.custom_rounds = custom_rounds or {}
        
    def get_system_prompt(self) -> str:
        return """你是一位专业的头脑风暴主持人（Facilitator），具备以下特质：
- 善于引导讨论，保持会议节奏
- 能够激发参与者的创造力
- 公正客观，善于总结归纳
- 语言简洁有力，富有感染力

你的任务是引导一场高效的创新头脑风暴会议。"""

    def get_phase_opening(self, topic: str, agents: List[str]) -> str:
        """获取当前阶段的开场白"""
        config = PHASE_CONFIG[self.current_phase]
        
        user_prompt = f"""当前阶段：{config['emoji']} {config['name']}
讨论主题：{topic}
参与专家：{', '.join(agents)}

{config['facilitator_prompt']}"""

        response = self.llm_client.get_completion(
            system_prompt=self.get_system_prompt(),
            user_prompt=user_prompt,
            model=self.model_name
        )
        return response
    
    def get_phase_config(self) -> dict:
        """Get phase config with custom rounds override"""
        config = PHASE_CONFIG[self.current_phase].copy()
        # Override rounds if custom value is set
        phase_key = self.current_phase.value
        if phase_key in self.custom_rounds:
            config['rounds'] = self.custom_rounds[phase_key]
        return config
    
    def advance_phase(self) -> bool:
        """进入下一阶段，返回是否还有更多阶段"""
        phases = list(BrainstormPhase)
        current_idx = phases.index(self.current_phase)
        if current_idx < len(phases) - 1:
            self.current_phase = phases[current_idx + 1]
            return True
        return False
    
    def get_agent_prompt_for_phase(self, topic: str) -> str:
        """获取当前阶段给Agent的提示"""
        config = PHASE_CONFIG[self.current_phase]
        base_prompt = config.get('agent_prompt', '')
        return f"【讨论主题】{topic}\n\n{base_prompt}" if base_prompt else ""
    
    def generate_final_summary(self, topic: str, history: List[dict]) -> str:
        """生成最终方案总结"""
        history_text = "\n".join([f"{h['sender']}: {h['content']}" for h in history[-50:]])
        
        prompt = f"""请基于以下头脑风暴讨论，生成一份完整的创新方案报告。

【讨论主题】{topic}

【讨论记录】
{history_text}

【报告要求】
请生成一份结构化的创新方案报告，包括：

## 📌 项目概述
简述项目背景和目标

## 🎯 核心创新点
列出3-5个关键创新方向

## 💡 详细方案
针对每个创新点，说明：
- 具体实现思路
- 技术路径
- 预期效果

## ⚠️ 风险与挑战
- 技术风险
- 市场风险
- 资源需求

## 📋 行动计划
- 短期（1-3个月）
- 中期（3-6个月）
- 长期（6-12个月）

## 🏁 结论
总结性陈述

请用中文生成报告："""

        return self.llm_client.get_completion(
            system_prompt="你是专业的创新方案报告撰写专家。",
            user_prompt=prompt,
            model=self.model_name
        )
