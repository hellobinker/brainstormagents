# -*- coding: utf-8 -*-
"""
API Routes Package
"""
from .session import router as session_router
from .phase import router as phase_router
from .techniques import router as techniques_router
from .statistics import router as statistics_router
from .websocket import router as websocket_router

__all__ = [
    "session_router",
    "phase_router", 
    "techniques_router",
    "statistics_router",
    "websocket_router"
]
