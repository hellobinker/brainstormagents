from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, AsyncGenerator
from core.agent import Agent
from core.session import BrainstormingSession
from core.facilitator import Facilitator, BrainstormPhase, PHASE_CONFIG
from core.protocol import Message
from utils.llm_client import LLMClient
from features.role_switcher import DynamicRoleSwitcher
from features.emotion_engine import EmotionalIntelligenceEngine
from features.knowledge import CrossDomainConnector
from features.visualization import RealTimeVisualizer
from core.session_manager import session_manager, SessionState
from features.websocket_manager import ws_manager  # Use global singleton
from features.statistics import SessionStatistics
from features.mention_parser import MentionParser
from config import (
    API_KEY, API_BASE_URL, DEFAULT_MODEL, AVAILABLE_MODELS,
    DEFAULT_SESSION_ID
)
import uvicorn
import os
import json
import asyncio
import uuid

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.params import Query

from database import init_db, get_db, SessionLocal, Session as DBSession, Message as DBMessage, Agent as DBAgent
import datetime

app = FastAPI()

# Initialize Database
init_db()

# CORS for SSE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 集成 ADK 路由
# ============================================================
try:
    from routes.adk_routes import router as adk_router
    app.include_router(adk_router)
    print("✅ ADK routes loaded successfully")
except ImportError as e:
    print(f"⚠️ ADK routes not loaded: {e}")

# ============================================================
# 技术问题求解 API
# ============================================================
try:
    from features.problem_solver import TechnicalProblemSolver
    from features.intent_analyzer import IntentAnalyzer
    from features.expert_matcher import ExpertMatcher, get_matcher
    PROBLEM_SOLVER_AVAILABLE = True
    print("✅ Problem Solver loaded successfully")
except ImportError as e:
    PROBLEM_SOLVER_AVAILABLE = False
    print(f"⚠️ Problem Solver not loaded: {e}")


class TechProblemRequest(BaseModel):
    """技术问题求解请求"""
    problem: str
    expert_indices: Optional[List[int]] = None  # 用户指定的专家索引
    max_experts: int = 5  # 最多使用的专家数
    iteration_rounds: int = 1  # 迭代轮数（1=无迭代，2+=反思验证）
    stream: bool = False  # 是否流式返回


@app.post("/solve")
async def solve_technical_problem(request: TechProblemRequest):
    """
    技术问题求解端点
    
    自动分析问题 → 匹配专家 → 并行求解 → 迭代反思 → 整合答案
    """
    if not PROBLEM_SOLVER_AVAILABLE:
        raise HTTPException(status_code=500, detail="Problem Solver not available")
    
    llm_client = LLMClient(api_key=API_KEY, base_url=API_BASE_URL)
    solver = TechnicalProblemSolver(llm_client)
    
    if request.stream:
        # 流式返回
        async def generate():
            async for event in solver.solve_stream(
                problem=request.problem,
                selected_expert_indices=request.expert_indices,
                max_experts=request.max_experts,
                iteration_rounds=request.iteration_rounds
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    else:
        # 一次性返回
        solution = await solver.solve(
            problem=request.problem,
            selected_expert_indices=request.expert_indices,
            max_experts=request.max_experts
        )
        return solution.to_dict()


@app.get("/solve/experts")
async def list_available_experts():
    """列出可用于问题求解的专家"""
    if not PROBLEM_SOLVER_AVAILABLE:
        raise HTTPException(status_code=500, detail="Problem Solver not available")
    
    matcher = get_matcher()
    return {
        "domains": matcher.get_all_domains(),
        "expert_count": len(matcher.experts),
        "experts": [
            {"index": i, "name": e.name, "role": e.role, "expertise": e.expertise}
            for i, e in enumerate(matcher.experts)
        ]
    }


@app.post("/solve/analyze")
async def analyze_problem_intent(problem: str):
    """只分析问题意图（不求解）"""
    if not PROBLEM_SOLVER_AVAILABLE:
        raise HTTPException(status_code=500, detail="Problem Solver not available")
    
    llm_client = LLMClient(api_key=API_KEY, base_url=API_BASE_URL)
    analyzer = IntentAnalyzer(llm_client)
    intent = await analyzer.analyze(problem)
    
    return {
        "intent": intent.to_dict(),
        "recommended_experts": get_matcher().match_by_domains(intent.domains, limit=5)
    }

# Serve Frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('frontend/index.html')

# New feature instances
mention_parser = MentionParser()

@app.post("/session/create")
def create_session():
    """Create a new brainstorming session"""
    session_id = session_manager.create_session()
    return {"session_id": session_id}

@app.get("/models")
def list_models():
    """List available models from API"""
    # Init temp client using config
    client = LLMClient(api_key=API_KEY, base_url=API_BASE_URL)
    models = client.list_models()
    
    # Fallback if list is empty - use config
    if not models:
        models = AVAILABLE_MODELS
        
    return {"models": models}


# Data Models
class AgentConfig(BaseModel):
    name: str
    role: str
    expertise: str
    style: str
    personality_traits: List[str]
    model_name: str = None  # Will use config.DEFAULT_MODEL via Agent class

class StartSessionRequest(BaseModel):
    session_id: str = DEFAULT_SESSION_ID
    topic: str
    agents: List[AgentConfig]
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    phase_rounds: Optional[Dict[str, int]] = None  # Custom rounds per phase

class RunPhaseRequest(BaseModel):
    session_id: str = "default"
    phase: Optional[str] = None

def get_session_or_create(session_id: str) -> SessionState:
    state = session_manager.get_session(session_id)
    if not state:
        # Auto-create if not exists (for simplified UX)
        session_manager.sessions[session_id] = SessionState(session_id)
        state = session_manager.sessions[session_id]
    return state

def create_sse_message(event: str, data: dict) -> str:
    """Create SSE formatted message"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

def save_message_to_db(session_id: str, sender: str, content: str, msg_type: str, phase: str = None, role: str = None, model: str = None):
    """Helper to save message to SQLite"""
    try:
        db = SessionLocal()
        new_msg = DBMessage(
            session_id=session_id,
            sender=sender,
            content=content,
            type=msg_type,
            phase=phase,
            role=role,
            model=model,
            timestamp=datetime.datetime.now()
        )
        db.add(new_msg)
        db.commit()
        db.close()
    except Exception as e:
        print(f"Error saving message to DB: {e}")

@app.get("/sessions")
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

@app.get("/sessions/{session_id}/history")
def get_session_history(session_id: str):
    """Get full chat history for a session"""
    db = SessionLocal()
    try:
        session = db.query(DBSession).filter(DBSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Sort messages by ID (insertion order)
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

@app.post("/session/start")
def start_session(request: StartSessionRequest):
    state = get_session_or_create(request.session_id)
    
    # Initialize LLM Client
    # Restoring real API configuration as verified working with gpt-4
    DEFAULT_API_KEY = "sk-j3MQdosfgMzzOHOtA7MUnrxHSNIdaO44FzMlk7RRJIcjrf8r"
    DEFAULT_BASE_URL = "https://yunwu.ai/v1"
    
    api_key = request.api_key or os.environ.get("OPENAI_API_KEY") or DEFAULT_API_KEY
    base_url = request.base_url or os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL
    
    # Update state LLM client
    state.llm_client = LLMClient(api_key=api_key, base_url=base_url)
    
    # Create Agent instances
    agent_instances = []
    for agent_conf in request.agents:
        agent_instances.append(Agent(
            name=agent_conf.name,
            role=agent_conf.role,
            expertise=agent_conf.expertise,
            style=agent_conf.style,
            personality_traits=agent_conf.personality_traits,
            model_name=agent_conf.model_name
        ))
    
    # Initialize session in state
    state.initialize_session(request.topic, agent_instances, request.phase_rounds)
    
    # Initialize facilitator
    if not state.facilitator:
        state.facilitator = Facilitator(state.llm_client)
        # model_name is now set from config.DEFAULT_MODEL in Facilitator.__init__

    # PERSISTENCE: Save Session and Agents to DB
    try:
        db = SessionLocal()
        # Check if session already exists in DB
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

async def generate_phase_stream(state: SessionState) -> AsyncGenerator[str, None]:
    """Generate streaming events for a single phase using SessionState"""
    if not state.session or not state.facilitator:
        return
        
    topic = state.session.topic
    agents = state.session.agents
    phase_config = state.facilitator.get_phase_config()
    phase_rounds = state.facilitator.phase_rounds.get(state.facilitator.current_phase.value, 1)
    phase_name = phase_config["name"]
    
    # 1. Phase Start
    yield create_sse_message("phase_start", {
        "phase": state.facilitator.current_phase.value,
        "name": phase_name,
        "emoji": phase_config["emoji"],
        "description": phase_config.get("description", "")
    })
    
    # Facilitator Intro
    # Use state.llm_client
    intro = state.llm_client.get_completion(
        system_prompt=state.facilitator.get_system_prompt(),
        user_prompt=f"Please introduce the '{phase_name}' phase for the topic: {topic}. Be brief and encouraging.",
        model=state.facilitator.model_name  # Use facilitator's configured model
    )
    
    yield create_sse_message("message", {
        "sender": "主持人",
        "content": intro,
        "type": "facilitator",
        "phase": state.facilitator.current_phase.value
    })
    
    state.session.add_message(Message("主持人", intro, {"type": "facilitator_intro", "phase": state.facilitator.current_phase.value}))
    state.session_stats.record_message("主持人", intro, {"type": "facilitator"})
    
    # PERSISTENCE
    save_message_to_db(
        state.session_id, "主持人", intro, "facilitator", 
        phase=state.facilitator.current_phase.value
    )
    
    await asyncio.sleep(0.3)
    
    # 2. If this phase has agent rounds, run them
    if phase_rounds > 0:
        agent_prompt = state.facilitator.get_agent_prompt_for_phase(topic)
        
        for round_num in range(phase_rounds):
            if phase_rounds > 1:
                yield create_sse_message("round_start", {"round": round_num + 1, "total": phase_rounds})
                await asyncio.sleep(0.1)
            
            for agent in agents:
                # Update emotions
                state.emotion_engine.update_emotions([agent], state.session.history)
                
                # Build context
                history_text = "\n".join([f"{m.sender}: {m.content}" for m in state.session.history[-15:]])
                
                # Check for recent human input to prioritize interaction
                human_instruction = ""
                # Also check interrupt_signal for immediate priority
                is_interrupt = state.interrupt_signal
                if is_interrupt:
                    state.interrupt_signal = False # Consume signal
                    print(f"⚠️ Interrupt detected for agent {agent.name}")

                for m in reversed(state.session.history[-3:]):
                     if m.metadata.get("type") == "human":
                         prefix = "🔴【紧急插播】" if is_interrupt else "⚠️【特别指令】"
                         human_instruction = f"\n\n{prefix} 用户刚刚参与了讨论！请务必优先回应用户的观点或问题 ('{m.content}')，与其进行互动，然后再继续阐述你的看法。"
                         break

                full_prompt = f"""{agent_prompt}

【讨论历史】
{history_text}{human_instruction}

请开始你的发言："""
                
                # Check if paused (using state.is_paused)
                while state.is_paused:
                    yield create_sse_message("paused", {"status": "paused"})
                    await asyncio.sleep(1)
                
                # Start typing indicator
                yield create_sse_message("agent_typing", {
                    "agent": agent.name,
                    "role": agent.role
                })
                
                await asyncio.sleep(0.1)
                
                # Stream the response token by token
                full_response = ""
                for chunk in state.llm_client.get_completion_stream(
                    system_prompt=agent.get_system_prompt(),
                    user_prompt=full_prompt,
                    model=agent.model_name
                ):
                    full_response += chunk
                    
                    # Send each chunk to frontend
                    yield create_sse_message("message_chunk", {
                        "sender": agent.name,
                        "chunk": chunk,
                        "type": "agent",
                        "role": agent.role,
                        "emotion": agent.current_emotion,
                        "model": agent.model_name,
                        "phase": state.facilitator.current_phase.value
                    })
                    
                    await asyncio.sleep(0.05)  # Streaming delay
                
                # Send completion signal
                yield create_sse_message("message_complete", {
                    "sender": agent.name,
                    "content": full_response,
                    "type": "agent",
                    "role": agent.role,
                    "emotion": agent.current_emotion,
                    "model": agent.model_name,
                    "phase": state.facilitator.current_phase.value
                })
                
                state.session.add_message(Message(agent.name, full_response, {
                    "phase": state.facilitator.current_phase.value,
                    "role": agent.role,
                    "round": state.session.rounds
                }))
                state.session_stats.record_message(agent.name, full_response, {
                    "role": agent.role, 
                    "emotion": agent.current_emotion
                })
                
                # PERSISTENCE
                save_message_to_db(
                    state.session_id, agent.name, full_response, "agent",
                    phase=state.facilitator.current_phase.value,
                    role=agent.role,
                    model=agent.model_name
                )
                
                # Update visualization and send graph data
                state.visualizer.update_graph(state.session.history)
                graph_json = state.visualizer.export_data()
                graph_data = json.loads(graph_json)
                yield create_sse_message("graph_update", graph_data)
                
                await asyncio.sleep(0.2)
        
        state.session.rounds += 1
    
    # 3. Phase complete
    yield create_sse_message("phase_complete", {
        "phase": state.facilitator.current_phase.value,
        "name": phase_name
    })

@app.get("/session/stream_phase")
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

@app.post("/session/next_phase")
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

async def run_full_session_stream(session_id: str = "default") -> AsyncGenerator[str, None]:
    """Run the complete brainstorming session with all phases"""
    state = get_session_or_create(session_id)
    
    if not state.session or not state.facilitator:
        yield create_sse_message("error", {"message": "Session not initialized"})
        return

    yield create_sse_message("session_start", {
        "topic": state.session.topic,
        "agent_count": len(state.session.agents)
    })
    
    # Run through all phases
    while True:
        async for msg in generate_phase_stream(state):
            yield msg
        
        await asyncio.sleep(0.5)
        
        if not state.facilitator.advance_phase():
            break
        
        yield create_sse_message("phase_transition", {
            "next_phase": state.facilitator.current_phase.value,
            "next_name": PHASE_CONFIG[state.facilitator.current_phase]["name"]
        })
        
        await asyncio.sleep(0.3)
    
    # Generate final summary
    yield create_sse_message("generating_summary", {"message": "正在生成创新方案报告..."})
    
    history_data = [{"sender": m.sender, "content": m.content} for m in state.session.history]
    
    # Use state.llm_client for summary generation if needed inside facilitator, 
    # but Facilitator is initialized with llm_client.
    summary = state.facilitator.generate_final_summary(state.session.topic, history_data)
    
    state.session.add_message(Message("📋 创新方案报告", summary, {"type": "summary"}))
    state.session_stats.record_message("System", summary, {"type": "summary"})
    
    # PERSISTENCE
    save_message_to_db(state.session_id, "System", summary, "summary")
    
    yield create_sse_message("summary", {"content": summary})
    
    # Final cleanup
    yield create_sse_message("session_complete", {"topic": state.session.topic})

@app.get("/session/stream_full")
async def stream_full(session_id: str = "default"):
    """Stream the full session"""
    try:
        # Check if session exists first to return proper error
        state = session_manager.get_session(session_id)
        if not state or not state.session or not state.facilitator:
             # If default and not exist, return error, user must call start first
             if session_id == "default":
                 return {"error": "Default session not started. Please start a session first."}
             return {"error": "Session not found"}

        return StreamingResponse(
            run_full_session_stream(session_id),
            media_type="text/event-stream"
        )
    except Exception as e:
        return {"error": str(e)}

@app.get("/session/state")
def get_state():
    global session, facilitator
    if not session:
        return {"status": "not_started"}
    
    history_data = [
        {
            "sender": m.sender,
            "content": m.content,
            "timestamp": m.timestamp,
            "metadata": m.metadata
        }
        for m in session.history
    ]
    
    agents_data = [
        {
            "name": a.name,
            "role": a.role,
            "emotion": a.current_emotion,
            "model": a.model_name
        }
        for a in session.agents
    ]
    
    graph_json = visualizer.export_data()
    graph_data = json.loads(graph_json)
    
    current_phase = facilitator.current_phase.value if facilitator else "unknown"
    phase_name = PHASE_CONFIG[facilitator.current_phase]["name"] if facilitator else "未知"
    
    return {
        "status": "active",
        "topic": session.topic,
        "rounds": session.rounds,
        "history": history_data,
        "graph_data": graph_data,
        "agents": agents_data,
        "current_phase": current_phase,
        "phase_name": phase_name
    }

@app.get("/phases")
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

@app.post("/session/reset")
def reset_session():
    """重置会话"""
    global session, facilitator, visualizer, is_paused
    session = None
    facilitator = None
    visualizer = RealTimeVisualizer()
    is_paused = False
    return {"message": "Session reset", "status": "reset"}

@app.post("/session/pause")
def pause_session():
    """暂停会话"""
    global is_paused
    is_paused = True
    return {"message": "Session paused", "is_paused": True}

@app.post("/session/resume")
def resume_session():
    """恢复会话"""
    global is_paused
    is_paused = False
    return {"message": "Session resumed", "is_paused": False}

@app.get("/session/pause_status")
def get_pause_status():
    """获取暂停状态"""
    global is_paused
    return {"is_paused": is_paused}

# ============ Advanced Techniques Endpoints ============

class CreativityRequest(BaseModel):
    technique: Optional[str] = None  # scamper, random_input, six_thinking_hats, reverse_thinking
    agent_index: int = 0

@app.post("/techniques/creativity")
async def apply_creativity_technique(request: CreativityRequest):
    """应用创意激发技术"""
    global session, creativity_techniques
    if not session or not creativity_techniques:
        raise HTTPException(status_code=400, detail="Session not started")
    
    agent = session.agents[request.agent_index % len(session.agents)]
    context = "\n".join([f"{m.sender}: {m.content}" for m in session.history[-10:]])
    
    result = creativity_techniques.stimulate_creativity(
        topic=session.topic,
        context=context,
        agent_role=agent.role,
        technique=request.technique
    )
    
    # Add to session history
    session.add_message(Message(
        f"💡 {agent.name}",
        f"【{result['technique_name']}】\n{result['result']}",
        {"technique": result['technique']}
    ))
    
    return result

class IdeaEvolutionRequest(BaseModel):
    ideas: List[str]
    generations: int = 2

@app.post("/techniques/evolution")
async def evolve_ideas(request: IdeaEvolutionRequest):
    """想法进化算法"""
    global session, idea_evolution
    if not session or not idea_evolution:
        raise HTTPException(status_code=400, detail="Session not started")
    
    evolved = idea_evolution.evolve_ideas(
        ideas=request.ideas,
        topic=session.topic,
        generations=request.generations
    )
    
    # Add evolved ideas to history
    for item in evolved:
        session.add_message(Message(
            "🧬 想法进化",
            f"【{item['type']}】{item['result']}",
            {"evolution_type": item['type']}
        ))
    
    return {"evolved_ideas": evolved}

@app.post("/techniques/parallel")
async def run_parallel_divergence():
    """平行发散模式"""
    global session, parallel_divergence
    if not session or not parallel_divergence:
        raise HTTPException(status_code=400, detail="Session not started")
    
    # All agents generate ideas in parallel
    all_ideas = parallel_divergence.generate_parallel_ideas(
        topic=session.topic,
        agents=session.agents
    )
    
    # Add ideas to history
    for idea_set in all_ideas:
        session.add_message(Message(
            f"💡 {idea_set['agent']}",
            f"【平行发散】{idea_set['ideas']}",
            {"mode": "parallel_divergence"}
        ))
    
    # Deduplicate and cluster
    clustered = parallel_divergence.deduplicate_and_cluster(all_ideas, session.topic)
    session.add_message(Message(
        "📋 想法整理",
        clustered,
        {"mode": "clustering"}
    ))
    
    return {"parallel_ideas": all_ideas, "clustered": clustered}

class ChainRequest(BaseModel):
    seed_idea: str

@app.post("/techniques/chain")
async def run_chain_deepening(request: ChainRequest):
    """链式深化模式"""
    global session, chain_deepening
    if not session or not chain_deepening:
        raise HTTPException(status_code=400, detail="Session not started")
    
    chain = chain_deepening.deepen_chain(
        seed_idea=request.seed_idea,
        agents=session.agents,
        topic=session.topic
    )
    
    # Add chain steps to history
    for step in chain:
        session.add_message(Message(
            f"🔗 {step['agent']}",
            f"【链式深化 #{step['step']}】{step['output']}",
            {"mode": "chain_deepening", "step": step['step']}
        ))
    
    return {"chain": chain}

class DebateRequest(BaseModel):
    idea: str
    pro_agent_indices: List[int] = [0]
    con_agent_indices: List[int] = [1]

@app.post("/techniques/debate")
async def run_debate(request: DebateRequest):
    """辩论模式"""
    global session, debate_mode
    if not session or not debate_mode:
        raise HTTPException(status_code=400, detail="Session not started")
    
    pro_agents = [session.agents[i % len(session.agents)] for i in request.pro_agent_indices]
    con_agents = [session.agents[i % len(session.agents)] for i in request.con_agent_indices]
    
    result = debate_mode.run_debate(
        idea=request.idea,
        pro_agents=pro_agents,
        con_agents=con_agents,
        topic=session.topic
    )
    
    # Add debate to history
    for pro in result['pro_arguments']:
        session.add_message(Message(
            f"👍 {pro['agent']}",
            f"【正方论点】{pro['argument']}",
            {"mode": "debate", "side": "pro"}
        ))
    
    for con in result['con_arguments']:
        session.add_message(Message(
            f"👎 {con['agent']}",
            f"【反方论点】{con['argument']}",
            {"mode": "debate", "side": "con"}
        ))
    
    session.add_message(Message(
        "⚖️ 辩论总结",
        result['synthesis'],
        {"mode": "debate", "type": "synthesis"}
    ))
    
    return result

@app.get("/techniques/list")
def list_techniques():
    """列出所有可用的高级技术"""
    return {
        "techniques": [
            {
                "id": "creativity",
                "name": "创意激发",
                "description": "SCAMPER、随机刺激、六顶思考帽、逆向思维",
                "sub_techniques": ["scamper", "random_input", "six_thinking_hats", "reverse_thinking"]
            },
            {
                "id": "evolution",
                "name": "想法进化",
                "description": "通过变异和交叉优化想法"
            },
            {
                "id": "parallel",
                "name": "平行发散",
                "description": "所有智能体同时独立产生想法"
            },
            {
                "id": "chain",
                "name": "链式深化",
                "description": "想法在智能体间传递深化"
            },
            {
                "id": "debate",
                "name": "辩论模式",
                "description": "正反方辩论评估想法"
            }
        ]
    }

# ============ WebSocket Multi-User Endpoints ============

@app.websocket("/ws/{user_name}")
async def websocket_endpoint(websocket: WebSocket, user_name: str, session_id: str = "default"):
    """WebSocket端点 - 支持多用户实时协作"""
    # Verify session exists
    state = get_session_or_create(session_id)
    
    user_id = str(uuid.uuid4())
    await ws_manager.connect(websocket, session_id, user_id, user_name)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # 处理不同类型的消息
            msg_type = data.get("type", "chat")
            
            if msg_type == "chat":
                content = data.get("content", "")
                
                # 检查@提及
                if mention_parser.has_mention(content) and state.session:
                    agent_names = [a.name for a in state.session.agents]
                    mentioned, is_all = mention_parser.get_mentioned_agents(content, agent_names)
                    
                    # 广播人类消息
                    await ws_manager.broadcast(session_id, {
                        "type": "human_message",
                        "user_id": user_id,
                        "user_name": user_name,
                        "content": content,
                        "mentions": mentioned
                    })
                    
                    # 添加到会话历史
                    msg = Message(f"👤 {user_name}", content, {"type": "human", "mentions": mentioned})
                    state.session.add_message(msg)
                    state.session_stats.record_message(f"👤 {user_name}", content, {"type": "human"})
                    
                    # PERSISTENCE
                    save_message_to_db(session_id, f"👤 {user_name}", content, "human")
                    
                    # 触发被@的智能体响应
                    for agent_name in mentioned:
                        agent = next((a for a in state.session.agents if a.name == agent_name), None)
                        if agent and state.llm_client:
                            context = "\n".join([f"{m.sender}: {m.content}" for m in state.session.history[-10:]])
                            prompt = mention_parser.create_mention_prompt(user_name, content, agent_name, context)
                            
                            response = state.llm_client.get_completion(
                                system_prompt=agent.get_system_prompt(),
                                user_prompt=prompt,
                                model=agent.model_name
                            )
                            
                            
                            # 广播智能体响应
                            await ws_manager.broadcast(session_id, {
                                "type": "agent_response",
                                "sender": agent.name,
                                "content": response,
                                "role": agent.role
                            })
                            
                            state.session.add_message(Message(agent.name, response, {"role": agent.role}))
                            state.session_stats.record_message(agent.name, response, {"role": agent.role, "type": "agent"})
                            
                            # PERSISTENCE
                            save_message_to_db(
                                session_id, agent.name, response, "agent", 
                                role=agent.role, model=agent.model_name
                            )
                
                # 如果没有提及，也是一种通用的参与
                else:
                    # 广播消息
                    await ws_manager.broadcast(session_id, {
                        "type": "human_message",
                        "user_id": user_id,
                        "user_name": user_name,
                        "content": content
                    })
                    if state.session:
                         state.session_stats.record_message(f"👤 {user_name}", content, {"type": "human"})
            
            elif msg_type == "typing":
                # 广播输入状态
                await ws_manager.broadcast(session_id, {
                    "type": "user_typing",
                    "user_id": user_id,
                    "user_name": user_name
                }, exclude={user_id})
                
            elif msg_type == "request_users":
                # 发送在线用户列表
                await ws_manager.send_personal_message(session_id, {
                    "type": "online_users",
                    "users": ws_manager.get_online_users(session_id)
                }, user_id)
                
    except WebSocketDisconnect:
        user_name = ws_manager.disconnect(session_id, user_id)
        # 广播离开消息
        await ws_manager.broadcast(session_id, {
            "type": "user_left",
            "user_id": user_id,
            "user_name": user_name,
            "online_count": ws_manager.get_online_count(session_id)
        })

@app.get("/ws/users")
def get_online_users(session_id: str = "default"):
    """Get list of online users"""
    return {
        "online_count": ws_manager.get_online_count(session_id),
        "users": ws_manager.get_online_users(session_id)
    }

# ============ @Mention Endpoints ============

class MentionRequest(BaseModel):
    sender: str
    content: str
    session_id: str = "default"

@app.post("/session/mention")
async def handle_mention(request: MentionRequest):
    """Handle @mention from human user"""
    state = get_session_or_create(request.session_id)
    
    # 记录人类消息
    if not state.session:
        raise HTTPException(status_code=400, detail="会话未开始，请先点击'启动头脑风暴'")
        
    msg = Message(f"👤 {request.sender}", request.content, {"type": "human"})
    state.session.add_message(msg)
    state.session_stats.record_message(f"👤 {request.sender}", request.content, {"type": "human"})
    
    # Trigger interrupt for immediate attention
    state.interrupt_signal = True
    
    # 解析@提及
    if state.session and mention_parser.has_mention(request.content):
        agent_names = [a.name for a in state.session.agents]
        mentioned, is_all = mention_parser.get_mentioned_agents(request.content, agent_names)
        
        # 广播人类消息 (via WebSocket if connected)
        await ws_manager.broadcast(request.session_id, {
            "type": "human_message",
            "user_name": request.sender,
            "content": request.content,
            "mentions": mentioned
        })

        # PERSISTENCE: Save human message
        save_message_to_db(request.session_id, f"👤 {request.sender}", request.content, "human")
        
        # 触发智能体响应
        for agent_name in mentioned:
            agent = next((a for a in state.session.agents if a.name == agent_name), None)
            
            if agent and state.llm_client:
                # Build context
                context = "\n".join([f"{m.sender}: {m.content}" for m in state.session.history[-10:]])
                prompt = mention_parser.create_mention_prompt(request.sender, request.content, agent_name, context)
                
                # Stream or generate response
                # Note: Currently synchronous generation for simplicity in this endpoint, 
                # but could use SSE if we want streaming for mentions too.
                # For now, we'll use non-streaming update to state.
                
                response = state.llm_client.get_completion(
                    system_prompt=agent.get_system_prompt(),
                    user_prompt=prompt,
                    model=agent.model_name
                )
                
                # Record response
                state.session.add_message(Message(agent.name, response, {"role": agent.role}))
                state.session_stats.record_message(agent.name, response, {"role": agent.role, "type": "agent"})
                
                # PERSISTENCE: Save agent response
                save_message_to_db(
                    request.session_id, agent.name, response, "agent", 
                    role=agent.role, model=agent.model_name
                )

                # Broadcast response via WebSocket
                await ws_manager.broadcast(request.session_id, {
                    "type": "agent_response",
                    "sender": agent.name,
                    "content": response,
                    "role": agent.role
                })
                
        return {"status": "processed", "mentions": mentioned}
    
    # 如果没有 Session，或者没有 Mention
    # PERSISTENCE: Save human message even if no mention triggered (just recording)
    if state.session and not mention_parser.has_mention(request.content):
         save_message_to_db(request.session_id, f"👤 {request.sender}", request.content, "human")

    return {"status": "recorded"}

# ============ Statistics Endpoints ============

@app.get("/statistics")
def get_statistics(session_id: str = "default"):
    """获取会话统计数据"""
    state = get_session_or_create(session_id)
    return state.session_stats.get_summary()

@app.get("/statistics/detailed")
def get_detailed_statistics(session_id: str = "default"):
    """获取详细统计数据"""
    state = get_session_or_create(session_id)
    return state.session_stats.to_dict()

@app.get("/statistics/export")
def export_statistics():
    """导出统计数据"""
    return {
        "json_data": session_stats.export_json(),
        "csv_data": session_stats.export_csv_data()
    }

@app.post("/statistics/reset")
def reset_statistics():
    """重置统计数据"""
    session_stats.reset()
    return {"status": "reset", "message": "统计数据已重置"}

# ============ Cross-Domain Knowledge Endpoints ============

@app.get("/knowledge/insight")
def get_cross_domain_insight():
    """获取跨领域洞察"""
    global session
    if not session:
        raise HTTPException(status_code=400, detail="Session not started")
    
    # 初始化知识连接器的LLM客户端
    knowledge_connector.llm_client = llm_client
    insight = knowledge_connector.generate_cross_domain_insight(session.topic)
    
    return insight

@app.get("/knowledge/multiple")
def get_multiple_insights(count: int = 3):
    """获取多个跨领域洞察"""
    global session
    if not session:
        raise HTTPException(status_code=400, detail="Session not started")
    
    knowledge_connector.llm_client = llm_client
    insights = knowledge_connector.get_multiple_insights(session.topic, count)
    
    return {"insights": insights}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

