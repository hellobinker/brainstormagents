"""
想法进化工具

通过变异、交叉等遗传算法思想优化创意想法
"""
import random
from typing import Dict, List, Any
from google.adk.tools import ToolContext


def evolve_ideas(
    ideas: str,
    evolution_type: str,
    topic: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """对想法进行进化变异。
    
    使用多种变异策略优化想法：
    - amplify: 放大核心优势
    - minimize: 简化到最小可行版本
    - combine: 与其他领域结合
    - reverse: 反转关键假设
    - extreme: 推向极端
    
    Args:
        ideas: 要进化的想法（可以是多个，用分号分隔）
        evolution_type: 进化类型 (amplify/minimize/combine/reverse/extreme)
        topic: 讨论主题
        tool_context: ADK 工具上下文
        
    Returns:
        dict: 进化后的想法和过程说明
    """
    mutations = {
        "amplify": {
            "name": "放大变异",
            "emoji": "🔍",
            "description": "放大这个想法的核心优势，让它更加突出、更有影响力",
            "prompt": "如何让这个想法的优势更加明显？如何扩大它的影响范围？"
        },
        "minimize": {
            "name": "简化变异",
            "emoji": "✂️",
            "description": "简化这个想法，找到最小可行版本，去除非必要元素",
            "prompt": "这个想法的核心是什么？如何用最少的资源实现核心价值？"
        },
        "combine": {
            "name": "跨界变异",
            "emoji": "🔗",
            "description": "将这个想法与另一个领域的成功案例或概念结合",
            "prompt": "其他领域有什么成功经验可以借鉴？如何实现跨界融合？"
        },
        "reverse": {
            "name": "反转变异",
            "emoji": "🔄",
            "description": "反转这个想法的某个关键假设，看看会产生什么新可能",
            "prompt": "这个想法有哪些基本假设？如果反转这些假设会怎样？"
        },
        "extreme": {
            "name": "极端变异",
            "emoji": "⚡",
            "description": "把这个想法推向极端，看看会发生什么，发现边界可能性",
            "prompt": "如果把这个想法推到极致会怎样？极端情况下有什么启发？"
        }
    }
    
    # 如果类型无效，随机选择
    if evolution_type not in mutations:
        evolution_type = random.choice(list(mutations.keys()))
    
    mutation_info = mutations[evolution_type]
    
    # 将想法添加到进化历史
    evolution_history = tool_context.state.get("evolution_history", [])
    evolution_record = {
        "original_ideas": ideas,
        "mutation_type": evolution_type,
        "mutation_name": mutation_info["name"],
        "topic": topic
    }
    evolution_history.append(evolution_record)
    tool_context.state["evolution_history"] = evolution_history
    
    return {
        "mutation_type": evolution_type,
        "mutation_name": mutation_info["name"],
        "mutation_emoji": mutation_info["emoji"],
        "description": mutation_info["description"],
        "original_ideas": ideas,
        "topic": topic,
        "instruction": f"{mutation_info['emoji']} 【{mutation_info['name']}】\n\n"
                      f"原始想法: {ideas}\n\n"
                      f"变异方向: {mutation_info['description']}\n\n"
                      f"思考引导: {mutation_info['prompt']}\n\n"
                      f"请生成变异后的新想法。"
    }


def crossover_ideas(
    idea_a: str,
    idea_b: str,
    topic: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """交叉两个想法，产生融合新想法。
    
    借鉴遗传算法的交叉操作，将两个不同想法的优势
    结合在一起，产生具有双方优点的新想法。
    
    Args:
        idea_a: 第一个想法
        idea_b: 第二个想法
        topic: 讨论主题
        tool_context: ADK 工具上下文
        
    Returns:
        dict: 交叉指导和融合提示
    """
    crossover_strategies = [
        {
            "name": "优势融合",
            "description": "提取两个想法各自的核心优势，创造性地融合在一起",
            "prompt": "想法A的优势是什么？想法B的优势是什么？如何同时拥有这两个优势？"
        },
        {
            "name": "补充短板",
            "description": "用一个想法的优势来弥补另一个想法的不足",
            "prompt": "想法A有什么不足？想法B能否补充这个不足？反过来呢？"
        },
        {
            "name": "层次嵌套",
            "description": "将一个想法嵌入到另一个想法中，形成层次结构",
            "prompt": "想法A可以作为想法B的一部分吗？或者反过来？如何嵌套？"
        },
        {
            "name": "场景切换",
            "description": "在想法A的场景下使用想法B的方法，或反过来",
            "prompt": "如果在想法A的应用场景中使用想法B的核心方法，会产生什么？"
        }
    ]
    
    strategy = random.choice(crossover_strategies)
    
    # 记录交叉操作
    crossover_history = tool_context.state.get("crossover_history", [])
    crossover_history.append({
        "idea_a": idea_a,
        "idea_b": idea_b,
        "strategy": strategy["name"],
        "topic": topic
    })
    tool_context.state["crossover_history"] = crossover_history
    
    return {
        "crossover_strategy": strategy["name"],
        "strategy_description": strategy["description"],
        "idea_a": idea_a,
        "idea_b": idea_b,
        "topic": topic,
        "instruction": f"🧬 【想法交叉】- {strategy['name']}\n\n"
                      f"想法 A: {idea_a}\n\n"
                      f"想法 B: {idea_b}\n\n"
                      f"交叉策略: {strategy['description']}\n\n"
                      f"思考引导: {strategy['prompt']}\n\n"
                      f"请生成融合后的新想法。"
    }


def evaluate_idea_fitness(
    idea: str,
    topic: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """评估想法的适应度/质量。
    
    从多个维度评估一个想法的质量，用于后续的选择优化。
    
    Args:
        idea: 要评估的想法
        topic: 讨论主题
        tool_context: ADK 工具上下文
        
    Returns:
        dict: 评估维度和评分指导
    """
    dimensions = [
        {
            "name": "创新性",
            "emoji": "💡",
            "description": "这个想法有多新颖？是否突破了常规思维？",
            "weight": 0.3
        },
        {
            "name": "可行性",
            "emoji": "🔧",
            "description": "以当前技术和资源，这个想法能实现吗？实现难度如何？",
            "weight": 0.25
        },
        {
            "name": "价值潜力",
            "emoji": "💰",
            "description": "这个想法能创造多大价值？解决了多大的痛点？",
            "weight": 0.25
        },
        {
            "name": "风险程度",
            "emoji": "⚠️",
            "description": "实施这个想法有哪些风险？风险是否可控？",
            "weight": 0.2
        }
    ]
    
    return {
        "idea": idea,
        "topic": topic,
        "evaluation_dimensions": dimensions,
        "instruction": f"📊 【想法评估】\n\n"
                      f"待评估想法: {idea}\n\n"
                      f"请从以下维度评估 (1-10分):\n" +
                      "\n".join([f"• {d['emoji']} {d['name']}: {d['description']}" 
                                for d in dimensions]) +
                      f"\n\n请给出每个维度的评分和简短理由。"
    }
