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
from features.websocket_manager import ConnectionManager
from features.mention_parser import MentionParser
from features.statistics import SessionStatistics
import uvicorn
import os
import json
import asyncio
import uuid

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS for SSE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('frontend/index.html')

# Global state
session: Optional[BrainstormingSession] = None
facilitator: Optional[Facilitator] = None
role_switcher = DynamicRoleSwitcher()
emotion_engine = EmotionalIntelligenceEngine()
knowledge_connector = CrossDomainConnector()
visualizer = RealTimeVisualizer()
llm_client = None
is_paused = False  # Pause state

# New feature instances
ws_manager = ConnectionManager()
mention_parser = MentionParser()
session_stats = SessionStatistics()

# Advanced techniques (initialized after llm_client)
creativity_techniques = None
idea_evolution = None
parallel_divergence = None
chain_deepening = None
debate_mode = None

# Data Models
class AgentConfig(BaseModel):
    name: str
    role: str
    expertise: str
    style: str
    personality_traits: List[str]
    model_name: str = "gpt-5.1"

class StartSessionRequest(BaseModel):
    topic: str
    agents: List[AgentConfig]
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    phase_rounds: Optional[Dict[str, int]] = None  # Custom rounds per phase

class RunPhaseRequest(BaseModel):
    phase: Optional[str] = None

def create_sse_message(event: str, data: dict) -> str:
    """Create SSE formatted message"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

@app.post("/session/start")
def start_session(request: StartSessionRequest):
    global session, llm_client, visualizer, facilitator
    
    # Initialize LLM Client
    DEFAULT_API_KEY = "sk-j3MQdosfgMzzOHOtA7MUnrxHSNIdaO44FzMlk7RRJIcjrf8r"
    DEFAULT_BASE_URL = "https://yunwu.ai/v1"
    
    api_key = request.api_key or os.environ.get("OPENAI_API_KEY") or DEFAULT_API_KEY
    base_url = request.base_url or os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL
    
    llm_client = LLMClient(api_key=api_key, base_url=base_url)
    
    # Initialize advanced techniques
    from features.advanced_techniques import (
        CreativityTechniques, IdeaEvolution, ParallelDivergence, 
        ChainDeepening, DebateMode
    )
    global creativity_techniques, idea_evolution, parallel_divergence, chain_deepening, debate_mode
    creativity_techniques = CreativityTechniques(llm_client)
    idea_evolution = IdeaEvolution(llm_client)
    parallel_divergence = ParallelDivergence(llm_client)
    chain_deepening = ChainDeepening(llm_client)
    debate_mode = DebateMode(llm_client)
    
    # Create Agents
    agents = []
    for config in request.agents:
        agent = Agent(
            name=config.name,
            role=config.role,
            expertise=config.expertise,
            style=config.style,
            personality_traits=config.personality_traits,
            model_name=config.model_name
        )
        agents.append(agent)
    
    # Initialize Session and Facilitator with custom rounds
    session = BrainstormingSession(request.topic, agents, llm_client)
    facilitator = Facilitator(
        llm_client, 
        model_name="gpt-5.1",
        custom_rounds=request.phase_rounds or {}
    )
    visualizer = RealTimeVisualizer()
    
    return {
        "message": "Session started",
        "topic": request.topic,
        "agent_count": len(agents),
        "current_phase": facilitator.current_phase.value,
        "phase_name": PHASE_CONFIG[facilitator.current_phase]["name"],
        "phase_rounds": request.phase_rounds or {}
    }

async def generate_phase_stream(topic: str, agents: List[Agent]) -> AsyncGenerator[str, None]:
    """Generate streaming responses for a phase"""
    global session, facilitator, visualizer
    
    if not facilitator or not session:
        yield create_sse_message("error", {"message": "Session not started"})
        return
    
    phase_config = facilitator.get_phase_config()
    phase_name = phase_config["name"]
    phase_emoji = phase_config["emoji"]
    phase_rounds = phase_config["rounds"]
    
    # 1. Facilitator opening for this phase
    yield create_sse_message("phase_start", {
        "phase": facilitator.current_phase.value,
        "name": phase_name,
        "emoji": phase_emoji
    })
    
    await asyncio.sleep(0.1)  # Small delay for UI
    
    # Get facilitator's opening statement
    facilitator_message = facilitator.get_phase_opening(topic, [a.name for a in agents])
    
    yield create_sse_message("message", {
        "sender": "🎙️ 主持人",
        "content": facilitator_message,
        "type": "facilitator",
        "phase": facilitator.current_phase.value
    })
    
    # Add to session history
    session.add_message(Message("🎙️ 主持人", facilitator_message, {"phase": facilitator.current_phase.value}))
    
    await asyncio.sleep(0.3)
    
    # 2. If this phase has agent rounds, run them
    if phase_rounds > 0:
        agent_prompt = facilitator.get_agent_prompt_for_phase(topic)
        
        for round_num in range(phase_rounds):
            if phase_rounds > 1:
                yield create_sse_message("round_start", {"round": round_num + 1, "total": phase_rounds})
                await asyncio.sleep(0.1)
            
            for agent in agents:
                # Update emotions
                emotion_engine.update_emotions([agent], session.history)
                
                # Build context
                history_text = "\n".join([f"{m.sender}: {m.content}" for m in session.history[-15:]])
                
                full_prompt = f"""{agent_prompt}

【讨论历史】
{history_text}

请开始你的发言："""
                
                # Check if paused
                global is_paused
                while is_paused:
                    yield create_sse_message("paused", {"status": "paused"})
                    await asyncio.sleep(1)
                
                # Generate response
                yield create_sse_message("agent_typing", {
                    "agent": agent.name,
                    "role": agent.role
                })
                
                await asyncio.sleep(0.1)
                
                response = llm_client.get_completion(
                    system_prompt=agent.get_system_prompt(),
                    user_prompt=full_prompt,
                    model=agent.model_name
                )
                
                # Stream the response
                yield create_sse_message("message", {
                    "sender": agent.name,
                    "content": response,
                    "type": "agent",
                    "role": agent.role,
                    "emotion": agent.current_emotion,
                    "model": agent.model_name,
                    "phase": facilitator.current_phase.value
                })
                
                session.add_message(Message(agent.name, response, {
                    "phase": facilitator.current_phase.value,
                    "role": agent.role,
                    "round": session.rounds
                }))
                
                # Update visualization and send graph data
                visualizer.update_graph(session.history)
                graph_json = visualizer.export_data()
                graph_data = json.loads(graph_json)
                yield create_sse_message("graph_update", graph_data)
                
                await asyncio.sleep(0.2)
        
        session.rounds += 1
    
    # 3. Phase complete
    yield create_sse_message("phase_complete", {
        "phase": facilitator.current_phase.value,
        "name": phase_name
    })

@app.get("/session/stream_phase")
async def stream_phase():
    """Stream a single phase of the brainstorming session"""
    global session, facilitator
    
    if not session or not facilitator:
        return {"error": "Session not started"}
    
    return StreamingResponse(
        generate_phase_stream(session.topic, session.agents),
        media_type="text/event-stream"
    )

@app.post("/session/next_phase")
async def next_phase():
    """Advance to the next phase"""
    global facilitator
    
    if not facilitator:
        raise HTTPException(status_code=400, detail="Session not started")
    
    has_more = facilitator.advance_phase()
    phase_config = facilitator.get_phase_config()
    
    return {
        "has_more": has_more,
        "current_phase": facilitator.current_phase.value,
        "phase_name": phase_config["name"],
        "phase_emoji": phase_config["emoji"]
    }

async def run_full_session_stream() -> AsyncGenerator[str, None]:
    """Run the complete brainstorming session with all phases"""
    global session, facilitator
    
    if not session or not facilitator:
        yield create_sse_message("error", {"message": "Session not started"})
        return
    
    yield create_sse_message("session_start", {
        "topic": session.topic,
        "agent_count": len(session.agents)
    })
    
    # Run through all phases
    while True:
        async for msg in generate_phase_stream(session.topic, session.agents):
            yield msg
        
        await asyncio.sleep(0.5)
        
        has_more = facilitator.advance_phase()
        if not has_more:
            break
        
        yield create_sse_message("phase_transition", {
            "next_phase": facilitator.current_phase.value,
            "next_name": PHASE_CONFIG[facilitator.current_phase]["name"]
        })
        
        await asyncio.sleep(0.3)
    
    # Generate final summary
    yield create_sse_message("generating_summary", {"message": "正在生成创新方案报告..."})
    
    history_data = [{"sender": m.sender, "content": m.content} for m in session.history]
    summary = facilitator.generate_final_summary(session.topic, history_data)
    
    session.add_message(Message("📋 创新方案报告", summary, {"type": "summary"}))
    
    yield create_sse_message("summary", {
        "content": summary
    })
    
    yield create_sse_message("session_complete", {
        "total_messages": len(session.history),
        "total_rounds": session.rounds
    })

@app.get("/session/stream_full")
async def stream_full_session():
    """Stream the complete brainstorming session"""
    global session, facilitator
    
    if not session or not facilitator:
        return {"error": "Session not started"}
    
    return StreamingResponse(
        run_full_session_stream(),
        media_type="text/event-stream"
    )

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
async def websocket_endpoint(websocket: WebSocket, user_name: str):
    """WebSocket端点 - 支持多用户实时协作"""
    user_id = str(uuid.uuid4())
    await ws_manager.connect(websocket, user_id, user_name)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # 处理不同类型的消息
            msg_type = data.get("type", "chat")
            
            if msg_type == "chat":
                content = data.get("content", "")
                
                # 检查@提及
                if mention_parser.has_mention(content) and session:
                    agent_names = [a.name for a in session.agents]
                    mentioned, is_all = mention_parser.get_mentioned_agents(content, agent_names)
                    
                    # 广播人类消息
                    await ws_manager.broadcast({
                        "type": "human_message",
                        "user_id": user_id,
                        "user_name": user_name,
                        "content": content,
                        "mentions": mentioned
                    })
                    
                    # 添加到会话历史
                    msg = Message(f"👤 {user_name}", content, {"type": "human", "mentions": mentioned})
                    session.add_message(msg)
                    session_stats.record_message(f"👤 {user_name}", content, {"type": "human"})
                    
                    # 触发被@的智能体响应
                    for agent_name in mentioned:
                        agent = next((a for a in session.agents if a.name == agent_name), None)
                        if agent and llm_client:
                            context = "\n".join([f"{m.sender}: {m.content}" for m in session.history[-10:]])
                            prompt = mention_parser.create_mention_prompt(user_name, content, agent_name, context)
                            
                            response = llm_client.get_completion(
                                system_prompt=agent.get_system_prompt(),
                                user_prompt=prompt,
                                model=agent.model_name
                            )
                            
                            # 广播智能体响应
                            await ws_manager.broadcast({
                                "type": "agent_response",
                                "agent": agent_name,
                                "content": response,
                                "reply_to": user_name
                            })
                            
                            session.add_message(Message(agent_name, response, {"type": "mention_response"}))
                            session_stats.record_message(agent_name, response, {"type": "mention_response"})
                            session_stats.record_mention(f"👤 {user_name}", agent_name)
                else:
                    # 普通聊天消息
                    await ws_manager.broadcast({
                        "type": "human_message",
                        "user_id": user_id,
                        "user_name": user_name,
                        "content": content
                    })
                    
                    if session:
                        msg = Message(f"👤 {user_name}", content, {"type": "human"})
                        session.add_message(msg)
                        session_stats.record_message(f"👤 {user_name}", content, {"type": "human"})
            
            elif msg_type == "typing":
                await ws_manager.broadcast({
                    "type": "user_typing",
                    "user_id": user_id,
                    "user_name": user_name
                }, exclude={user_id})
            
            elif msg_type == "request_users":
                await ws_manager.send_personal_message({
                    "type": "online_users",
                    "users": ws_manager.get_online_users()
                }, user_id)
                
    except WebSocketDisconnect:
        user_name = ws_manager.disconnect(user_id)
        await ws_manager.broadcast({
            "type": "user_left",
            "user_id": user_id,
            "user_name": user_name,
            "online_count": ws_manager.get_online_count()
        })

@app.get("/ws/users")
def get_online_users():
    """获取在线用户列表"""
    return {
        "online_count": ws_manager.get_online_count(),
        "users": ws_manager.get_online_users()
    }

# ============ @Mention Endpoints ============

class MentionRequest(BaseModel):
    sender: str
    content: str

@app.post("/session/mention")
async def handle_mention(request: MentionRequest):
    """处理@提及消息（或普通人类消息）"""
    global session, llm_client
    
    if not session:
        raise HTTPException(status_code=400, detail="Session not started")
    
    # Always add user message to session history first
    user_msg = Message(f"👤 {request.sender}", request.content, {"type": "human"})
    session.add_message(user_msg)
    session_stats.record_message(f"👤 {request.sender}", request.content, {"type": "human"})
    
    # Broadcast to WebSocket clients
    await ws_manager.broadcast({
        "type": "human_message",
        "sender": request.sender,
        "content": request.content
    })
    
    # Check for @mentions
    agent_names = [a.name for a in session.agents]
    mentioned, is_all = mention_parser.get_mentioned_agents(request.content, agent_names)
    
    responses = []
    
    if mentioned:
        for agent_name in mentioned:
            agent = next((a for a in session.agents if a.name == agent_name), None)
            if agent and llm_client:
                context = "\n".join([f"{m.sender}: {m.content}" for m in session.history[-10:]])
                prompt = mention_parser.create_mention_prompt(request.sender, request.content, agent_name, context)
                
                response = llm_client.get_completion(
                    system_prompt=agent.get_system_prompt(),
                    user_prompt=prompt,
                    model=agent.model_name
                )
                
                # 添加到历史
                session.add_message(Message(agent_name, response, {"type": "mention_response", "reply_to": request.sender}))
                session_stats.record_message(agent_name, response, {"type": "mention_response"})
                session_stats.record_mention(request.sender, agent_name)
                
                responses.append({
                    "agent": agent_name,
                    "response": response
                })
                
                # 广播给WebSocket客户端
                await ws_manager.broadcast({
                    "type": "agent_response",
                    "agent": agent_name,
                    "content": response,
                    "reply_to": request.sender
                })
    
    return {
        "status": "success",
        "mentioned_agents": mentioned,
        "responses": responses
    }

# ============ Statistics Endpoints ============

@app.get("/statistics")
def get_statistics():
    """获取会话统计数据"""
    return session_stats.get_summary()

@app.get("/statistics/detailed")
def get_detailed_statistics():
    """获取详细统计数据"""
    return {
        "summary": session_stats.get_summary(),
        "phases": session_stats.get_phase_breakdown(),
        "interaction_network": session_stats.get_interaction_network(),
        "timeline": session_stats.get_timeline_data()[-50:]
    }

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

