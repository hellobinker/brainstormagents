from typing import Dict, Optional, List
import uuid
from core.session import BrainstormingSession
from core.facilitator import Facilitator
from core.agent import Agent
from features.visualization import KnowledgeGraphVisualizer
from features.statistics import SessionStatistics
from features.emotion_engine import EmotionEngine
from features.role_switcher import RoleSwitcher
from features.advanced_techniques import DebateMode, CrossDomainConnector, ChainDeepening
from utils.llm_client import LLMClient

class SessionState:
    """持有单个会话的所有状态对象"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session: Optional[BrainstormingSession] = None
        self.facilitator: Optional[Facilitator] = None
        self.visualizer = KnowledgeGraphVisualizer()
        self.session_stats = SessionStatistics()
        
        # Features
        self.emotion_engine = EmotionEngine()
        self.role_switcher = RoleSwitcher()
        self.debate_mode = DebateMode()
        self.cross_domain_connector = CrossDomainConnector()
        self.chain_deepening = ChainDeepening()
        
        # State flags
        self.is_paused = False
        self.llm_client = LLMClient()  # Each session can have its own client config if needed

    def initialize_session(self, topic: str, agents: List[Agent], phase_rounds: int = 1):
        self.session = BrainstormingSession(topic, agents)
        self.session.rounds = 0 # Reset rounds
        self.facilitator = Facilitator(self.session)
        self.facilitator.phase_rounds = phase_rounds
        
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
