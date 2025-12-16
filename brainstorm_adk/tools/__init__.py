"""
ADK 工具模块

包含头脑风暴所需的各种工具:
- creativity: 创意激发工具 (SCAMPER, 六顶思考帽, 随机刺激)
- session: 会话管理工具
- evolution: 想法进化工具
- debate: 辩论模式工具
"""

from .creativity import (
    apply_scamper,
    apply_six_hats,
    apply_random_stimulus,
    apply_reverse_thinking
)
from .session import (
    start_brainstorm,
    add_idea,
    advance_phase,
    get_session_summary,
    list_ideas
)
from .evolution import (
    evolve_ideas,
    crossover_ideas
)
from .debate import (
    argue_for,
    argue_against,
    synthesize_debate
)

__all__ = [
    # Creativity tools
    "apply_scamper",
    "apply_six_hats", 
    "apply_random_stimulus",
    "apply_reverse_thinking",
    # Session tools
    "start_brainstorm",
    "add_idea",
    "advance_phase",
    "get_session_summary",
    "list_ideas",
    # Evolution tools
    "evolve_ideas",
    "crossover_ideas",
    # Debate tools
    "argue_for",
    "argue_against",
    "synthesize_debate"
]
