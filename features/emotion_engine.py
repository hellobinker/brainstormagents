"""
情感智能引擎
智能体能识别和利用情感因素激发创造力
"""
from typing import List, Dict, Optional
import random
from core.agent import Agent
from core.protocol import Message

class EmotionalIntelligenceEngine:
    """情感智能引擎 - 识别和利用情感因素激发创造力"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        
        # 情感状态定义
        self.emotional_states = {
            "inspired": {
                "name": "灵感迸发",
                "emoji": "✨",
                "energy": 0.9,
                "creativity_boost": 1.3,
                "prompt": "你感到灵感迸发，思维特别活跃，请大胆表达你的创意想法！"
            },
            "curious": {
                "name": "好奇探索",
                "emoji": "🔮",
                "energy": 0.8,
                "creativity_boost": 1.2,
                "prompt": "你充满好奇心，想要深入探索这个话题的各个方面。"
            },
            "excited": {
                "name": "兴奋激动",
                "emoji": "🎉",
                "energy": 0.85,
                "creativity_boost": 1.25,
                "prompt": "你对这个讨论感到兴奋，充满热情地参与！"
            },
            "focused": {
                "name": "专注投入",
                "emoji": "🎯",
                "energy": 0.7,
                "creativity_boost": 1.1,
                "prompt": "你非常专注，深入思考每一个细节。"
            },
            "skeptical": {
                "name": "理性质疑",
                "emoji": "🤔",
                "energy": 0.6,
                "creativity_boost": 0.9,
                "prompt": "你保持理性质疑的态度，仔细审视每个观点。"
            },
            "contemplative": {
                "name": "沉思默想",
                "emoji": "🧘",
                "energy": 0.5,
                "creativity_boost": 1.0,
                "prompt": "你在深入沉思，试图从更高的层面理解问题。"
            },
            "collaborative": {
                "name": "协作共创",
                "emoji": "🤝",
                "energy": 0.75,
                "creativity_boost": 1.15,
                "prompt": "你渴望与他人协作，在交流中碰撞出新的火花。"
            },
            "neutral": {
                "name": "平和客观",
                "emoji": "😊",
                "energy": 0.6,
                "creativity_boost": 1.0,
                "prompt": "保持平和客观的态度参与讨论。"
            }
        }
        
        # 情感触发词
        self.emotion_triggers = {
            "inspired": ["突破", "创新", "wow", "太棒了", "灵感", "妙"],
            "curious": ["为什么", "如何", "怎样", "可能", "假如", "?"],
            "excited": ["太好了", "完美", "绝妙", "amazing", "厉害"],
            "skeptical": ["但是", "问题", "风险", "不确定", "挑战"],
            "contemplative": ["思考", "深层", "本质", "根本", "哲学"],
            "collaborative": ["一起", "共同", "我们", "合作", "结合"]
        }
    
    def analyze_message_emotion(self, content: str) -> Dict:
        """分析消息中的情感倾向"""
        emotion_scores = {}
        
        for emotion, triggers in self.emotion_triggers.items():
            score = sum(1 for trigger in triggers if trigger in content)
            if score > 0:
                emotion_scores[emotion] = score
        
        # 找出主导情感
        if emotion_scores:
            dominant = max(emotion_scores, key=emotion_scores.get)
            return {
                "dominant_emotion": dominant,
                "scores": emotion_scores,
                "intensity": min(emotion_scores[dominant] / 3, 1.0)
            }
        
        return {"dominant_emotion": "neutral", "scores": {}, "intensity": 0.5}
    
    def update_emotions(self, agents: List[Agent], history: List[Message]):
        """根据讨论历史更新智能体情感状态"""
        if not history:
            return
        
        recent_msgs = history[-5:]
        
        # 分析讨论氛围
        emotion_counts = {}
        for msg in recent_msgs:
            analysis = self.analyze_message_emotion(msg.content)
            dominant = analysis["dominant_emotion"]
            emotion_counts[dominant] = emotion_counts.get(dominant, 0) + 1
        
        # 确定群体情感倾向
        if emotion_counts:
            group_emotion = max(emotion_counts, key=emotion_counts.get)
        else:
            group_emotion = "neutral"
        
        # 更新每个智能体的情感
        for agent in agents:
            # 30%概率受群体情感影响
            if random.random() < 0.3:
                agent.current_emotion = group_emotion
            # 20%概率产生互补情感（增加多样性）
            elif random.random() < 0.2:
                complementary = self._get_complementary_emotion(group_emotion)
                agent.current_emotion = complementary
            # 否则小概率随机变化
            elif random.random() < 0.1:
                agent.current_emotion = random.choice(list(self.emotional_states.keys()))
    
    def _get_complementary_emotion(self, emotion: str) -> str:
        """获取互补情感（增加讨论多样性）"""
        complements = {
            "inspired": "skeptical",
            "excited": "contemplative",
            "curious": "focused",
            "skeptical": "inspired",
            "contemplative": "excited",
            "collaborative": "focused",
            "focused": "curious"
        }
        return complements.get(emotion, "neutral")
    
    def get_emotional_prompt_modifier(self, agent: Agent) -> str:
        """获取情感状态对应的提示词修饰"""
        emotion = getattr(agent, 'current_emotion', 'neutral')
        if emotion in self.emotional_states:
            state = self.emotional_states[emotion]
            return f"[情感状态: {state['emoji']} {state['name']}] {state['prompt']}"
        return ""
    
    def get_creativity_multiplier(self, agent: Agent) -> float:
        """获取创造力加成系数"""
        emotion = getattr(agent, 'current_emotion', 'neutral')
        if emotion in self.emotional_states:
            return self.emotional_states[emotion]["creativity_boost"]
        return 1.0
    
    def inject_emotional_stimulus(self, topic: str, current_emotion: str) -> str:
        """注入情感刺激来激发创造力"""
        stimuli = {
            "inspired": f"想象一下，如果{topic}能够彻底改变人们的生活方式，那会是什么样子？",
            "curious": f"关于{topic}，有什么是我们还没有探索过的角落？",
            "excited": f"{topic}最令人兴奋的可能性是什么？",
            "skeptical": f"让我们暂停一下，{topic}真正的核心挑战是什么？",
            "contemplative": f"从更宏观的视角来看，{topic}的本质意义是什么？",
            "collaborative": f"我们如何将各自对{topic}的理解融合成一个更强大的方案？"
        }
        return stimuli.get(current_emotion, f"继续探索{topic}的更多可能性。")
    
    def generate_emotion_report(self, agents: List[Agent]) -> Dict:
        """生成情感状态报告"""
        emotion_distribution = {}
        for agent in agents:
            emotion = getattr(agent, 'current_emotion', 'neutral')
            emotion_distribution[emotion] = emotion_distribution.get(emotion, 0) + 1
        
        # 计算群体能量水平
        total_energy = 0
        for agent in agents:
            emotion = getattr(agent, 'current_emotion', 'neutral')
            if emotion in self.emotional_states:
                total_energy += self.emotional_states[emotion]["energy"]
        
        avg_energy = total_energy / len(agents) if agents else 0.5
        
        return {
            "distribution": emotion_distribution,
            "average_energy": avg_energy,
            "energy_level": "高" if avg_energy > 0.7 else "中" if avg_energy > 0.5 else "低"
        }
