from typing import Dict, Optional, List
import uuid
from core.session import BrainstormingSession
from core.facilitator import Facilitator
from core.agent import Agent
from features.visualization import RealTimeVisualizer
from features.statistics import SessionStatistics
from features.emotion_engine import EmotionalIntelligenceEngine
from features.role_switcher import DynamicRoleSwitcher
# Note: CrossDomainConnector is in features.knowledge, but we also imported it from advanced_techniques below?
# Let's check where it really is. Based on server.py, it's features.knowledge.
from features.knowledge import CrossDomainConnector 
from features.advanced_techniques import DebateMode, ChainDeepening
from utils.llm_client import LLMClient

class SessionState:
    """持有单个会话的所有状态对象"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session: Optional[BrainstormingSession] = None
        self.facilitator: Optional[Facilitator] = None
        self.visualizer = RealTimeVisualizer()
        self.session_stats = SessionStatistics()
        
        # Features
        self.emotion_engine = EmotionalIntelligenceEngine()
        self.role_switcher = DynamicRoleSwitcher()
        self.debate_mode = DebateMode(None) # These need llm_client, let's init lazily or pass None for now
        self.cross_domain_connector = CrossDomainConnector()
        self.chain_deepening = ChainDeepening(None)
        
        # State flags
        self.is_paused = False
        self.interrupt_signal = False  # Signal for immediate human intervention checks
        self.llm_client = LLMClient()  # Each session can have its own client config if needed

    def initialize_session(self, topic: str, agents: List[Agent], phase_rounds: Optional[Dict[str, int]] = None):
        self.session = BrainstormingSession(topic, agents, self.llm_client)
        self.session.rounds = 0 # Reset rounds
        
        # Reset visualizer and stats for fresh session
        self.visualizer = RealTimeVisualizer()
        self.session_stats = SessionStatistics()
        
        # Facilitator requires llm_client, not session
        self.facilitator = Facilitator(self.llm_client, custom_rounds=phase_rounds)
        
        # Also expose phase_rounds attribute for backward compatibility if needed, though Facilitator.custom_rounds is used
        self.facilitator.phase_rounds = phase_rounds or {}
        
        # Initialize features with session
        self.debate_mode.llm_client = self.llm_client
        self.cross_domain_connector.llm_client = self.llm_client
        self.chain_deepening.llm_client = self.llm_client

class GlobalSessionManager:
    """全局单例，管理所有会话状态"""
    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())[:8]
        self.sessions[session_id] = SessionState(session_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[SessionState]:
        return self.sessions.get(session_id)

    def remove_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]

# Global instance
session_manager = GlobalSessionManager()
