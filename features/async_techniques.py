# -*- coding: utf-8 -*-
"""
Async Parallel Divergence - True parallel idea generation using asyncio
"""
import asyncio
from typing import List, Dict, Any
from utils.async_llm_client import AsyncLLMClient


class AsyncParallelDivergence:
    """
    Parallel divergence mode with true async execution.
    All agents generate ideas simultaneously using asyncio.gather().
    """
    
    def __init__(self, async_client: AsyncLLMClient):
        self.async_client = async_client
    
    async def generate_parallel_ideas_async(
        self, 
        topic: str, 
        agents: List[Any], 
        context: str = ""
    ) -> List[Dict[str, Any]]:
        """
        All agents generate ideas truly in parallel.
        
        Args:
            topic: The brainstorming topic
            agents: List of Agent objects
            context: Optional discussion context
        
        Returns:
            List of idea dicts: [{"agent": name, "role": role, "ideas": content}, ...]
        """
        # Build prompts for each agent
        prompts = []
        for agent in agents:
            prompt = f"""【平行发散模式】🧠

现在是头脑风暴的平行发散环节。请从你的专业角度({agent.expertise})出发，
针对主题提出2-3个独立的创新想法。

【主题】{topic}

{"【参考上下文】" + context if context else ""}

请直接列出你的想法，每个想法用 • 开头："""
            
            prompts.append({
                "system_prompt": agent.get_system_prompt(),
                "user_prompt": prompt,
                "model": agent.model_name
            })
        
        # Execute all completions in parallel
        responses = await self.async_client.get_parallel_completions(prompts)
        
        # Map responses to agents
        results = []
        for agent, response in zip(agents, responses):
            results.append({
                "agent": agent.name,
                "role": agent.role,
                "ideas": response
            })
        
        return results
    
    async def generate_and_cluster_async(
        self, 
        topic: str, 
        agents: List[Any], 
        context: str = ""
    ) -> Dict[str, Any]:
        """
        Generate parallel ideas and then cluster them.
        
        Returns:
            Dict with parallel_ideas and clustered summary
        """
        # Step 1: Parallel generation
        all_ideas = await self.generate_parallel_ideas_async(topic, agents, context)
        
        # Step 2: Cluster and deduplicate
        ideas_text = "\n".join([
            f"【{item['agent']} ({item['role']})】\n{item['ideas']}"
            for item in all_ideas
        ])
        
        cluster_prompt = f"""请对以下多位专家的想法进行整理和归类：

{ideas_text}

请：
1. 识别共同主题和独特观点
2. 合并相似想法
3. 按主题分类整理
4. 输出结构化的想法清单"""
        
        clustered = await self.async_client.get_completion_async(
            system_prompt="你是创意整理专家，擅长归纳和分类想法。",
            user_prompt=cluster_prompt
        )
        
        return {
            "parallel_ideas": all_ideas,
            "clustered": clustered
        }


class AsyncChainDeepening:
    """
    Chain deepening with async execution.
    Ideas flow through agents sequentially but each step is async.
    """
    
    def __init__(self, async_client: AsyncLLMClient):
        self.async_client = async_client
    
    async def deepen_chain_async(
        self, 
        seed_idea: str, 
        agents: List[Any], 
        topic: str
    ) -> List[Dict[str, Any]]:
        """
        Pass idea through agent chain, each agent deepens it.
        """
        chain = []
        current_idea = seed_idea
        
        for i, agent in enumerate(agents):
            prompt = f"""【链式深化模式】🔗

你是链式深化的第 {i+1} 环。请在前一位专家的想法基础上进行深化和扩展。

【主题】{topic}
【当前想法】{current_idea}

请从你的专业角度({agent.expertise})深化这个想法：
1. 指出优点和可行性
2. 补充具体实现细节
3. 提出改进建议

请用100字以内回应："""
            
            response = await self.async_client.get_completion_async(
                system_prompt=agent.get_system_prompt(),
                user_prompt=prompt,
                model=agent.model_name
            )
            
            chain.append({
                "step": i + 1,
                "agent": agent.name,
                "role": agent.role,
                "input": current_idea,
                "output": response
            })
            
            current_idea = response
        
        return chain


class AsyncDebateMode:
    """
    Debate mode with parallel pro/con arguments.
    """
    
    def __init__(self, async_client: AsyncLLMClient):
        self.async_client = async_client
    
    async def run_debate_async(
        self, 
        idea: str, 
        pro_agents: List[Any], 
        con_agents: List[Any], 
        topic: str
    ) -> Dict[str, Any]:
        """
        Run debate with pro and con arguments generated in parallel.
        """
        # Prepare pro prompts
        pro_prompts = []
        for agent in pro_agents:
            pro_prompts.append({
                "system_prompt": agent.get_system_prompt(),
                "user_prompt": f"""【辩论模式 - 正方】👍

请论证以下想法的优点和可行性：

【主题】{topic}
【待辩论想法】{idea}

请从你的专业角度提供有力的支持论点（100字以内）：""",
                "model": agent.model_name
            })
        
        # Prepare con prompts
        con_prompts = []
        for agent in con_agents:
            con_prompts.append({
                "system_prompt": agent.get_system_prompt(),
                "user_prompt": f"""【辩论模式 - 反方】👎

请指出以下想法的问题和风险：

【主题】{topic}
【待辩论想法】{idea}

请从你的专业角度提供具有建设性的质疑（100字以内）：""",
                "model": agent.model_name
            })
        
        # Execute pro and con arguments in parallel
        pro_responses, con_responses = await asyncio.gather(
            self.async_client.get_parallel_completions(pro_prompts),
            self.async_client.get_parallel_completions(con_prompts)
        )
        
        # Format results
        pro_arguments = [
            {"agent": agent.name, "role": agent.role, "argument": response}
            for agent, response in zip(pro_agents, pro_responses)
        ]
        
        con_arguments = [
            {"agent": agent.name, "role": agent.role, "argument": response}
            for agent, response in zip(con_agents, con_responses)
        ]
        
        # Generate synthesis
        synthesis_prompt = f"""请综合以下辩论内容，给出平衡的结论：

【想法】{idea}

【正方观点】
{chr(10).join([f"• {a['agent']}: {a['argument']}" for a in pro_arguments])}

【反方观点】
{chr(10).join([f"• {a['agent']}: {a['argument']}" for a in con_arguments])}

请给出：
1. 核心共识
2. 主要分歧
3. 建议的行动方向"""
        
        synthesis = await self.async_client.get_completion_async(
            system_prompt="你是中立的辩论主持人，擅长综合各方观点。",
            user_prompt=synthesis_prompt
        )
        
        return {
            "idea": idea,
            "pro_arguments": pro_arguments,
            "con_arguments": con_arguments,
            "synthesis": synthesis
        }
