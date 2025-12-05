"""
动态角色切换模块
智能体根据讨论进展动态调整角色属性
"""
from typing import List, Dict, Optional
from core.agent import Agent
from core.protocol import Message

class DynamicRoleSwitcher:
    """根据讨论阶段和内容动态调整智能体角色"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        
        # 角色模式定义
        self.role_modes = {
            "innovator": {
                "name": "创新者",
                "emoji": "💡",
                "traits": ["开放思维", "大胆假设", "跳跃联想"],
                "prompt": "你现在是创新者模式，专注于提出新颖、大胆、打破常规的想法。"
            },
            "critic": {
                "name": "批评者",
                "emoji": "🔍",
                "traits": ["严谨分析", "风险识别", "逻辑推理"],
                "prompt": "你现在是批评者模式，专注于发现潜在问题、评估风险、确保可行性。"
            },
            "integrator": {
                "name": "整合者",
                "emoji": "🔗",
                "traits": ["综合归纳", "寻找共识", "方案优化"],
                "prompt": "你现在是整合者模式，专注于融合不同观点、构建完整方案。"
            },
            "explorer": {
                "name": "探索者",
                "emoji": "🧭",
                "traits": ["好奇心强", "深入追问", "边界探索"],
                "prompt": "你现在是探索者模式，专注于深入挖掘、探索未知领域。"
            },
            "advocate": {
                "name": "支持者",
                "emoji": "👍",
                "traits": ["积极肯定", "发现优点", "鼓励发展"],
                "prompt": "你现在是支持者模式，专注于发现想法的闪光点并推动其发展。"
            }
        }
        
        # 阶段-角色映射建议
        self.phase_role_hints = {
            "diverge": ["innovator", "explorer"],
            "deepen": ["critic", "explorer"],
            "evaluate": ["critic", "integrator"],
            "integrate": ["integrator", "advocate"]
        }
    
    def analyze_discussion_needs(self, history: List[Message], current_phase: str) -> Dict:
        """分析讨论当前需要什么类型的角色"""
        # 统计最近发言的角色倾向
        recent_msgs = history[-10:] if len(history) > 10 else history
        
        # 简单分析：统计关键词
        innovation_keywords = ["创新", "新颖", "突破", "想法", "可能"]
        critical_keywords = ["问题", "风险", "挑战", "难点", "不足"]
        integration_keywords = ["综合", "结合", "整合", "统一", "方案"]
        
        innovation_count = 0
        critical_count = 0
        integration_count = 0
        
        for msg in recent_msgs:
            content = msg.content
            innovation_count += sum(1 for kw in innovation_keywords if kw in content)
            critical_count += sum(1 for kw in critical_keywords if kw in content)
            integration_count += sum(1 for kw in integration_keywords if kw in content)
        
        # 确定讨论缺少什么
        total = innovation_count + critical_count + integration_count + 1
        
        return {
            "innovation_ratio": innovation_count / total,
            "critical_ratio": critical_count / total,
            "integration_ratio": integration_count / total,
            "suggested_roles": self.phase_role_hints.get(current_phase, ["innovator"]),
            "phase": current_phase
        }
    
    def suggest_role_switch(self, agent: Agent, analysis: Dict) -> Optional[Dict]:
        """建议角色切换"""
        current_mode = getattr(agent, 'current_mode', 'innovator')
        
        # 根据分析结果建议新角色
        if analysis["innovation_ratio"] < 0.2 and current_mode != "innovator":
            return self.role_modes["innovator"]
        elif analysis["critical_ratio"] < 0.15 and current_mode != "critic":
            return self.role_modes["critic"]
        elif analysis["integration_ratio"] < 0.1 and analysis["phase"] in ["integrate", "evaluate"]:
            return self.role_modes["integrator"]
        
        # 基于阶段建议
        suggested = analysis.get("suggested_roles", [])
        if suggested and current_mode not in suggested:
            import random
            new_mode = random.choice(suggested)
            return self.role_modes[new_mode]
        
        return None
    
    def switch_role(self, agent: Agent, new_mode: str) -> str:
        """切换智能体角色模式"""
        if new_mode in self.role_modes:
            mode_info = self.role_modes[new_mode]
            agent.current_mode = new_mode
            agent.mode_prompt = mode_info["prompt"]
            return f"{agent.name} 切换到 {mode_info['emoji']} {mode_info['name']} 模式"
        return ""
    
    def get_role_prompt_modifier(self, agent: Agent) -> str:
        """获取当前角色的提示词修饰"""
        current_mode = getattr(agent, 'current_mode', None)
        if current_mode and current_mode in self.role_modes:
            return self.role_modes[current_mode]["prompt"]
        return ""
    
    def analyze_and_switch(self, agents: List[Agent], history: List[Message], phase: str = "diverge") -> List[str]:
        """分析并执行角色切换"""
        changes = []
        analysis = self.analyze_discussion_needs(history, phase)
        
        for agent in agents:
            suggestion = self.suggest_role_switch(agent, analysis)
            if suggestion:
                # 找到对应的模式key
                for mode_key, mode_info in self.role_modes.items():
                    if mode_info == suggestion:
                        change_msg = self.switch_role(agent, mode_key)
                        if change_msg:
                            changes.append(change_msg)
                        break
        
        return changes
