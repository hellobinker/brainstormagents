# -*- coding: utf-8 -*-
"""
WebSocket Routes - Handle real-time multi-user collaboration
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
import json
import asyncio
import uuid

from core.protocol import Message
from core.session_manager import session_manager, SessionState
from features.websocket_manager import ws_manager
from features.mention_parser import MentionParser
from database import SessionLocal, Message as DBMessage
import datetime

router = APIRouter(tags=["WebSocket"])

mention_parser = MentionParser()


# ============ Request Models ============

class MentionRequest(BaseModel):
    sender: str
    content: str
    session_id: str = "default"


# ============ Helper Functions ============

def get_session_state(session_id: str) -> SessionState:
    """Get session state or raise error"""
    state = session_manager.get_session(session_id)
    if not state or not state.session:
        raise HTTPException(status_code=400, detail="Session not started")
    return state


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


# ============ Routes ============

@router.websocket("/ws/{user_name}")
async def websocket_endpoint(websocket: WebSocket, user_name: str, session_id: str = "default"):
    """WebSocket endpoint for multi-user real-time collaboration"""
    # Generate unique user ID for this connection
    user_id = str(uuid.uuid4())
    
    # Connect using the correct API: connect(websocket, room_id, user_id, user_name)
    await ws_manager.connect(websocket, session_id, user_id, user_name)
    
    try:
        state = session_manager.get_session(session_id)
        
        # Send current state to newly connected user
        if state and state.session:
            await websocket.send_json({
                "type": "state_sync",
                "topic": state.session.topic,
                "phase": state.facilitator.current_phase.value if state.facilitator else None,
                "history": [
                    {"sender": m.sender, "content": m.content[:100], "type": m.metadata.get("type", "agent")}
                    for m in state.session.history[-20:]
                ],
                "agents": [{"name": a.name, "role": a.role} for a in state.session.agents]
            })
        
        # Note: broadcast is already called in ws_manager.connect()
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                content = data.get("content", "")
                
                if state and state.session:
                    # Add to session history
                    state.session.add_message(Message(
                        sender=user_name,
                        content=content,
                        metadata={"type": "human", "source": "websocket"}
                    ))
                    
                    # Trigger interrupt signal for prioritized response
                    state.interrupt_signal = True
                    
                    # Persist
                    save_message_to_db(session_id, user_name, content, "human")
                
                # Broadcast to all users in session using correct API
                await ws_manager.broadcast(session_id, {
                    "type": "human_message",
                    "sender": user_name,
                    "content": content
                })
                
            elif data.get("type") == "typing":
                # Broadcast typing status (exclude sender)
                await ws_manager.broadcast(session_id, {
                    "type": "user_typing",
                    "user": user_name
                }, exclude={user_id})
                
    except WebSocketDisconnect:
        # Disconnect using correct API: disconnect(room_id, user_id)
        ws_manager.disconnect(session_id, user_id)
        # Broadcast user left
        await ws_manager.broadcast(session_id, {
            "type": "user_left",
            "user": user_name,
            "online_count": ws_manager.get_online_count(session_id)
        })


@router.get("/online_users")
def get_online_users(session_id: str = "default"):
    """Get list of online users"""
    # Use correct API: get_online_users(room_id)
    users = ws_manager.get_online_users(session_id)
    return {"users": users}


@router.post("/session/mention")
async def handle_mention(request: MentionRequest):
    """Handle @mention from human user"""
    state = get_session_state(request.session_id)
    
    # Parse mentions
    mentions = mention_parser.parse(request.content)
    
    # Add human message to history
    state.session.add_message(Message(
        sender=request.sender,
        content=request.content,
        metadata={"type": "human", "mentions": mentions}
    ))
    
    # Set interrupt signal for priority response
    state.interrupt_signal = True
    
    # Persist human message
    save_message_to_db(request.session_id, request.sender, request.content, "human")
    
    # If specific agents were mentioned, get their responses
    responses = []
    mentioned_agents = [a for a in state.session.agents if a.name in mentions or a.role in mentions]
    
    if not mentioned_agents:
        mentioned_agents = state.session.agents[:1]  # Default to first agent
    
    context = "\n".join([f"{m.sender}: {m.content}" for m in state.session.history[-10:]])
    
    for agent in mentioned_agents:
        prompt = f"""用户 {request.sender} 刚刚@了你，请直接回应：

【用户消息】{request.content}

【讨论上下文】
{context}

请用100字以内回应用户的问题或观点："""
        
        response = state.llm_client.get_completion(
            system_prompt=agent.get_system_prompt(),
            user_prompt=prompt,
            model=agent.model_name
        )
        
        # Add to history
        state.session.add_message(Message(
            sender=agent.name,
            content=response,
            metadata={"type": "agent", "in_reply_to": request.sender}
        ))
        
        # Persist
        save_message_to_db(
            request.session_id, agent.name, response, "agent",
            role=agent.role, model=agent.model_name
        )
        
        responses.append({
            "agent": agent.name,
            "role": agent.role,
            "response": response
        })
    
    # Broadcast via WebSocket using correct API
    await ws_manager.broadcast(request.session_id, {
        "type": "mention_responses",
        "original": {"sender": request.sender, "content": request.content},
        "responses": responses
    })
    
    return {
        "original_message": request.content,
        "mentions_found": mentions,
        "responses": responses
    }

