# -*- coding: utf-8 -*-
"""
Phase Routes - Handle brainstorming phase operations and streaming
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, AsyncGenerator
import json
import asyncio
import datetime

from core.protocol import Message
from core.facilitator import BrainstormPhase, PHASE_CONFIG
from core.session_manager import session_manager, SessionState
from database import SessionLocal, Message as DBMessage
from api.services.stream_service import (
    generate_phase_stream,
    run_full_session_stream,
    create_sse_message
)

router = APIRouter(tags=["Phase"])


# ============ Request Models ============

class RunPhaseRequest(BaseModel):
    session_id: str = "default"
    phase: Optional[str] = None


# ============ Helper Functions ============

def get_session_or_create(session_id: str) -> SessionState:
    """Get existing session or create new one"""
    state = session_manager.get_session(session_id)
    if not state:
        session_manager.sessions[session_id] = SessionState(session_id)
        state = session_manager.sessions[session_id]
    return state


# ============ Routes ============

@router.get("/phases")
def get_phases():
    """Get all available phases"""
    phases = []
    for phase in BrainstormPhase:
        config = PHASE_CONFIG[phase]
        phases.append({
            "id": phase.value,
            "name": config["name"],
            "emoji": config["emoji"],
            "rounds": config["rounds"]
        })
    return {"phases": phases}


@router.get("/session/stream_phase")
async def stream_phase(session_id: str = "default"):
    """Stream a single phase of the brainstorming session"""
    try:
        state = get_session_or_create(session_id)
        if not state.session or not state.facilitator:
            return {"error": "Session not started"}
        
        return StreamingResponse(
            generate_phase_stream(state),
            media_type="text/event-stream"
        )
    except HTTPException as e:
        return {"error": e.detail}


@router.post("/session/next_phase")
async def next_phase(request: RunPhaseRequest):
    """Advance to the next phase"""
    state = get_session_or_create(request.session_id)
    
    if not state.facilitator:
        raise HTTPException(status_code=400, detail="Session not started")
    
    has_more = state.facilitator.advance_phase()
    phase_config = state.facilitator.get_phase_config()
    
    return {
        "has_more": has_more,
        "current_phase": state.facilitator.current_phase.value,
        "phase_name": phase_config["name"],
        "phase_emoji": phase_config["emoji"]
    }


@router.get("/session/stream_full")
async def stream_full(session_id: str = "default"):
    """Stream the full session"""
    try:
        state = session_manager.get_session(session_id)
        if not state or not state.session or not state.facilitator:
            if session_id == "default":
                return {"error": "Default session not started. Please start a session first."}
            return {"error": "Session not found"}

        return StreamingResponse(
            run_full_session_stream(session_id),
            media_type="text/event-stream"
        )
    except Exception as e:
        return {"error": str(e)}
