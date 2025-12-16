"""
会话管理工具

管理头脑风暴会话的状态、阶段和想法收集
"""
from typing import Dict, List, Any
from google.adk.tools import ToolContext
from ..shared.state import BrainstormPhase, PHASE_CONFIG, get_next_phase


def start_brainstorm(topic: str, tool_context: ToolContext) -> Dict[str, Any]:
    """开始一个新的头脑风暴会话。
    
    初始化会话状态，设置主题和初始阶段。
    
    Args:
        topic: 讨论的主题
        tool_context: ADK 工具上下文，用于访问 session state
        
    Returns:
        dict: 包含会话初始化信息的响应
    """
    # 初始化会话状态
    tool_context.state["topic"] = topic
    tool_context.state["phase"] = BrainstormPhase.OPENING.value
    tool_context.state["ideas"] = []
    tool_context.state["round"] = 0
    tool_context.state["agents_spoken"] = []
    
    phase_config = PHASE_CONFIG[BrainstormPhase.OPENING]
    
    return {
        "status": "started",
        "topic": topic,
        "current_phase": BrainstormPhase.OPENING.value,
        "phase_name": phase_config["name"],
        "phase_emoji": phase_config["emoji"],
        "message": f"🎬 头脑风暴会话已启动！\n主题: 「{topic}」\n\n"
                   f"欢迎各位专家参与本次创新讨论。"
    }


def add_idea(
    idea: str,
    agent_name: str,
    category: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """向会话添加一个新想法。
    
    记录专家提出的想法，包含来源和阶段信息。
    
    Args:
        idea: 想法内容
        agent_name: 提出想法的 agent 名称
        category: 想法分类 (如 "创新", "风险", "实现" 等)
        tool_context: ADK 工具上下文
        
    Returns:
        dict: 确认信息和当前想法统计
    """
    ideas = tool_context.state.get("ideas", [])
    current_phase = tool_context.state.get("phase", "unknown")
    
    new_idea = {
        "id": len(ideas) + 1,
        "content": idea,
        "agent": agent_name,
        "category": category,
        "phase": current_phase
    }
    ideas.append(new_idea)
    tool_context.state["ideas"] = ideas
    
    # 记录发言的 agent
    agents_spoken = tool_context.state.get("agents_spoken", [])
    if agent_name not in agents_spoken:
        agents_spoken.append(agent_name)
        tool_context.state["agents_spoken"] = agents_spoken
    
    return {
        "status": "added",
        "idea_id": new_idea["id"],
        "total_ideas": len(ideas),
        "message": f"✅ 想法已记录 (#{new_idea['id']}) - 来自 {agent_name}"
    }


def advance_phase(tool_context: ToolContext) -> Dict[str, Any]:
    """推进到下一个讨论阶段。
    
    根据预定义的阶段流程，将会话推进到下一阶段。
    
    Args:
        tool_context: ADK 工具上下文
        
    Returns:
        dict: 新阶段信息或完成状态
    """
    current_phase_str = tool_context.state.get("phase", BrainstormPhase.OPENING.value)
    next_phase_str = get_next_phase(current_phase_str)
    
    # 检查是否已到最后阶段
    if next_phase_str == current_phase_str:
        return {
            "status": "completed",
            "message": "🎉 头脑风暴所有阶段已完成！",
            "current_phase": current_phase_str
        }
    
    # 更新阶段
    tool_context.state["phase"] = next_phase_str
    tool_context.state["round"] = 0
    tool_context.state["agents_spoken"] = []
    
    try:
        phase_enum = BrainstormPhase(next_phase_str)
        phase_config = PHASE_CONFIG[phase_enum]
        
        return {
            "status": "advanced",
            "previous_phase": current_phase_str,
            "current_phase": next_phase_str,
            "phase_name": phase_config["name"],
            "phase_emoji": phase_config["emoji"],
            "phase_description": phase_config["description"],
            "message": f"{phase_config['emoji']} 进入新阶段: {phase_config['name']}\n"
                       f"{phase_config['description']}"
        }
    except ValueError:
        return {
            "status": "error",
            "message": f"未知阶段: {next_phase_str}"
        }


def get_session_summary(tool_context: ToolContext) -> Dict[str, Any]:
    """获取当前会话的总结信息。
    
    汇总会话的主题、阶段、想法统计等信息。
    
    Args:
        tool_context: ADK 工具上下文
        
    Returns:
        dict: 会话状态摘要
    """
    topic = tool_context.state.get("topic", "未设置")
    phase_str = tool_context.state.get("phase", "未开始")
    ideas = tool_context.state.get("ideas", [])
    agents_spoken = tool_context.state.get("agents_spoken", [])
    
    # 按 agent 分组想法
    ideas_by_agent = {}
    for idea in ideas:
        agent = idea.get("agent", "未知")
        if agent not in ideas_by_agent:
            ideas_by_agent[agent] = []
        ideas_by_agent[agent].append(idea["content"])
    
    # 按类别分组
    ideas_by_category = {}
    for idea in ideas:
        category = idea.get("category", "其他")
        if category not in ideas_by_category:
            ideas_by_category[category] = 0
        ideas_by_category[category] += 1
    
    # 获取阶段名称
    phase_name = "未知"
    phase_emoji = "❓"
    try:
        phase_enum = BrainstormPhase(phase_str)
        phase_config = PHASE_CONFIG[phase_enum]
        phase_name = phase_config["name"]
        phase_emoji = phase_config["emoji"]
    except ValueError:
        pass
    
    return {
        "topic": topic,
        "current_phase": phase_str,
        "phase_name": phase_name,
        "phase_emoji": phase_emoji,
        "total_ideas": len(ideas),
        "agents_participated": agents_spoken,
        "ideas_by_agent": ideas_by_agent,
        "ideas_by_category": ideas_by_category,
        "summary": f"📊 会话摘要\n"
                   f"主题: {topic}\n"
                   f"阶段: {phase_emoji} {phase_name}\n"
                   f"想法数: {len(ideas)}\n"
                   f"参与专家: {', '.join(agents_spoken) if agents_spoken else '暂无'}"
    }


def list_ideas(
    tool_context: ToolContext,
    filter_agent: str = None,
    filter_category: str = None
) -> Dict[str, Any]:
    """列出会话中收集的想法。
    
    可以按 agent 或类别筛选想法。
    
    Args:
        tool_context: ADK 工具上下文
        filter_agent: 可选，筛选特定 agent 的想法
        filter_category: 可选，筛选特定类别的想法
        
    Returns:
        dict: 想法列表
    """
    ideas = tool_context.state.get("ideas", [])
    
    # 应用筛选
    filtered = ideas
    if filter_agent:
        filtered = [i for i in filtered if i.get("agent") == filter_agent]
    if filter_category:
        filtered = [i for i in filtered if i.get("category") == filter_category]
    
    return {
        "total": len(filtered),
        "filter_applied": {
            "agent": filter_agent,
            "category": filter_category
        },
        "ideas": [
            {
                "id": i["id"],
                "content": i["content"],
                "agent": i["agent"],
                "category": i.get("category", "未分类"),
                "phase": i.get("phase", "未知")
            }
            for i in filtered
        ]
    }
