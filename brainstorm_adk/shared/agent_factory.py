"""
动态 Agent 工厂

根据用户选择的专家列表动态创建 ADK 头脑风暴流程。
支持任意组合的专家参与讨论。
"""
from typing import List, Optional
from google.adk.agents import LlmAgent, SequentialAgent

from .model_config import get_model
from .expert_catalog import ExpertPreset, EXPERT_CATALOG, get_experts_by_indices, get_experts_by_names
from ..tools.creativity import apply_scamper, apply_six_hats, apply_random_stimulus, apply_reverse_thinking


def create_expert_agent(
    expert: ExpertPreset,
    phase: str,
    round_num: int,
    output_key: str,
    context_keys: List[str] = None
) -> LlmAgent:
    """
    根据专家配置和阶段创建 LlmAgent
    
    Args:
        expert: 专家预设
        phase: 阶段名称 (diverge/deepen/evaluate)
        round_num: 轮次
        output_key: 输出键名
        context_keys: 需要读取的上下文键
    """
    # 构建上下文引用
    context_section = ""
    if context_keys:
        context_section = "\n\n【参考上下文】\n" + "\n".join([
            f"- {key}: {{{key}}}" for key in context_keys
        ])
    
    # 根据阶段生成不同指令
    if phase == "diverge":
        instruction = f'''你是{expert.name}，作为{expert.role}。

【你的专业领域】
{expert.expertise}

【你的风格特点】
- 思维风格：{expert.style}
- 性格特质：{", ".join(expert.personality_traits)}

【当前阶段】发散阶段 第{round_num}轮

【你的任务】
1. 从你的专业角度出发，提出 2-3 个创新想法
2. 每个想法要体现你的专业特长
3. 大胆提出，不用担心可行性
4. 与其他专家的想法形成互补{context_section}

请开始分享你的想法：'''
    
    elif phase == "deepen":
        instruction = f'''你是{expert.name}，作为{expert.role}。

【你的专业领域】
{expert.expertise}

【当前阶段】深化阶段 第{round_num}轮

【你的任务】
1. 从你的专业角度深入分析之前的想法
2. 评估技术可行性和实施难点
3. 提出具体的实现建议
4. 识别潜在风险和应对方案{context_section}

请分享你的专业分析：'''
    
    elif phase == "evaluate":
        instruction = f'''你是{expert.name}，作为{expert.role}。

【你的专业领域】
{expert.expertise}

【当前阶段】评估阶段

【你的任务】
1. 从{expert.expertise}角度评估方案
2. 给出专业维度的评分（1-5分）
3. 指出与你专业相关的优势和风险
4. 给出改进建议{context_section}

请给出你的专业评估：'''
    
    else:
        instruction = f'''你是{expert.name}，作为{expert.role}。
专业领域：{expert.expertise}
{context_section}

请分享你的观点：'''
    
    # 根据专业分配工具
    tools = []
    if "创新" in expert.name or "AI" in expert.name or "产品" in expert.name:
        tools = [apply_scamper, apply_random_stimulus]
    elif "分析" in expert.expertise or "评估" in expert.expertise:
        tools = [apply_reverse_thinking]
    elif "设计" in expert.expertise or "规划" in expert.expertise:
        tools = [apply_six_hats]
    
    return LlmAgent(
        name=f"{expert.name.replace(' ', '_')}_{phase}_r{round_num}",
        model=get_model(),
        output_key=output_key,
        description=f"{expert.name} - {phase}阶段",
        instruction=instruction,
        tools=tools if tools else None
    )


def create_dynamic_brainstorm(
    expert_indices: List[int] = None,
    expert_names: List[str] = None,
    diverge_rounds: int = 2,
    deepen_rounds: int = 1,
) -> SequentialAgent:
    """
    创建动态的头脑风暴流程
    
    Args:
        expert_indices: 专家索引列表（从 EXPERT_CATALOG 选择）
        expert_names: 专家名称列表（与 expert_indices 二选一）
        diverge_rounds: 发散阶段轮数
        deepen_rounds: 深化阶段轮数
    
    Returns:
        配置好的 SequentialAgent
    """
    # 获取专家列表
    if expert_names:
        experts = get_experts_by_names(expert_names)
    elif expert_indices:
        experts = get_experts_by_indices(expert_indices)
    else:
        # 默认使用前 3 个专家
        experts = EXPERT_CATALOG[:3]
    
    if not experts:
        raise ValueError("至少需要选择一个专家")
    
    agents = []
    context_keys = []
    
    # 1. 开场
    opening = LlmAgent(
        name="opening_facilitator",
        model=get_model(),
        output_key="opening_message",
        description="开场主持人",
        instruction=f'''你是头脑风暴主持人。

请完成开场：
1. 欢迎参与的专家：{", ".join([e.name for e in experts])}
2. 宣布讨论主题
3. 说明头脑风暴规则

保持简洁（100字以内）。'''
    )
    agents.append(opening)
    context_keys.append("opening_message")
    
    # 2. 定义主题
    define_topic = LlmAgent(
        name="define_topic",
        model=get_model(),
        output_key="topic_definition",
        description="主题定义",
        instruction='''你是主题分析专家。

请分析主题：
1. 明确核心问题
2. 分解 3-4 个关键维度
3. 提出引导性问题

开场信息：{opening_message}'''
    )
    agents.append(define_topic)
    context_keys.append("topic_definition")
    
    # 3. 发散阶段
    for r in range(1, diverge_rounds + 1):
        round_ideas_keys = []
        for i, expert in enumerate(experts):
            output_key = f"diverge_r{r}_{expert.name.replace(' ', '_')}"
            agent = create_expert_agent(
                expert=expert,
                phase="diverge",
                round_num=r,
                output_key=output_key,
                context_keys=context_keys.copy()
            )
            agents.append(agent)
            round_ideas_keys.append(output_key)
        
        # 每轮结束后的汇总
        summary_key = f"diverge_r{r}_summary"
        summary_agent = LlmAgent(
            name=f"diverge_r{r}_summary",
            model=get_model(),
            output_key=summary_key,
            description=f"发散第{r}轮汇总",
            instruction=f'''汇总第{r}轮发散讨论：
1. 列出所有专家提出的核心想法
2. 标注最有潜力的 2-3 个
3. 为下一轮讨论提供方向

本轮专家观点：
''' + "\n".join([f"- {{{key}}}" for key in round_ideas_keys])
        )
        agents.append(summary_agent)
        context_keys = [summary_key]  # 更新上下文为汇总
    
    # 4. 深化阶段
    for r in range(1, deepen_rounds + 1):
        round_analysis_keys = []
        for i, expert in enumerate(experts):
            output_key = f"deepen_r{r}_{expert.name.replace(' ', '_')}"
            agent = create_expert_agent(
                expert=expert,
                phase="deepen",
                round_num=r,
                output_key=output_key,
                context_keys=context_keys.copy()
            )
            agents.append(agent)
            round_analysis_keys.append(output_key)
        
        # 深化阶段汇总
        summary_key = f"deepen_r{r}_summary"
        summary_agent = LlmAgent(
            name=f"deepen_r{r}_summary",
            model=get_model(),
            output_key=summary_key,
            description=f"深化第{r}轮汇总",
            instruction=f'''综合第{r}轮深化分析：
1. 整合各专家的专业分析
2. 识别共同关注的风险点
3. 提炼可行的实施方案

本轮专家分析：
''' + "\n".join([f"- {{{key}}}" for key in round_analysis_keys])
        )
        agents.append(summary_agent)
        context_keys = [summary_key]
    
    # 5. 评估阶段
    eval_keys = []
    for i, expert in enumerate(experts):
        output_key = f"evaluate_{expert.name.replace(' ', '_')}"
        agent = create_expert_agent(
            expert=expert,
            phase="evaluate",
            round_num=1,
            output_key=output_key,
            context_keys=context_keys.copy()
        )
        agents.append(agent)
        eval_keys.append(output_key)
    
    # 评估汇总
    eval_summary = LlmAgent(
        name="evaluation_summary",
        model=get_model(),
        output_key="evaluation_result",
        description="评估汇总",
        instruction='''综合所有专家的评估：
1. 汇总各专业维度的评分
2. 给出综合排名
3. 列出各方案优劣势

专家评估：
''' + "\n".join([f"- {{{key}}}" for key in eval_keys])
    )
    agents.append(eval_summary)
    
    # 6. 整合阶段
    integrate_agent = LlmAgent(
        name="integrate_agent",
        model=get_model(),
        output_key="final_solution",
        description="整合专家",
        instruction='''根据评估结果，整合最终方案：

评估结果：{evaluation_result}

请输出：
## 🎯 最终方案
## 📋 实施计划
## ⚠️ 风险应对'''
    )
    agents.append(integrate_agent)
    
    # 7. 输出报告
    output_agent = LlmAgent(
        name="output_facilitator",
        model=get_model(),
        output_key="final_report",
        description="生成报告",
        instruction=f'''生成完整的创新方案报告。

参与专家：{", ".join([e.name for e in experts])}
最终方案：{{final_solution}}

请按格式输出：
# 🚀 创新方案报告
## 执行摘要
## 核心方案
## 实施路线图
## 风险与应对
## 下一步行动'''
    )
    agents.append(output_agent)
    
    return SequentialAgent(
        name="dynamic_brainstorm_session",
        description=f"动态头脑风暴（{len(experts)}位专家，发散{diverge_rounds}轮，深化{deepen_rounds}轮）",
        sub_agents=agents
    )
