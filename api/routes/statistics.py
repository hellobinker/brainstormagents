# -*- coding: utf-8 -*-
"""
Statistics Routes - Handle session statistics and cross-domain insights
"""
from fastapi import APIRouter, HTTPException

from core.session_manager import session_manager
from features.knowledge import CrossDomainConnector

router = APIRouter(tags=["Statistics"])


# ============ Helper Functions ============

def get_session_state(session_id: str):
    """Get session state or raise error"""
    state = session_manager.get_session(session_id)
    if not state or not state.session:
        raise HTTPException(status_code=400, detail="Session not started")
    return state


# ============ Statistics Routes ============

@router.get("/statistics")
def get_statistics(session_id: str = "default"):
    """Get session statistics"""
    state = get_session_state(session_id)
    return state.session_stats.get_summary()


@router.get("/statistics/detailed")
def get_detailed_statistics(session_id: str = "default"):
    """Get detailed statistics"""
    state = get_session_state(session_id)
    return state.session_stats.export_json()


@router.get("/statistics/export")
def export_statistics(session_id: str = "default"):
    """Export statistics as JSON"""
    state = get_session_state(session_id)
    return state.session_stats.export_json()


@router.post("/statistics/reset")
def reset_statistics(session_id: str = "default"):
    """Reset statistics"""
    state = get_session_state(session_id)
    state.session_stats.reset()
    return {"message": "Statistics reset"}


# ============ Cross-Domain Knowledge Routes ============

@router.get("/knowledge/insight")
def get_cross_domain_insight(session_id: str = "default"):
    """Get cross-domain insight"""
    state = get_session_state(session_id)
    
    connector = CrossDomainConnector(state.llm_client)
    insight = connector.generate_cross_domain_insight(
        topic=state.session.topic,
        context=""
    )
    
    return insight


@router.get("/knowledge/insights")
def get_multiple_insights(session_id: str = "default", count: int = 3):
    """Get multiple cross-domain insights"""
    state = get_session_state(session_id)
    
    connector = CrossDomainConnector(state.llm_client)
    insights = connector.get_multiple_insights(
        topic=state.session.topic,
        count=count
    )
    
    return {"insights": insights}
