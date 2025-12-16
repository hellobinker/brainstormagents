"""
辩论模式工具

实现正反方辩论，评估想法的优劣
"""
from typing import Dict, List, Any
from google.adk.tools import ToolContext


def argue_for(
    idea: str,
    topic: str,
    agent_perspective: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """为想法进行正方论证。
    
    从支持者的角度，阐述想法的价值、优势和可行性。
    
    Args:
        idea: 待辩护的想法
        topic: 讨论主题
        agent_perspective: 辩护者的专业视角 (如 "技术专家", "商业分析师" 等)
        tool_context: ADK 工具上下文
        
    Returns:
        dict: 正方论证指导
    """
    argument_angles = [
        "这个想法解决了什么核心痛点？",
        "实施这个想法有哪些技术优势？",
        "从商业角度，这个想法能创造什么价值？",
        "与现有方案相比，这个想法有什么独特之处？",
        "这个想法如何适应未来趋势？"
    ]
    
    # 记录辩论
    debate_log = tool_context.state.get("debate_log", [])
    debate_log.append({
        "type": "pro",
        "idea": idea,
        "perspective": agent_perspective
    })
    tool_context.state["debate_log"] = debate_log
    
    return {
        "debate_side": "pro",
        "debate_emoji": "👍",
        "idea": idea,
        "topic": topic,
        "perspective": agent_perspective,
        "argument_angles": argument_angles,
        "instruction": f"👍 【正方辩论】\n\n"
                      f"你作为「{agent_perspective}」，需要为以下想法辩护：\n\n"
                      f"💡 想法: {idea}\n\n"
                      f"📌 主题: {topic}\n\n"
                      f"请从你的专业角度，列出 3 个支持这个想法的论点。\n"
                      f"可以考虑以下角度:\n" +
                      "\n".join([f"• {angle}" for angle in argument_angles[:3]])
    }


def argue_against(
    idea: str,
    topic: str,
    agent_perspective: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """对想法进行反方质疑。
    
    从批评者的角度，指出想法的问题、风险和挑战。
    
    Args:
        idea: 待质疑的想法
        topic: 讨论主题
        agent_perspective: 质疑者的专业视角
        tool_context: ADK 工具上下文
        
    Returns:
        dict: 反方论证指导
    """
    critique_angles = [
        "这个想法有哪些技术实现上的困难？",
        "从成本和资源角度，这个想法可行吗？",
        "这个想法可能面临哪些市场风险？",
        "有没有更简单、更成熟的替代方案？",
        "这个想法的假设是否站得住脚？"
    ]
    
    # 记录辩论
    debate_log = tool_context.state.get("debate_log", [])
    debate_log.append({
        "type": "con",
        "idea": idea,
        "perspective": agent_perspective
    })
    tool_context.state["debate_log"] = debate_log
    
    return {
        "debate_side": "con",
        "debate_emoji": "👎",
        "idea": idea,
        "topic": topic,
        "perspective": agent_perspective,
        "critique_angles": critique_angles,
        "instruction": f"👎 【反方辩论】\n\n"
                      f"你作为「{agent_perspective}」，需要对以下想法提出质疑：\n\n"
                      f"💡 想法: {idea}\n\n"
                      f"📌 主题: {topic}\n\n"
                      f"请从你的专业角度，列出 3 个质疑这个想法的论点。\n"
                      f"可以考虑以下角度:\n" +
                      "\n".join([f"• {angle}" for angle in critique_angles[:3]])
    }


def synthesize_debate(
    idea: str,
    topic: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """综合辩论结论。
    
    作为中立裁判，综合正反双方观点，得出客观结论。
    
    Args:
        idea: 辩论的想法
        topic: 讨论主题
        tool_context: ADK 工具上下文
        
    Returns:
        dict: 综合结论指导
    """
    debate_log = tool_context.state.get("debate_log", [])
    
    # 提取本想法的辩论记录
    pro_entries = [d for d in debate_log if d.get("idea") == idea and d.get("type") == "pro"]
    con_entries = [d for d in debate_log if d.get("idea") == idea and d.get("type") == "con"]
    
    synthesis_framework = [
        {
            "aspect": "核心价值",
            "question": "综合双方观点，这个想法的核心价值是什么？"
        },
        {
            "aspect": "主要风险",
            "question": "需要重点关注哪些风险和挑战？"
        },
        {
            "aspect": "改进建议",
            "question": "如何改进这个想法以扬长避短？"
        },
        {
            "aspect": "最终建议",
            "question": "给出你的建议：推荐 / 谨慎推进 / 暂缓"
        }
    ]
    
    return {
        "idea": idea,
        "topic": topic,
        "debate_emoji": "⚖️",
        "pro_count": len(pro_entries),
        "con_count": len(con_entries),
        "synthesis_framework": synthesis_framework,
        "instruction": f"⚖️ 【辩论综合】\n\n"
                      f"💡 讨论的想法: {idea}\n\n"
                      f"📌 主题: {topic}\n\n"
                      f"辩论情况: {len(pro_entries)} 个正方论点，{len(con_entries)} 个反方论点\n\n"
                      f"请作为中立裁判，综合双方观点，给出客观结论:\n\n" +
                      "\n".join([f"• {f['aspect']}: {f['question']}" 
                                for f in synthesis_framework])
    }


def get_debate_summary(tool_context: ToolContext) -> Dict[str, Any]:
    """获取辩论摘要。
    
    汇总当前会话中所有的辩论活动。
    
    Args:
        tool_context: ADK 工具上下文
        
    Returns:
        dict: 辩论摘要
    """
    debate_log = tool_context.state.get("debate_log", [])
    
    # 按想法分组
    ideas_debated = {}
    for entry in debate_log:
        idea = entry.get("idea", "未知")
        if idea not in ideas_debated:
            ideas_debated[idea] = {"pro": 0, "con": 0}
        ideas_debated[idea][entry.get("type", "pro")] += 1
    
    return {
        "total_debates": len(debate_log),
        "ideas_count": len(ideas_debated),
        "ideas_debated": ideas_debated,
        "summary": f"📊 辩论摘要\n"
                   f"总辩论次数: {len(debate_log)}\n"
                   f"讨论的想法数: {len(ideas_debated)}"
    }
