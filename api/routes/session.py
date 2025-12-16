# -*- coding: utf-8 -*-
"""
Session Routes - Handle session CRUD operations
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import datetime

from core.agent import Agent
from core.facilitator import Facilitator, PHASE_CONFIG
from core.session_manager import session_manager, SessionState
from utils.llm_client import LLMClient
from database import SessionLocal, Session as DBSession, Agent as DBAgent
from config import API_KEY, API_BASE_URL, DEFAULT_SESSION_ID, AVAILABLE_MODELS

router = APIRouter(prefix="/session", tags=["Session"])


# ============ Request Models ============

class AgentConfig(BaseModel):
    name: str
    role: str
    expertise: str
    style: str
    personality_traits: List[str]
    model_name: str = None


class StartSessionRequest(BaseModel):
    session_id: str = DEFAULT_SESSION_ID
    topic: str
    agents: List[AgentConfig]
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    phase_rounds: Optional[Dict[str, int]] = None


# ============ Helper Functions ============

def get_session_or_create(session_id: str) -> SessionState:
    """Get existing session or create new one"""
    state = session_manager.get_session(session_id)
    if not state:
        session_manager.sessions[session_id] = SessionState(session_id)
        state = session_manager.sessions[session_id]
    return state


# ============ Routes ============

@router.post("/create")
def create_session():
    """Create a new brainstorming session"""
    session_id = session_manager.create_session()
    return {"session_id": session_id}


@router.post("/start")
def start_session(request: StartSessionRequest):
    """Start a brainstorming session with configuration"""
    state = get_session_or_create(request.session_id)
    
    # Initialize LLM Client
    api_key = request.api_key or os.environ.get("OPENAI_API_KEY") or API_KEY
    base_url = request.base_url or os.environ.get("OPENAI_BASE_URL") or API_BASE_URL
    
    state.llm_client = LLMClient(api_key=api_key, base_url=base_url)
    
    # Create Agent instances
    agent_instances = [
        Agent(
            name=agent_conf.name,
            role=agent_conf.role,
            expertise=agent_conf.expertise,
            style=agent_conf.style,
            personality_traits=agent_conf.personality_traits,
            model_name=agent_conf.model_name
        )
        for agent_conf in request.agents
    ]
    
    # Initialize session in state
    state.initialize_session(request.topic, agent_instances, request.phase_rounds)
    
    # Initialize facilitator
    if not state.facilitator:
        state.facilitator = Facilitator(state.llm_client)

    # PERSISTENCE: Save Session and Agents to DB
    try:
        db = SessionLocal()
        existing = db.query(DBSession).filter(DBSession.id == state.session_id).first()
        if not existing:
            db_session = DBSession(
                id=state.session_id,
                topic=request.topic,
                current_phase=state.facilitator.current_phase.value
            )
            db.add(db_session)
            
            for agent in agent_instances:
                db_agent = DBAgent(
                    session_id=state.session_id,
                    name=agent.name,
                    role=agent.role,
                    model=agent.model_name
                )
                db.add(db_agent)
            
            db.commit()
        db.close()
    except Exception as e:
        print(f"Error saving session start to DB: {e}")

    return {
        "status": "started",
        "session_id": state.session_id,
        "topic": request.topic,
        "agent_count": len(agent_instances),
        "phase_rounds": state.facilitator.phase_rounds,
        "current_phase": state.facilitator.current_phase.value,
        "phase_name": PHASE_CONFIG[state.facilitator.current_phase]["name"]
    }


@router.get("/list", name="list_sessions")
def list_sessions():
    """List past sessions from DB"""
    db = SessionLocal()
    try:
        sessions = db.query(DBSession).order_by(DBSession.created_at.desc()).all()
        return {
            "sessions": [
                {
                    "id": s.id,
                    "topic": s.topic,
                    "created_at": s.created_at.isoformat(),
                    "agent_count": len(s.agents)
                }
                for s in sessions
            ]
        }
    finally:
        db.close()


@router.get("/{session_id}/history")
def get_session_history(session_id: str):
    """Get full chat history for a session"""
    db = SessionLocal()
    try:
        session = db.query(DBSession).filter(DBSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        messages = sorted(session.messages, key=lambda m: m.id)
        
        return {
            "session": {
                "id": session.id,
                "topic": session.topic,
                "current_phase": session.current_phase
            },
            "history": [
                {
                    "sender": m.sender,
                    "content": m.content,
                    "type": m.type,
                    "timestamp": m.timestamp.isoformat(),
                    "role": m.role,
                    "model": m.model,
                    "phase": m.phase
                }
                for m in messages
            ],
            "agents": [
                {"name": a.name, "role": a.role, "model": a.model}
                for a in session.agents
            ]
        }
    finally:
        db.close()


@router.post("/reset")
def reset_session(session_id: str = "default"):
    """Reset a session"""
    state = session_manager.get_session(session_id)
    if state:
        state.reset()
    return {"message": "Session reset", "status": "reset"}


@router.post("/pause")
def pause_session(session_id: str = "default"):
    """Pause a session"""
    state = get_session_or_create(session_id)
    state.is_paused = True
    return {"message": "Session paused", "is_paused": True}


@router.post("/resume")
def resume_session(session_id: str = "default"):
    """Resume a session"""
    state = get_session_or_create(session_id)
    state.is_paused = False
    return {"message": "Session resumed", "is_paused": False}


@router.get("/pause_status")
def get_pause_status(session_id: str = "default"):
    """Get pause status"""
    state = get_session_or_create(session_id)
    return {"is_paused": state.is_paused}
