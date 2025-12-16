# -*- coding: utf-8 -*-
"""
Multi-Agent Brainstorming Server - Refactored Entry Point

This is the new modular server that uses the refactored route structure.
The original server.py is preserved for backward compatibility.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from database import init_db
from api.routes import (
    session_router,
    phase_router,
    techniques_router,
    statistics_router,
    websocket_router
)
from utils.llm_client import LLMClient
from config import API_KEY, API_BASE_URL, AVAILABLE_MODELS

# Create FastAPI app
app = FastAPI(
    title="Multi-Agent Brainstorming System",
    description="A collaborative AI brainstorming platform with multiple intelligent agents",
    version="2.0.0"
)

# Initialize Database
init_db()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


# ============ Core Routes ============

@app.get("/")
async def read_index():
    """Serve the frontend"""
    return FileResponse('frontend/index.html')


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/models")
def list_models():
    """List available models from API"""
    client = LLMClient(api_key=API_KEY, base_url=API_BASE_URL)
    models = client.list_models()
    
    if not models:
        models = AVAILABLE_MODELS
        
    return {"models": models}


# ============ Register Routers ============

# Session management routes (create, start, list, history, pause, resume, reset)
app.include_router(session_router)

# Phase control routes (phases, stream_phase, next_phase, stream_full)
app.include_router(phase_router)

# Advanced techniques routes (creativity, evolution, parallel, chain, debate)
app.include_router(techniques_router)

# Statistics routes (statistics, export, knowledge insights)
app.include_router(statistics_router)

# WebSocket routes (ws, mention, online_users)
app.include_router(websocket_router)


# ============ Backward Compatibility ============
# These aliases ensure old API paths still work

@app.get("/sessions")
def list_sessions_compat():
    """Backward compatible /sessions endpoint"""
    from api.routes.session import list_sessions
    return list_sessions()


# ============ Entry Point ============

if __name__ == "__main__":
    print("🚀 Starting Multi-Agent Brainstorming Server v2.0.0")
    print("📦 Using modular route architecture")
    print("⚡ Async LLM client available for parallel execution")
    uvicorn.run(app, host="0.0.0.0", port=8000)
