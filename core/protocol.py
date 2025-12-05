from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class Message:
    sender: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # metadata can include: 'emotion', 'role', 'round', 'type' (idea, critique, etc.)

@dataclass
class Idea:
    id: str
    title: str
    description: str
    author: str
    round_num: int
    score: float = 0.0
    tags: List[str] = field(default_factory=list)
