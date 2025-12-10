"""
创意激发技术模块
包含多种思维激励技术：SCAMPER、随机刺激、六顶思考帽、逆向思维
"""
import random
from typing import List, Dict, Any

class CreativityTechniques:
    """创意激发技术"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        
    def apply_scamper(self, topic: str, context: str, agent_role: str) -> str:
        """SCAMPER方法：替代、组合、调整、修改、用途转换、消除、重排"""
        scamper_prompts = {
            "S": "替代(Substitute): 有什么可以被替代？材料、流程、部件？",
            "C": "组合(Combine): 能否将多个功能、想法或产品组合？",
            "A": "调整(Adapt): 能否借鉴其他领域的成功经验？",
            "M": "修改(Modify): 能否改变大小、形状、颜色或其他属性？",
            "P": "用途转换(Put to other uses): 能否找到新的应用场景？",
            "E": "消除(Eliminate): 能否简化或去除某些部分？",
            "R": "重排(Rearrange): 能否改变顺序、布局或结构？"
        }
        
        # 随机选择2-3个SCAMPER维度
        selected = random.sample(list(scamper_prompts.items()), k=random.randint(2, 3))
        dimensions = "\n".join([f"- {v}" for k, v in selected])
        
        prompt = f"""请运用SCAMPER创意方法，针对主题进行创新思考。

【主题】{topic}
【背景】{context[:500]}
【你的角色】{agent_role}

【SCAMPER维度】
{dimensions}

请从以上维度出发，结合你的专业背景，提出创新想法（150字以内）："""
        
        return self.llm_client.get_completion(
            system_prompt="你是创新思维专家，擅长运用SCAMPER方法激发创意。",
            user_prompt=prompt,
            model="gemini-3-pro-preview"
        )
    
    def apply_random_stimulus(self, topic: str, context: str, agent_role: str) -> str:
        """随机刺激法：用随机词汇/概念激发联想"""
        random_stimuli = [
            "水流", "蜂巢", "镜子", "云朵", "树根", "蝴蝶效应", "沙漏", "回声",
            "指纹", "蒲公英", "磁铁", "心跳", "螺旋", "光影", "种子", "桥梁",
            "薄膜", "脉冲", "气泡", "织网", "温度计", "透镜", "钟摆", "迷宫"
        ]
        stimulus = random.choice(random_stimuli)
        
        prompt = f"""请运用"随机刺激法"进行创意联想。

【主题】{topic}
【随机刺激词】🎲 {stimulus}
【你的角色】{agent_role}

请思考："{stimulus}"这个概念/意象，能给我们的主题带来什么启发？
尝试建立联系，提出创新想法（100字以内）："""

        return self.llm_client.get_completion(
            system_prompt="你是创意联想专家，擅长从看似无关的事物中发现创新灵感。",
            user_prompt=prompt,
            model="gemini-3-pro-preview"
        )
    
    def apply_six_hats(self, topic: str, context: str, agent_role: str) -> str:
        """六顶思考帽：从不同思维角度分析"""
        hats = {
            "白帽": ("📊", "客观事实", "关注数据、信息和事实，不带情绪地分析"),
            "红帽": ("❤️", "情感直觉", "关注情绪、感受和直觉，不需要解释理由"),
            "黑帽": ("⚫", "谨慎批判", "关注风险、问题和障碍，批判性思考"),
            "黄帽": ("💛", "乐观积极", "关注价值、好处和机会，积极正面思考"),
            "绿帽": ("💚", "创意创新", "关注新想法、替代方案和创造性思维"),
            "蓝帽": ("💙", "过程控制", "关注思维过程、总结和下一步行动")
        }
        
        # 根据agent角色选择合适的帽子
        hat_name, (emoji, focus, desc) = random.choice(list(hats.items()))
        
        prompt = f"""请戴上"{hat_name}"（{focus}）进行思考。

【主题】{topic}
【{hat_name}思维】{emoji} {desc}
【你的角色】{agent_role}

请从{hat_name}的角度，针对主题发表观点（100字以内）："""

        return self.llm_client.get_completion(
            system_prompt=f"你正在运用六顶思考帽方法，现在戴着{hat_name}，专注于{focus}。",
            user_prompt=prompt,
            model="gemini-3-pro-preview"
        )
    
    def apply_reverse_thinking(self, topic: str, context: str, agent_role: str) -> str:
        """逆向思维：从反面思考问题"""
        prompt = f"""请运用"逆向思维"方法进行创新思考。

【主题】{topic}
【背景】{context[:300]}
【你的角色】{agent_role}

【逆向思维步骤】
1. 如果我们想让这个主题彻底失败，应该怎么做？
2. 把这些"失败方法"反过来，能得到什么启发？
3. 提出你的创新建议

请运用逆向思维，提出创新想法（150字以内）："""

        return self.llm_client.get_completion(
            system_prompt="你是逆向思维专家，擅长从问题的反面找到创新突破口。",
            user_prompt=prompt,
            model="gemini-3-pro-preview"
        )
    
    def stimulate_creativity(self, topic: str, context: str, agent_role: str, technique: str = None) -> Dict[str, str]:
        """应用创意激发技术"""
        techniques = {
            "scamper": ("SCAMPER方法", self.apply_scamper),
            "random_input": ("随机刺激法", self.apply_random_stimulus),
            "six_thinking_hats": ("六顶思考帽", self.apply_six_hats),
            "reverse_thinking": ("逆向思维", self.apply_reverse_thinking)
        }
        
        if technique is None:
            technique = random.choice(list(techniques.keys()))
        
        name, func = techniques[technique]
        result = func(topic, context, agent_role)
        
        return {
            "technique": technique,
            "technique_name": name,
            "result": result
        }


class IdeaEvolution:
    """想法进化算法：通过变异、交叉、选择来优化想法"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    def mutate_idea(self, idea: str, mutation_type: str, topic: str) -> str:
        """对想法进行变异"""
        mutations = {
            "amplify": "放大这个想法的核心优势，让它更加突出",
            "minimize": "简化这个想法，找到最小可行版本",
            "combine": "将这个想法与另一个领域的成功案例结合",
            "reverse": "反转这个想法的某个关键假设",
            "extreme": "把这个想法推向极端，看看会发生什么"
        }
        
        mutation_desc = mutations.get(mutation_type, mutations["amplify"])
        
        prompt = f"""请对以下想法进行"变异"优化。

【原始想法】{idea}
【讨论主题】{topic}
【变异方向】{mutation_desc}

请生成变异后的新想法（100字以内）："""

        return self.llm_client.get_completion(
            system_prompt="你是创意进化专家，擅长通过变异优化想法。",
            user_prompt=prompt,
            model="gemini-3-pro-preview"
        )
    
    def crossover_ideas(self, idea1: str, idea2: str, topic: str) -> str:
        """交叉两个想法，产生新想法"""
        prompt = f"""请将以下两个想法进行"交叉"，产生一个融合两者优势的新想法。

【想法A】{idea1}
【想法B】{idea2}
【讨论主题】{topic}

请生成交叉后的新想法，结合两者的精华（100字以内）："""

        return self.llm_client.get_completion(
            system_prompt="你是创意融合专家，擅长将不同想法交叉产生创新。",
            user_prompt=prompt,
            model="gemini-3-pro-preview"
        )
    
    def evaluate_fitness(self, idea: str, topic: str) -> Dict[str, Any]:
        """评估想法的适应度"""
        prompt = f"""请评估以下创新想法的质量。

【想法】{idea}
【主题】{topic}

请从以下维度评分(1-10分)并给出简短理由：
1. 创新性
2. 可行性
3. 价值潜力
4. 风险程度

请用JSON格式回答："""

        result = self.llm_client.get_completion(
            system_prompt="你是创新评估专家，客观评价想法质量。",
            user_prompt=prompt,
            model="gemini-3-pro-preview"
        )
        
        # 简单解析，返回原始文本
        return {"evaluation": result, "idea": idea}
    
    def evolve_ideas(self, ideas: List[str], topic: str, generations: int = 2) -> List[Dict]:
        """进化一组想法"""
        evolved = []
        
        for gen in range(generations):
            # 选择两个想法进行交叉
            if len(ideas) >= 2:
                pair = random.sample(ideas, 2)
                crossed = self.crossover_ideas(pair[0], pair[1], topic)
                evolved.append({
                    "type": "crossover",
                    "parents": pair,
                    "result": crossed,
                    "generation": gen + 1
                })
            
            # 随机变异一个想法
            if ideas:
                base = random.choice(ideas)
                mutation = random.choice(["amplify", "minimize", "combine", "reverse", "extreme"])
                mutated = self.mutate_idea(base, mutation, topic)
                evolved.append({
                    "type": "mutation",
                    "base": base,
                    "mutation_type": mutation,
                    "result": mutated,
                    "generation": gen + 1
                })
        
        return evolved


class ParallelDivergence:
    """平行发散模式：所有智能体同时独立产生想法"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    def generate_parallel_ideas(self, topic: str, agents: List[Any], context: str = "") -> List[Dict]:
        """所有智能体同时产生想法"""
        all_ideas = []
        
        prompt_template = """【平行发散模式】
请独立思考，不要受其他人影响，针对主题提出你的独特想法。

【主题】{topic}
【你的角色】{role}
【你的专长】{expertise}

要求：
1. 从你的专业角度出发
2. 提出1-2个独特想法
3. 每个想法简洁明了（50字以内）

请直接列出你的想法："""

        for agent in agents:
            prompt = prompt_template.format(
                topic=topic,
                role=agent.role,
                expertise=agent.expertise
            )
            
            result = self.llm_client.get_completion(
                system_prompt=agent.get_system_prompt(),
                user_prompt=prompt,
                model=agent.model_name
            )
            
            all_ideas.append({
                "agent": agent.name,
                "role": agent.role,
                "ideas": result
            })
        
        return all_ideas
    
    def deduplicate_and_cluster(self, ideas: List[Dict], topic: str) -> str:
        """去重并聚类想法"""
        ideas_text = "\n".join([f"【{i['agent']}】{i['ideas']}" for i in ideas])
        
        prompt = f"""请整理以下各专家独立提出的想法。

{ideas_text}

请：
1. 识别相似/重复的想法
2. 将想法按主题聚类
3. 提炼出最有价值的核心想法

输出整理后的想法清单："""

        return self.llm_client.get_completion(
            system_prompt="你是创意整理专家，擅长从大量想法中提炼精华。",
            user_prompt=prompt,
            model="gemini-3-pro-preview"
        )


class ChainDeepening:
    """链式深化模式：想法在智能体间传递深化"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    def deepen_chain(self, seed_idea: str, agents: List[Any], topic: str) -> List[Dict]:
        """想法在智能体间传递深化"""
        chain = []
        current_idea = seed_idea
        
        for i, agent in enumerate(agents):
            prompt = f"""【链式深化模式】
你是深化链条的第{i+1}环。请在前一个想法的基础上，从你的专业角度进行深化。

【讨论主题】{topic}
【当前想法】{current_idea}
【你的角色】{agent.role}
【你的专长】{agent.expertise}

请从你的专业角度：
1. 补充技术细节或实现方案
2. 指出潜在问题和解决思路
3. 增加你的专业视角

深化后的想法（150字以内）："""

            result = self.llm_client.get_completion(
                system_prompt=agent.get_system_prompt(),
                user_prompt=prompt,
                model=agent.model_name
            )
            
            chain.append({
                "step": i + 1,
                "agent": agent.name,
                "role": agent.role,
                "input": current_idea,
                "output": result
            })
            
            current_idea = result
        
        return chain


class DebateMode:
    """辩论模式：正反方辩论评估想法"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    def argue_for(self, idea: str, agent: Any, topic: str) -> str:
        """正方论证"""
        prompt = f"""【辩论模式 - 正方】
你需要为以下想法进行辩护，说明其价值和可行性。

【讨论主题】{topic}
【待辩护的想法】{idea}
【你的角色】{agent.role}

请从你的专业角度，列出3个支持这个想法的论点（100字以内）："""

        return self.llm_client.get_completion(
            system_prompt=f"你是辩论赛正方代表，你的角色是{agent.role}，需要有理有据地支持这个想法。",
            user_prompt=prompt,
            model=agent.model_name
        )
    
    def argue_against(self, idea: str, agent: Any, topic: str) -> str:
        """反方论证"""
        prompt = f"""【辩论模式 - 反方】
你需要对以下想法提出质疑，指出其问题和风险。

【讨论主题】{topic}
【待质疑的想法】{idea}
【你的角色】{agent.role}

请从你的专业角度，列出3个质疑这个想法的论点（100字以内）："""

        return self.llm_client.get_completion(
            system_prompt=f"你是辩论赛反方代表，你的角色是{agent.role}，需要理性地质疑和挑战这个想法。",
            user_prompt=prompt,
            model=agent.model_name
        )
    
    def run_debate(self, idea: str, pro_agents: List[Any], con_agents: List[Any], topic: str) -> Dict:
        """执行辩论"""
        pro_arguments = []
        con_arguments = []
        
        # 正方发言
        for agent in pro_agents:
            arg = self.argue_for(idea, agent, topic)
            pro_arguments.append({
                "agent": agent.name,
                "role": agent.role,
                "argument": arg
            })
        
        # 反方发言
        for agent in con_agents:
            arg = self.argue_against(idea, agent, topic)
            con_arguments.append({
                "agent": agent.name,
                "role": agent.role,
                "argument": arg
            })
        
        # 综合辩论结果
        synthesis = self.synthesize_debate(idea, pro_arguments, con_arguments, topic)
        
        return {
            "idea": idea,
            "pro_arguments": pro_arguments,
            "con_arguments": con_arguments,
            "synthesis": synthesis
        }
    
    def synthesize_debate(self, idea: str, pro: List[Dict], con: List[Dict], topic: str) -> str:
        """综合辩论结论"""
        pro_text = "\n".join([f"【{p['agent']}】{p['argument']}" for p in pro])
        con_text = "\n".join([f"【{c['agent']}】{c['argument']}" for c in con])
        
        prompt = f"""请综合以下辩论，得出客观结论。

【主题】{topic}
【讨论的想法】{idea}

【正方观点】
{pro_text}

【反方观点】
{con_text}

请综合双方观点：
1. 这个想法的核心价值是什么？
2. 主要风险和挑战是什么？
3. 如何改进这个想法？
4. 最终建议（推荐/谨慎推进/暂缓）

请给出综合结论（200字以内）："""

        return self.llm_client.get_completion(
            system_prompt="你是公正的辩论裁判，需要客观综合双方观点得出结论。",
            user_prompt=prompt,
            model="gemini-3-pro-preview"
        )
