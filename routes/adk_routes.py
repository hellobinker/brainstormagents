"""
FastAPI 路由 - ADK 集成

提供 API 端点来调用 ADK 多智能体头脑风暴系统
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, AsyncGenerator
import asyncio
import json

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# 导入 ADK agents
from brainstorm_adk import root_agent


# 创建路由器
router = APIRouter(prefix="/adk", tags=["ADK"])

# 会话服务
session_service = InMemorySessionService()

# 存储活跃的 runners
active_runners: Dict[str, Runner] = {}


class ADKBrainstormRequest(BaseModel):
    """ADK 头脑风暴请求"""
    topic: str
    session_id: Optional[str] = None


class ADKMessageRequest(BaseModel):
    """ADK 消息请求"""
    session_id: str
    message: str


def get_or_create_runner(session_id: str) -> Runner:
    """获取或创建 Runner 实例"""
    if session_id not in active_runners:
        active_runners[session_id] = Runner(
            agent=root_agent,
            app_name="brainstorm_adk",
            session_service=session_service
        )
    return active_runners[session_id]


@router.post("/start")
async def start_adk_brainstorm(request: ADKBrainstormRequest):
    """
    启动 ADK 头脑风暴会话
    
    输入主题后，会自动运行完整的 7 阶段多轮讨论流程
    """
    import uuid
    
    session_id = request.session_id or str(uuid.uuid4())
    
    # 创建 session
    session = await session_service.create_session(
        app_name="brainstorm_adk",
        user_id="user",
        session_id=session_id
    )
    
    return {
        "session_id": session_id,
        "status": "created",
        "message": f"会话已创建，请发送主题开始讨论"
    }


@router.post("/run")
async def run_adk_brainstorm(request: ADKMessageRequest):
    """
    运行 ADK 头脑风暴（同步模式）
    
    返回完整的讨论结果
    """
    runner = get_or_create_runner(request.session_id)
    
    # 收集所有响应
    responses = []
    
    try:
        async for event in runner.run_async(
            user_id="user",
            session_id=request.session_id,
            new_message=request.message
        ):
            if hasattr(event, 'content') and event.content:
                if hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            responses.append({
                                "agent": getattr(event, 'author', 'unknown'),
                                "text": part.text
                            })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return {
        "session_id": request.session_id,
        "responses": responses
    }


@router.post("/stream")
async def stream_adk_brainstorm(request: ADKMessageRequest):
    """
    运行 ADK 头脑风暴（流式模式）
    
    使用 SSE 流式返回每个 agent 的响应
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        runner = get_or_create_runner(request.session_id)
        
        try:
            async for event in runner.run_async(
                user_id="user",
                session_id=request.session_id,
                new_message=request.message
            ):
                if hasattr(event, 'content') and event.content:
                    if hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                data = {
                                    "agent": getattr(event, 'author', 'unknown'),
                                    "text": part.text
                                }
                                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                                await asyncio.sleep(0.01)  # 小延迟确保流式传输
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/sessions")
async def list_adk_sessions():
    """列出所有活跃的 ADK 会话"""
    return {
        "sessions": list(active_runners.keys())
    }


@router.delete("/session/{session_id}")
async def delete_adk_session(session_id: str):
    """删除 ADK 会话"""
    if session_id in active_runners:
        del active_runners[session_id]
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/agents")
async def list_adk_agents():
    """列出 ADK 系统中的所有 agents"""
    agents = []
    
    # 获取 full_brainstorm_session 中的所有 sub_agents
    if root_agent.sub_agents:
        full_session = root_agent.sub_agents[0]
        for agent in full_session.sub_agents:
            agents.append({
                "name": agent.name,
                "description": getattr(agent, 'description', '')
            })
    
    return {
        "coordinator": {
            "name": root_agent.name,
            "description": root_agent.description
        },
        "workflow_agents": agents,
        "total_steps": len(agents)
    }


# ============================================================
# 专家选择 API
# ============================================================

@router.get("/experts")
async def list_experts():
    """
    列出所有可用的专家（31个）
    
    返回专家列表，包含 index, name, role, expertise 等信息。
    用户可以通过 index 或 name 选择专家参与头脑风暴。
    """
    from brainstorm_adk.shared.expert_catalog import list_all_experts, EXPERT_PRESETS
    
    return {
        "experts": list_all_experts(),
        "presets": {
            name: {
                "indices": indices,
                "description": f"{len(indices)}位专家的预设组合"
            }
            for name, indices in EXPERT_PRESETS.items()
        },
        "total": 31
    }


@router.get("/experts/preset/{preset_name}")
async def get_expert_preset(preset_name: str):
    """
    获取预设的专家组合
    
    可用预设: default, software, hardware, innovation, thermal, smart_home
    """
    from brainstorm_adk.shared.expert_catalog import EXPERT_PRESETS, EXPERT_CATALOG
    
    if preset_name not in EXPERT_PRESETS:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_name}' not found")
    
    indices = EXPERT_PRESETS[preset_name]
    experts = [EXPERT_CATALOG[i] for i in indices]
    
    return {
        "preset": preset_name,
        "experts": [
            {"index": idx, "name": e.name, "role": e.role, "expertise": e.expertise}
            for idx, e in zip(indices, experts)
        ]
    }


class DynamicBrainstormRequest(BaseModel):
    """动态头脑风暴请求"""
    topic: str
    expert_indices: Optional[List[int]] = None  # 专家索引列表
    expert_names: Optional[List[str]] = None    # 或专家名称列表
    preset: Optional[str] = None                # 或使用预设
    diverge_rounds: int = 2                     # 发散轮数
    deepen_rounds: int = 1                      # 深化轮数


@router.post("/dynamic/start")
async def start_dynamic_brainstorm(request: DynamicBrainstormRequest):
    """
    启动动态配置的头脑风暴会话
    
    可以通过以下方式选择专家（三选一）：
    1. expert_indices: 专家索引列表 [0, 5, 30]
    2. expert_names: 专家名称列表 ["产品经理", "AI技术专家"]
    3. preset: 预设组合名称 ("default", "software", "hardware", etc.)
    
    还可以配置轮数：
    - diverge_rounds: 发散阶段轮数（默认2）
    - deepen_rounds: 深化阶段轮数（默认1）
    """
    import uuid
    from brainstorm_adk.shared.agent_factory import create_dynamic_brainstorm
    from brainstorm_adk.shared.expert_catalog import EXPERT_PRESETS
    
    session_id = str(uuid.uuid4())
    
    # 确定专家列表
    expert_indices = request.expert_indices
    expert_names = request.expert_names
    
    if request.preset:
        if request.preset not in EXPERT_PRESETS:
            raise HTTPException(status_code=400, detail=f"Unknown preset: {request.preset}")
        expert_indices = EXPERT_PRESETS[request.preset]
    
    # 创建动态会话
    try:
        dynamic_session = create_dynamic_brainstorm(
            expert_indices=expert_indices,
            expert_names=expert_names,
            diverge_rounds=request.diverge_rounds,
            deepen_rounds=request.deepen_rounds
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # 创建 Runner
    from google.adk.agents import LlmAgent
    from brainstorm_adk.shared.model_config import get_model
    
    # 创建一个专门的协调器
    coordinator = LlmAgent(
        name="dynamic_coordinator",
        model=get_model(),
        description="动态头脑风暴协调器",
        instruction=f"将用户主题转交给 dynamic_brainstorm_session 执行。主题：{request.topic}",
        sub_agents=[dynamic_session]
    )
    
    # 存储到活跃 runners
    active_runners[session_id] = Runner(
        agent=coordinator,
        app_name="brainstorm_adk_dynamic",
        session_service=session_service
    )
    
    # 创建 session
    await session_service.create_session(
        app_name="brainstorm_adk_dynamic",
        user_id="user",
        session_id=session_id
    )
    
    return {
        "session_id": session_id,
        "status": "created",
        "config": {
            "experts": expert_indices or expert_names or "default",
            "diverge_rounds": request.diverge_rounds,
            "deepen_rounds": request.deepen_rounds
        },
        "message": f"动态会话已创建，共 {len(dynamic_session.sub_agents)} 个步骤"
    }
