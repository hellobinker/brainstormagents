"""
会话状态管理

集中式状态管理，支持序列化和持久化恢复。
"""
import json
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


class SessionPhase(str, Enum):
    """会话阶段"""
    OPENING = "opening"
    DEFINE_TOPIC = "define_topic"
    DIVERGE = "diverge"
    DEEPEN = "deepen"
    EVALUATE = "evaluate"
    INTEGRATE = "integrate"
    OUTPUT = "output"
    COMPLETED = "completed"


@dataclass
class AgentState:
    """单个 Agent 的状态"""
    name: str
    role: str
    expertise: str
    model: str
    emotion: str = "neutral"
    message_count: int = 0
    last_response_time: float = 0
    total_tokens: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "AgentState":
        return cls(**data)


@dataclass
class Message:
    """消息记录"""
    sender: str
    content: str
    role: str = ""
    phase: str = ""
    round: int = 0
    timestamp: float = field(default_factory=time.time)
    model: str = ""
    tokens: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(**data)


@dataclass
class SessionMetrics:
    """会话统计指标"""
    total_messages: int = 0
    total_tokens: int = 0
    total_duration: float = 0
    phase_durations: Dict[str, float] = field(default_factory=dict)
    agent_contributions: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "SessionMetrics":
        return cls(**data)


@dataclass
class SessionState:
    """
    集中式会话状态
    
    管理整个头脑风暴会话的状态，支持：
    - 状态追踪
    - 序列化/反序列化
    - 持久化恢复
    - 指标收集
    
    使用示例:
        state = SessionState(session_id="abc", topic="创新方案")
        state.add_message(Message(sender="Agent1", content="..."))
        state.advance_phase()
        
        # 保存
        json_str = state.to_json()
        
        # 恢复
        state = SessionState.from_json(json_str)
    """
    session_id: str
    topic: str
    phase: SessionPhase = SessionPhase.OPENING
    round: int = 0
    messages: List[Message] = field(default_factory=list)
    agent_states: Dict[str, AgentState] = field(default_factory=dict)
    metrics: SessionMetrics = field(default_factory=SessionMetrics)
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    is_paused: bool = False
    is_completed: bool = False
    
    # 阶段顺序
    PHASE_ORDER = [
        SessionPhase.OPENING,
        SessionPhase.DEFINE_TOPIC,
        SessionPhase.DIVERGE,
        SessionPhase.DEEPEN,
        SessionPhase.EVALUATE,
        SessionPhase.INTEGRATE,
        SessionPhase.OUTPUT,
        SessionPhase.COMPLETED
    ]
    
    def add_agent(self, name: str, role: str, expertise: str, model: str):
        """添加 Agent 到会话"""
        self.agent_states[name] = AgentState(
            name=name,
            role=role,
            expertise=expertise,
            model=model
        )
        self.metrics.agent_contributions[name] = 0
    
    def add_message(self, message: Message):
        """添加消息"""
        message.phase = self.phase.value
        message.round = self.round
        self.messages.append(message)
        
        # 更新统计
        self.metrics.total_messages += 1
        self.metrics.total_tokens += message.tokens
        
        # 更新 Agent 状态
        if message.sender in self.agent_states:
            agent = self.agent_states[message.sender]
            agent.message_count += 1
            agent.total_tokens += message.tokens
            agent.last_response_time = message.timestamp
            self.metrics.agent_contributions[message.sender] = agent.message_count
        
        self.updated_at = time.time()
    
    def advance_phase(self) -> bool:
        """
        进入下一阶段
        
        Returns:
            是否还有更多阶段
        """
        current_idx = self.PHASE_ORDER.index(self.phase)
        if current_idx < len(self.PHASE_ORDER) - 1:
            # 记录阶段持续时间
            phase_key = self.phase.value
            if phase_key not in self.metrics.phase_durations:
                self.metrics.phase_durations[phase_key] = 0
            
            self.phase = self.PHASE_ORDER[current_idx + 1]
            self.round = 0
            self.updated_at = time.time()
            
            if self.phase == SessionPhase.COMPLETED:
                self.is_completed = True
                self.metrics.total_duration = time.time() - self.created_at
                return False
            return True
        return False
    
    def advance_round(self):
        """进入下一轮"""
        self.round += 1
        self.updated_at = time.time()
    
    def pause(self):
        """暂停会话"""
        self.is_paused = True
        self.updated_at = time.time()
    
    def resume(self):
        """恢复会话"""
        self.is_paused = False
        self.updated_at = time.time()
    
    def get_recent_messages(self, count: int = 20) -> List[Message]:
        """获取最近的消息"""
        return self.messages[-count:] if self.messages else []
    
    def get_phase_messages(self, phase: SessionPhase = None) -> List[Message]:
        """获取指定阶段的消息"""
        target_phase = (phase or self.phase).value
        return [m for m in self.messages if m.phase == target_phase]
    
    def get_agent_messages(self, agent_name: str) -> List[Message]:
        """获取指定 Agent 的消息"""
        return [m for m in self.messages if m.sender == agent_name]
    
    def to_dict(self) -> dict:
        """转换为字典（用于序列化）"""
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "phase": self.phase.value,
            "round": self.round,
            "messages": [m.to_dict() for m in self.messages],
            "agent_states": {k: v.to_dict() for k, v in self.agent_states.items()},
            "metrics": self.metrics.to_dict(),
            "config": self.config,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_paused": self.is_paused,
            "is_completed": self.is_completed
        }
    
    def to_json(self, indent: int = 2) -> str:
        """序列化为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
    
    @classmethod
    def from_dict(cls, data: dict) -> "SessionState":
        """从字典恢复"""
        state = cls(
            session_id=data["session_id"],
            topic=data["topic"],
            phase=SessionPhase(data["phase"]),
            round=data.get("round", 0),
            config=data.get("config", {}),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            is_paused=data.get("is_paused", False),
            is_completed=data.get("is_completed", False)
        )
        
        # 恢复消息
        state.messages = [Message.from_dict(m) for m in data.get("messages", [])]
        
        # 恢复 Agent 状态
        state.agent_states = {
            k: AgentState.from_dict(v) 
            for k, v in data.get("agent_states", {}).items()
        }
        
        # 恢复指标
        if "metrics" in data:
            state.metrics = SessionMetrics.from_dict(data["metrics"])
        
        return state
    
    @classmethod
    def from_json(cls, json_str: str) -> "SessionState":
        """从 JSON 字符串恢复"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def save_to_file(self, filepath: str):
        """保存到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
    
    @classmethod
    def load_from_file(cls, filepath: str) -> "SessionState":
        """从文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return cls.from_json(f.read())
    
    def get_summary(self) -> dict:
        """获取会话摘要"""
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "phase": self.phase.value,
            "round": self.round,
            "total_messages": self.metrics.total_messages,
            "total_tokens": self.metrics.total_tokens,
            "agent_count": len(self.agent_states),
            "duration_seconds": time.time() - self.created_at,
            "is_paused": self.is_paused,
            "is_completed": self.is_completed
        }


# 全局状态管理器
class StateManager:
    """
    全局状态管理器
    
    管理多个会话的状态
    """
    
    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}
    
    def create_session(self, session_id: str, topic: str, config: dict = None) -> SessionState:
        """创建新会话"""
        state = SessionState(
            session_id=session_id,
            topic=topic,
            config=config or {}
        )
        self._sessions[session_id] = state
        return state
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """获取会话状态"""
        return self._sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """移除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    def list_sessions(self) -> List[dict]:
        """列出所有会话摘要"""
        return [s.get_summary() for s in self._sessions.values()]
    
    def save_all(self, directory: str):
        """保存所有会话到目录"""
        import os
        os.makedirs(directory, exist_ok=True)
        for session_id, state in self._sessions.items():
            state.save_to_file(os.path.join(directory, f"{session_id}.json"))
    
    def load_all(self, directory: str):
        """从目录加载所有会话"""
        import os
        if not os.path.exists(directory):
            return
        for filename in os.listdir(directory):
            if filename.endswith('.json'):
                filepath = os.path.join(directory, filename)
                state = SessionState.load_from_file(filepath)
                self._sessions[state.session_id] = state


# 全局单例
_state_manager: Optional[StateManager] = None

def get_state_manager() -> StateManager:
    """获取全局状态管理器"""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager
