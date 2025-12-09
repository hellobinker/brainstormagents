"""
数据统计与分析模块
提供会话的详细统计和分析功能
"""
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict
from datetime import datetime
import json

class SessionStatistics:
    """会话统计分析器 - 提供详细的数据统计和分析"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """重置统计数据"""
        self.message_count = 0
        self.agent_stats: Dict[str, Dict] = {}
        self.phase_stats: Dict[str, Dict] = {}
        self.emotion_history: List[Dict] = []
        self.keyword_frequency: Counter = Counter()
        self.interaction_matrix: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.timeline: List[Dict] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    def start_session(self):
        """标记会话开始"""
        self.start_time = datetime.now()
    
    def end_session(self):
        """标记会话结束"""
        self.end_time = datetime.now()
    
    def record_message(self, sender: str, content: str, metadata: Dict = None):
        """记录一条消息"""
        metadata = metadata or {}
        self.message_count += 1
        
        # 更新智能体统计
        if sender not in self.agent_stats:
            self.agent_stats[sender] = {
                "message_count": 0,
                "total_words": 0,
                "avg_length": 0,
                "emotions": [],
                "phases": [],
                "mentions_made": 0,
                "mentions_received": 0
            }
        
        stats = self.agent_stats[sender]
        stats["message_count"] += 1
        word_count = len(content)
        stats["total_words"] += word_count
        stats["avg_length"] = stats["total_words"] / stats["message_count"]
        
        # 记录情感
        if "emotion" in metadata:
            stats["emotions"].append(metadata["emotion"])
        
        # 记录阶段
        if "phase" in metadata:
            phase = metadata["phase"]
            stats["phases"].append(phase)
            
            if phase not in self.phase_stats:
                self.phase_stats[phase] = {
                    "message_count": 0,
                    "participants": set(),
                    "avg_length": 0,
                    "total_words": 0
                }
            
            self.phase_stats[phase]["message_count"] += 1
            self.phase_stats[phase]["participants"].add(sender)
            self.phase_stats[phase]["total_words"] += word_count
            self.phase_stats[phase]["avg_length"] = (
                self.phase_stats[phase]["total_words"] / 
                self.phase_stats[phase]["message_count"]
            )
        
        # 提取关键词
        self._extract_keywords(content)
        
        # 记录时间线
        self.timeline.append({
            "timestamp": datetime.now().isoformat(),
            "sender": sender,
            "length": word_count,
            "phase": metadata.get("phase", "unknown")
        })
    
    def record_mention(self, sender: str, mentioned: str):
        """记录@提及"""
        if sender in self.agent_stats:
            self.agent_stats[sender]["mentions_made"] += 1
        if mentioned in self.agent_stats:
            self.agent_stats[mentioned]["mentions_received"] += 1
        
        # 更新交互矩阵
        self.interaction_matrix[sender][mentioned] += 1
    
    def record_emotion(self, agent: str, emotion: str):
        """记录情感状态变化"""
        self.emotion_history.append({
            "timestamp": datetime.now().isoformat(),
            "agent": agent,
            "emotion": emotion
        })
    
    def _extract_keywords(self, content: str):
        """提取关键词"""
        keywords = [
            "创新", "AI", "智能", "技术", "方案", "问题", "解决",
            "用户", "体验", "数据", "安全", "效率", "成本", "优化",
            "设计", "产品", "功能", "需求", "市场", "竞争", "价值"
        ]
        for kw in keywords:
            if kw in content:
                self.keyword_frequency[kw] += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """获取统计摘要"""
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
        
        # 计算参与度
        total_messages = self.message_count
        participation = {}
        for agent, stats in self.agent_stats.items():
            participation[agent] = round(
                stats["message_count"] / total_messages * 100, 1
            ) if total_messages > 0 else 0
        
        # 情感分布
        emotion_dist = Counter()
        for agent, stats in self.agent_stats.items():
            for emotion in stats.get("emotions", []):
                emotion_dist[emotion] += 1
        
        return {
            "overview": {
                "total_messages": self.message_count,
                "total_agents": len(self.agent_stats),
                "duration_seconds": duration,
                "phases_completed": len(self.phase_stats)
            },
            "participation": participation,
            "emotion_distribution": dict(emotion_dist),
            "top_keywords": dict(self.keyword_frequency.most_common(10)),
            "agent_details": {
                agent: {
                    "messages": stats["message_count"],
                    "avg_length": round(stats["avg_length"], 1),
                    "mentions_made": stats["mentions_made"],
                    "mentions_received": stats["mentions_received"]
                }
                for agent, stats in self.agent_stats.items()
            }
        }
    
    def get_interaction_network(self) -> Dict[str, Any]:
        """获取交互网络数据（用于可视化）"""
        nodes = []
        links = []
        
        for agent in self.agent_stats:
            stats = self.agent_stats[agent]
            nodes.append({
                "id": agent,
                "size": stats["message_count"],
                "type": "agent"
            })
        
        for source, targets in self.interaction_matrix.items():
            for target, weight in targets.items():
                if weight > 0:
                    links.append({
                        "source": source,
                        "target": target,
                        "weight": weight
                    })
        
        return {"nodes": nodes, "links": links}
    
    def get_timeline_data(self) -> List[Dict]:
        """获取时间线数据（用于图表）"""
        return self.timeline
    
    def get_phase_breakdown(self) -> Dict[str, Any]:
        """获取阶段分析"""
        result = {}
        for phase, stats in self.phase_stats.items():
            result[phase] = {
                "message_count": stats["message_count"],
                "participant_count": len(stats["participants"]),
                "participants": list(stats["participants"]),
                "avg_message_length": round(stats["avg_length"], 1)
            }
        return result
    
    def export_json(self) -> str:
        """导出JSON格式报告"""
        return json.dumps({
            "summary": self.get_summary(),
            "phases": self.get_phase_breakdown(),
            "interaction_network": self.get_interaction_network(),
            "timeline": self.timeline[-100:]  # 最近100条
        }, ensure_ascii=False, indent=2)
    
    def export_csv_data(self) -> Dict[str, List[Dict]]:
        """导出CSV格式数据"""
        return {
            "agents": [
                {
                    "name": agent,
                    "message_count": stats["message_count"],
                    "avg_length": round(stats["avg_length"], 1),
                    "mentions_made": stats["mentions_made"],
                    "mentions_received": stats["mentions_received"]
                }
                for agent, stats in self.agent_stats.items()
            ],
            "keywords": [
                {"keyword": kw, "count": count}
                for kw, count in self.keyword_frequency.most_common(20)
            ]
        }


# 全局统计实例
session_stats = SessionStatistics()
