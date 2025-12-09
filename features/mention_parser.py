"""
@提及功能模块
解析消息中的@提及并触发目标智能体响应
"""
from typing import List, Dict, Optional, Tuple
import re

class MentionParser:
    """@提及解析器 - 解析和处理消息中的@提及"""
    
    def __init__(self):
        # @提及的正则表达式模式
        self.mention_pattern = re.compile(r'@(\w+)', re.UNICODE)
        # 特殊提及
        self.special_mentions = {
            "all": "所有智能体",
            "主持人": "主持人",
            "facilitator": "主持人"
        }
    
    def parse_mentions(self, content: str) -> List[str]:
        """解析消息中的所有@提及"""
        mentions = self.mention_pattern.findall(content)
        return mentions
    
    def has_mention(self, content: str) -> bool:
        """检查消息是否包含@提及"""
        return bool(self.mention_pattern.search(content))
    
    def get_mentioned_agents(self, content: str, available_agents: List[str]) -> Tuple[List[str], bool]:
        """
        获取被提及的智能体列表
        返回: (被提及的智能体名称列表, 是否是@all)
        """
        mentions = self.parse_mentions(content)
        mentioned_agents = []
        is_mention_all = False
        
        for mention in mentions:
            # 检查特殊提及
            if mention.lower() in ["all", "所有", "全体"]:
                is_mention_all = True
                mentioned_agents = available_agents.copy()
                break
            
            # 模糊匹配智能体名称
            for agent_name in available_agents:
                if mention.lower() in agent_name.lower() or agent_name.lower() in mention.lower():
                    if agent_name not in mentioned_agents:
                        mentioned_agents.append(agent_name)
                    break
        
        return mentioned_agents, is_mention_all
    
    def remove_mentions(self, content: str) -> str:
        """从消息中移除@提及，返回纯净内容"""
        return self.mention_pattern.sub('', content).strip()
    
    def format_mention(self, agent_name: str) -> str:
        """格式化@提及"""
        return f"@{agent_name}"
    
    def create_mention_prompt(self, 
                              sender: str, 
                              content: str, 
                              mentioned_agent: str,
                              context: str = "") -> str:
        """为被@的智能体创建响应提示"""
        clean_content = self.remove_mentions(content)
        
        prompt = f"""你被 {sender} 点名提问或评论了！

【原始消息】
{sender}: {content}

【提问/评论内容】
{clean_content}

【讨论上下文】
{context}

请直接回应 {sender} 的问题或评论。你的回复应该：
1. 直接针对他/她的观点进行回应
2. 可以表达同意、反对或提出新的思考角度
3. 保持你的角色特色和专业视角
4. 控制在200字以内

请开始你的回应："""
        
        return prompt
    
    def detect_conversation_thread(self, content: str, history: List[Dict]) -> Optional[Dict]:
        """检测是否是对话线程的延续"""
        mentions = self.parse_mentions(content)
        
        if not mentions:
            return None
        
        # 查找最近被提及者的发言
        for msg in reversed(history[-20:]):
            if msg.get("sender") in mentions:
                return {
                    "reply_to": msg.get("sender"),
                    "original_content": msg.get("content"),
                    "thread_detected": True
                }
        
        return None


# 全局解析器实例
mention_parser = MentionParser()
