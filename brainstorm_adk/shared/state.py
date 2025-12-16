"""
共享状态定义

定义头脑风暴阶段和配置，从原项目迁移
"""
from enum import Enum
from typing import Dict, Any


class BrainstormPhase(Enum):
    """头脑风暴阶段枚举"""
    OPENING = "opening"           # 启动会话
    DEFINE_TOPIC = "define_topic" # 定义主题
    DIVERGE = "diverge"           # 发散阶段
    DEEPEN = "deepen"             # 深化阶段
    EVALUATE = "evaluate"         # 评估阶段
    INTEGRATE = "integrate"       # 整合阶段
    OUTPUT = "output"             # 输出方案


PHASE_CONFIG: Dict[BrainstormPhase, Dict[str, Any]] = {
    BrainstormPhase.OPENING: {
        "name": "启动会话",
        "emoji": "🎬",
        "rounds": 0,
        "description": "欢迎所有参与的专家，介绍主题和规则"
    },
    BrainstormPhase.DEFINE_TOPIC: {
        "name": "定义主题",
        "emoji": "🎯",
        "rounds": 1,
        "description": "明确核心问题，分解关键维度"
    },
    BrainstormPhase.DIVERGE: {
        "name": "发散阶段",
        "emoji": "💡",
        "rounds": 2,
        "description": "自由发散，提出创新想法，量大于质"
    },
    BrainstormPhase.DEEPEN: {
        "name": "深化阶段",
        "emoji": "🔍",
        "rounds": 2,
        "description": "深入分析可行性，完善实现方案"
    },
    BrainstormPhase.EVALUATE: {
        "name": "评估阶段",
        "emoji": "⚖️",
        "rounds": 1,
        "description": "评估创新性、可行性和商业价值"
    },
    BrainstormPhase.INTEGRATE: {
        "name": "整合阶段",
        "emoji": "🔗",
        "rounds": 1,
        "description": "整合核心创新点，构建解决方案"
    },
    BrainstormPhase.OUTPUT: {
        "name": "输出方案",
        "emoji": "📋",
        "rounds": 0,
        "description": "生成最终创新方案报告"
    }
}


def get_phase_list() -> list:
    """获取所有阶段列表"""
    return [
        {
            "id": phase.value,
            "name": config["name"],
            "emoji": config["emoji"],
            "description": config["description"]
        }
        for phase, config in PHASE_CONFIG.items()
    ]


def get_next_phase(current_phase: str) -> str:
    """获取下一阶段"""
    phases = list(BrainstormPhase)
    try:
        current = BrainstormPhase(current_phase)
        current_idx = phases.index(current)
        if current_idx < len(phases) - 1:
            return phases[current_idx + 1].value
    except ValueError:
        pass
    return current_phase
