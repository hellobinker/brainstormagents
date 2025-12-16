# -*- coding: utf-8 -*-
"""
Techniques Routes - Handle advanced brainstorming techniques
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from core.protocol import Message
from core.session_manager import session_manager, SessionState
from features.advanced_techniques import (
    CreativityTechniques, IdeaEvolution, 
    ParallelDivergence, ChainDeepening, DebateMode
)

router = APIRouter(prefix="/techniques", tags=["Techniques"])


# ============ Request Models ============

class CreativityRequest(BaseModel):
    technique: Optional[str] = None
    agent_index: int = 0
    session_id: str = "default"


class IdeaEvolutionRequest(BaseModel):
    ideas: List[str]
    generations: int = 2
    session_id: str = "default"


class ChainRequest(BaseModel):
    seed_idea: str
    session_id: str = "default"


class DebateRequest(BaseModel):
    idea: str
    pro_agent_indices: List[int] = [0]
    con_agent_indices: List[int] = [1]
    session_id: str = "default"


# ============ Helper Functions ============

def get_session_state(session_id: str) -> SessionState:
    """Get session state or raise error"""
    state = session_manager.get_session(session_id)
    if not state or not state.session:
        raise HTTPException(status_code=400, detail="Session not started")
    return state


def get_technique_instances(state: SessionState):
    """Get or create technique instances for a session"""
    if not hasattr(state, '_creativity_techniques'):
        state._creativity_techniques = CreativityTechniques(state.llm_client)
        state._idea_evolution = IdeaEvolution(state.llm_client)
        state._parallel_divergence = ParallelDivergence(state.llm_client)
        state._chain_deepening = ChainDeepening(state.llm_client)
        state._debate_mode = DebateMode(state.llm_client)
    
    return (
        state._creativity_techniques,
        state._idea_evolution,
        state._parallel_divergence,
        state._chain_deepening,
        state._debate_mode
    )


# ============ Routes ============

@router.get("/list")
def list_techniques():
    """List all available advanced techniques"""
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


@router.post("/creativity")
async def apply_creativity_technique(request: CreativityRequest):
    """Apply creativity stimulation technique"""
    state = get_session_state(request.session_id)
    creativity, _, _, _, _ = get_technique_instances(state)
    
    agent = state.session.agents[request.agent_index % len(state.session.agents)]
    context = "\n".join([f"{m.sender}: {m.content}" for m in state.session.history[-10:]])
    
    result = creativity.stimulate_creativity(
        topic=state.session.topic,
        context=context,
        agent_role=agent.role,
        technique=request.technique
    )
    
    state.session.add_message(Message(
        f"💡 {agent.name}",
        f"【{result['technique_name']}】\n{result['result']}",
        {"technique": result['technique']}
    ))
    
    return result


@router.post("/evolution")
async def evolve_ideas(request: IdeaEvolutionRequest):
    """Idea evolution algorithm"""
    state = get_session_state(request.session_id)
    _, idea_evolution, _, _, _ = get_technique_instances(state)
    
    evolved = idea_evolution.evolve_ideas(
        ideas=request.ideas,
        topic=state.session.topic,
        generations=request.generations
    )
    
    for item in evolved:
        state.session.add_message(Message(
            "🧬 想法进化",
            f"【{item['type']}】{item['result']}",
            {"evolution_type": item['type']}
        ))
    
    return {"evolved_ideas": evolved}


@router.post("/parallel")
async def run_parallel_divergence(session_id: str = "default"):
    """Parallel divergence mode - all agents generate ideas simultaneously"""
    state = get_session_state(session_id)
    _, _, parallel_divergence, _, _ = get_technique_instances(state)
    
    all_ideas = parallel_divergence.generate_parallel_ideas(
        topic=state.session.topic,
        agents=state.session.agents
    )
    
    for idea_set in all_ideas:
        state.session.add_message(Message(
            f"💡 {idea_set['agent']}",
            f"【平行发散】{idea_set['ideas']}",
            {"mode": "parallel_divergence"}
        ))
    
    clustered = parallel_divergence.deduplicate_and_cluster(all_ideas, state.session.topic)
    state.session.add_message(Message(
        "📋 想法整理",
        clustered,
        {"mode": "clustering"}
    ))
    
    return {"parallel_ideas": all_ideas, "clustered": clustered}


@router.post("/chain")
async def run_chain_deepening(request: ChainRequest):
    """Chain deepening mode"""
    state = get_session_state(request.session_id)
    _, _, _, chain_deepening, _ = get_technique_instances(state)
    
    chain = chain_deepening.deepen_chain(
        seed_idea=request.seed_idea,
        agents=state.session.agents,
        topic=state.session.topic
    )
    
    for step in chain:
        state.session.add_message(Message(
            f"🔗 {step['agent']}",
            f"【链式深化 #{step['step']}】{step['output']}",
            {"mode": "chain_deepening", "step": step['step']}
        ))
    
    return {"chain": chain}


@router.post("/debate")
async def run_debate(request: DebateRequest):
    """Debate mode"""
    state = get_session_state(request.session_id)
    _, _, _, _, debate_mode = get_technique_instances(state)
    
    pro_agents = [state.session.agents[i % len(state.session.agents)] for i in request.pro_agent_indices]
    con_agents = [state.session.agents[i % len(state.session.agents)] for i in request.con_agent_indices]
    
    result = debate_mode.run_debate(
        idea=request.idea,
        pro_agents=pro_agents,
        con_agents=con_agents,
        topic=state.session.topic
    )
    
    for pro in result['pro_arguments']:
        state.session.add_message(Message(
            f"👍 {pro['agent']}",
            f"【正方论点】{pro['argument']}",
            {"mode": "debate", "side": "pro"}
        ))
    
    for con in result['con_arguments']:
        state.session.add_message(Message(
            f"👎 {con['agent']}",
            f"【反方论点】{con['argument']}",
            {"mode": "debate", "side": "con"}
        ))
    
    state.session.add_message(Message(
        "⚖️ 辩论总结",
        result['synthesis'],
        {"mode": "debate", "type": "synthesis"}
    ))
    
    return result
