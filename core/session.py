from typing import List, Dict
from core.agent import Agent
from core.protocol import Message
from utils.llm_client import LLMClient

class BrainstormingSession:
    def __init__(self, topic: str, agents: List[Agent], llm_client: LLMClient):
        self.topic = topic
        self.agents = agents
        self.llm_client = llm_client
        self.history: List[Message] = []
        self.rounds = 0
        self.summary = None
        
    def add_message(self, message: Message):
        self.history.append(message)
        for agent in self.agents:
            agent.update_history(message)
            
    def run_round(self):
        self.rounds += 1
        print(f"\n--- Round {self.rounds} ---")
        for agent in self.agents:
            # Construct context from history
            history_text = "\n".join([f"{m.sender}: {m.content}" for m in self.history[-20:]])  # Last 20 messages
            
            # Topic-focused prompt with role reminder
            user_prompt = (
                f"【讨论主题】{self.topic}\n\n"
                f"【重要提醒】请始终围绕主题 '{self.topic}' 进行讨论，结合你的专业背景提出观点。\n\n"
                f"【讨论历史】\n{history_text}\n\n"
                f"【你的任务】\n"
                f"1. 基于你的角色({agent.role})和专长({agent.expertise})，针对主题提出你的观点\n"
                f"2. 可以回应或补充其他成员的观点\n"
                f"3. 发言内容请控制在200字以内，直接给出观点\n"
                f"\n请开始你的发言："
            )
            
            response_text = self.llm_client.get_completion(
                system_prompt=agent.get_system_prompt(),
                user_prompt=user_prompt,
                model=agent.model_name
            )
            
            message = Message(sender=agent.name, content=response_text, metadata={"round": self.rounds, "role": agent.role})
            self.add_message(message)
            print(f"[{agent.name}]: {response_text[:100]}...")
    
    def generate_summary(self) -> str:
        """Generate a comprehensive summary of the brainstorming session."""
        # Collect all viewpoints by agent
        agent_contributions = {}
        for msg in self.history:
            if msg.sender != "System":
                if msg.sender not in agent_contributions:
                    agent_contributions[msg.sender] = []
                agent_contributions[msg.sender].append(msg.content)
        
        # Format contributions for summary
        contributions_text = ""
        for agent_name, contents in agent_contributions.items():
            contributions_text += f"\n【{agent_name}的观点】\n"
            for i, content in enumerate(contents, 1):
                contributions_text += f"第{i}轮: {content}\n"
        
        summary_prompt = (
            f"你是一个专业的头脑风暴总结专家。请根据以下多位专家的讨论，生成一份创新方案总结。\n\n"
            f"【讨论主题】{self.topic}\n\n"
            f"【参与专家】{', '.join([a.name + '(' + a.role + ')' for a in self.agents])}\n\n"
            f"【各专家观点汇总】{contributions_text}\n\n"
            f"【总结要求】\n"
            f"请生成一份结构化的创新方案总结，包括：\n"
            f"1. 🎯 核心创新点（3-5个关键创新方向）\n"
            f"2. 💡 具体方案建议（整合各专家观点）\n"
            f"3. ⚠️ 需要关注的风险或挑战\n"
            f"4. 📋 下一步行动建议\n"
            f"\n请用中文生成总结："
        )
        
        system_prompt = "你是专业的头脑风暴总结专家，擅长整合多方观点形成可执行的创新方案。"
        
        self.summary = self.llm_client.get_completion(
            system_prompt=system_prompt,
            user_prompt=summary_prompt,
            model="gpt-5.1"  # Use a powerful model for summary
        )
        
        return self.summary
            
    def get_summary(self):
        if self.summary:
            return self.summary
        return f"Session on '{self.topic}' completed with {len(self.history)} messages. Call generate_summary() to get AI summary."

