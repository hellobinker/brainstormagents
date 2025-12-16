# -*- coding: utf-8 -*-
"""
Stream Service - Handles SSE streaming for brainstorming phases
"""
from typing import AsyncGenerator
import json
import asyncio
import datetime

from core.protocol import Message
from core.facilitator import PHASE_CONFIG
from core.session_manager import session_manager, SessionState
from database import SessionLocal, Message as DBMessage


def create_sse_message(event: str, data: dict) -> str:
    """Create SSE formatted message"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def save_message_to_db(session_id: str, sender: str, content: str, msg_type: str, 
                       phase: str = None, role: str = None, model: str = None):
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
    intro = state.llm_client.get_completion(
        system_prompt=state.facilitator.get_system_prompt(),
        user_prompt=f"Please introduce the '{phase_name}' phase for the topic: {topic}. Be brief and encouraging.",
        model=state.facilitator.model_name
    )
    
    yield create_sse_message("message", {
        "sender": "主持人",
        "content": intro,
        "type": "facilitator",
        "phase": state.facilitator.current_phase.value
    })
    
    state.session.add_message(Message("主持人", intro, {
        "type": "facilitator_intro", 
        "phase": state.facilitator.current_phase.value
    }))
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
                is_interrupt = state.interrupt_signal
                if is_interrupt:
                    state.interrupt_signal = False
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
                
                # Check if paused
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
                    
                    yield create_sse_message("message_chunk", {
                        "sender": agent.name,
                        "chunk": chunk,
                        "type": "agent",
                        "role": agent.role,
                        "emotion": agent.current_emotion,
                        "model": agent.model_name,
                        "phase": state.facilitator.current_phase.value
                    })
                    
                    await asyncio.sleep(0.05)
                
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
                
                # Update visualization
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


async def run_full_session_stream(session_id: str = "default") -> AsyncGenerator[str, None]:
    """Run the complete brainstorming session with all phases"""
    state = session_manager.get_session(session_id)
    
    if not state:
        state = session_manager.sessions.get(session_id)
    
    if not state or not state.session or not state.facilitator:
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
    
    summary = state.facilitator.generate_final_summary(state.session.topic, history_data)
    
    state.session.add_message(Message("📋 创新方案报告", summary, {"type": "summary"}))
    state.session_stats.record_message("System", summary, {"type": "summary"})
    
    # PERSISTENCE
    save_message_to_db(state.session_id, "System", summary, "summary")
    
    yield create_sse_message("summary", {"content": summary})
    
    # Final cleanup
    yield create_sse_message("session_complete", {"topic": state.session.topic})
