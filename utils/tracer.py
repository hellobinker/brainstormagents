"""
调试追踪系统

记录会话执行的完整时间线，用于调试和性能分析。
"""
import time
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime


class TraceEventType(str, Enum):
    """追踪事件类型"""
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    PHASE_START = "phase_start"
    PHASE_END = "phase_end"
    ROUND_START = "round_start"
    ROUND_END = "round_end"
    AGENT_CALL_START = "agent_call_start"
    AGENT_CALL_END = "agent_call_end"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END = "tool_call_end"
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class TraceEvent:
    """追踪事件"""
    event_type: TraceEventType
    timestamp: float = field(default_factory=time.time)
    name: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0
    parent_id: Optional[str] = None
    event_id: str = ""
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = f"{self.event_type.value}_{int(self.timestamp * 1000)}"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "timestamp_readable": datetime.fromtimestamp(self.timestamp).isoformat(),
            "name": self.name,
            "data": self.data,
            "duration_ms": self.duration_ms,
            "parent_id": self.parent_id,
            "event_id": self.event_id
        }


class SessionTracer:
    """
    会话追踪器
    
    记录会话执行的完整时间线，支持：
    - 嵌套事件（如 Phase > Round > Agent Call）
    - 性能分析（各阶段耗时）
    - JSON 导出
    - 可视化时间线
    
    使用示例:
        tracer = SessionTracer("session_123")
        
        with tracer.trace_phase("diverge"):
            with tracer.trace_agent_call("Agent1"):
                # ... agent 执行
                pass
        
        # 导出分析
        tracer.print_summary()
        tracer.export_json("trace.json")
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.events: List[TraceEvent] = []
        self._event_stack: List[str] = []  # 嵌套事件栈
        self._start_times: Dict[str, float] = {}
        self.start_time = time.time()
    
    def _get_parent_id(self) -> Optional[str]:
        """获取当前父事件 ID"""
        return self._event_stack[-1] if self._event_stack else None
    
    def _add_event(self, event: TraceEvent) -> str:
        """添加事件"""
        event.parent_id = self._get_parent_id()
        self.events.append(event)
        return event.event_id
    
    def trace_session_start(self, topic: str, agents: List[str]):
        """记录会话开始"""
        event = TraceEvent(
            event_type=TraceEventType.SESSION_START,
            name=f"Session: {topic[:30]}...",
            data={
                "session_id": self.session_id,
                "topic": topic,
                "agents": agents
            }
        )
        event_id = self._add_event(event)
        self._event_stack.append(event_id)
        self._start_times[event_id] = time.time()
        return event_id
    
    def trace_session_end(self, summary: dict = None):
        """记录会话结束"""
        if self._event_stack:
            start_event_id = self._event_stack.pop()
            start_time = self._start_times.pop(start_event_id, self.start_time)
        else:
            start_time = self.start_time
        
        event = TraceEvent(
            event_type=TraceEventType.SESSION_END,
            name="Session Complete",
            data=summary or {},
            duration_ms=(time.time() - start_time) * 1000
        )
        self._add_event(event)
    
    def trace_phase_start(self, phase: str, round_count: int = 0):
        """记录阶段开始"""
        event = TraceEvent(
            event_type=TraceEventType.PHASE_START,
            name=f"Phase: {phase}",
            data={"phase": phase, "planned_rounds": round_count}
        )
        event_id = self._add_event(event)
        self._event_stack.append(event_id)
        self._start_times[event_id] = time.time()
        return event_id
    
    def trace_phase_end(self, phase: str, result: dict = None):
        """记录阶段结束"""
        if self._event_stack:
            start_event_id = self._event_stack.pop()
            start_time = self._start_times.pop(start_event_id, time.time())
        else:
            start_time = time.time()
        
        event = TraceEvent(
            event_type=TraceEventType.PHASE_END,
            name=f"Phase Complete: {phase}",
            data=result or {},
            duration_ms=(time.time() - start_time) * 1000
        )
        self._add_event(event)
    
    def trace_agent_call(self, agent_name: str, model: str = "", prompt_preview: str = ""):
        """
        追踪 Agent 调用（上下文管理器）
        
        使用:
            with tracer.trace_agent_call("Agent1", "gpt-4"):
                # agent 执行
                pass
        """
        return _AgentCallTracer(self, agent_name, model, prompt_preview)
    
    def trace_llm_request(self, model: str, prompt_tokens: int = 0):
        """记录 LLM 请求"""
        event = TraceEvent(
            event_type=TraceEventType.LLM_REQUEST,
            name=f"LLM: {model}",
            data={"model": model, "prompt_tokens": prompt_tokens}
        )
        event_id = self._add_event(event)
        self._start_times[event_id] = time.time()
        return event_id
    
    def trace_llm_response(self, request_id: str, completion_tokens: int = 0, success: bool = True):
        """记录 LLM 响应"""
        start_time = self._start_times.pop(request_id, time.time())
        event = TraceEvent(
            event_type=TraceEventType.LLM_RESPONSE,
            name="LLM Response",
            data={
                "completion_tokens": completion_tokens,
                "success": success
            },
            duration_ms=(time.time() - start_time) * 1000
        )
        self._add_event(event)
    
    def trace_error(self, error: str, context: dict = None):
        """记录错误"""
        event = TraceEvent(
            event_type=TraceEventType.ERROR,
            name="Error",
            data={"error": error, "context": context or {}}
        )
        self._add_event(event)
    
    def trace_info(self, message: str, data: dict = None):
        """记录信息"""
        event = TraceEvent(
            event_type=TraceEventType.INFO,
            name=message,
            data=data or {}
        )
        self._add_event(event)
    
    def get_timeline(self) -> List[dict]:
        """获取完整时间线"""
        return [e.to_dict() for e in self.events]
    
    def get_summary(self) -> dict:
        """获取追踪摘要"""
        total_duration = time.time() - self.start_time
        
        # 统计各类事件
        event_counts = {}
        for e in self.events:
            event_type = e.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        # 统计各阶段耗时
        phase_durations = {}
        for e in self.events:
            if e.event_type == TraceEventType.PHASE_END:
                phase = e.data.get("phase", e.name)
                phase_durations[phase] = e.duration_ms
        
        # 统计 LLM 调用
        llm_calls = [e for e in self.events if e.event_type == TraceEventType.LLM_RESPONSE]
        llm_total_time = sum(e.duration_ms for e in llm_calls)
        
        return {
            "session_id": self.session_id,
            "total_duration_ms": total_duration * 1000,
            "event_counts": event_counts,
            "phase_durations_ms": phase_durations,
            "llm_calls": len(llm_calls),
            "llm_total_time_ms": llm_total_time,
            "errors": event_counts.get("error", 0)
        }
    
    def print_summary(self):
        """打印追踪摘要"""
        summary = self.get_summary()
        print("\n" + "=" * 50)
        print(f"📊 Session Trace Summary: {self.session_id}")
        print("=" * 50)
        print(f"⏱️  Total Duration: {summary['total_duration_ms']:.0f} ms")
        print(f"📡 LLM Calls: {summary['llm_calls']} ({summary['llm_total_time_ms']:.0f} ms)")
        print(f"❌ Errors: {summary['errors']}")
        
        if summary['phase_durations_ms']:
            print("\n📋 Phase Durations:")
            for phase, duration in summary['phase_durations_ms'].items():
                print(f"   {phase}: {duration:.0f} ms")
        
        print("=" * 50 + "\n")
    
    def export_json(self, filepath: str):
        """导出为 JSON 文件"""
        data = {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "summary": self.get_summary(),
            "timeline": self.get_timeline()
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def to_json(self) -> str:
        """导出为 JSON 字符串"""
        data = {
            "session_id": self.session_id,
            "summary": self.get_summary(),
            "timeline": self.get_timeline()
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


class _AgentCallTracer:
    """Agent 调用追踪器（上下文管理器）"""
    
    def __init__(self, tracer: SessionTracer, agent_name: str, model: str, prompt_preview: str):
        self.tracer = tracer
        self.agent_name = agent_name
        self.model = model
        self.prompt_preview = prompt_preview
        self.event_id = None
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        event = TraceEvent(
            event_type=TraceEventType.AGENT_CALL_START,
            name=f"Agent: {self.agent_name}",
            data={
                "agent": self.agent_name,
                "model": self.model,
                "prompt_preview": self.prompt_preview[:100] if self.prompt_preview else ""
            }
        )
        self.event_id = self.tracer._add_event(event)
        self.tracer._event_stack.append(self.event_id)
        self.tracer._start_times[self.event_id] = self.start_time
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.tracer._event_stack:
            self.tracer._event_stack.pop()
        
        duration = (time.time() - self.start_time) * 1000 if self.start_time else 0
        
        event = TraceEvent(
            event_type=TraceEventType.AGENT_CALL_END,
            name=f"Agent Complete: {self.agent_name}",
            data={
                "agent": self.agent_name,
                "success": exc_type is None,
                "error": str(exc_val) if exc_val else None
            },
            duration_ms=duration
        )
        self.tracer._add_event(event)
        
        # 不抑制异常
        return False


# 全局追踪器管理
_active_tracers: Dict[str, SessionTracer] = {}

def get_tracer(session_id: str) -> SessionTracer:
    """获取或创建会话追踪器"""
    if session_id not in _active_tracers:
        _active_tracers[session_id] = SessionTracer(session_id)
    return _active_tracers[session_id]

def remove_tracer(session_id: str):
    """移除追踪器"""
    if session_id in _active_tracers:
        del _active_tracers[session_id]
