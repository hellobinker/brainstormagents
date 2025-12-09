"""
跨领域知识连接模块
自动关联不同领域的知识产生跨界创新
"""
from typing import List, Dict, Any, Optional
import random

class CrossDomainConnector:
    """跨领域知识连接器 - 寻找不同领域间的创新联系"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        
        # 预定义领域库（用于启发）
        self.domains = {
            "nature": {
                "name": "自然界/仿生学",
                "concepts": ["光合作用", "蜂巢结构", "进化适应", "共生关系", "伪装机制", "自愈能力"]
            },
            "art": {
                "name": "艺术与设计",
                "concepts": ["极简主义", "留白", "黄金分割", "对比", "节奏感", "解构主义"]
            },
            "history": {
                "name": "历史与文明",
                "concepts": ["丝绸之路", "文艺复兴", "工业革命", "游牧文化", "封建等级", "神话传说"]
            },
            "physics": {
                "name": "物理学",
                "concepts": ["量子纠缠", "相对论", "熵增", "杠杆原理", "共振", "相变"]
            },
            "business": {
                "name": "商业模式",
                "concepts": ["订阅制", "共享经济", "长尾效应", "网络效应", "免费增值", "众筹"]
            },
            "psychology": {
                "name": "心理学",
                "concepts": ["马斯洛需求", "心流", "认知偏差", "从众效应", "锚定效应", "条件反射"]
            },
            "gaming": {
                "name": "游戏机制",
                "concepts": ["即时反馈", "升级系统", "成就感", "随机掉落", "排行榜", "新手引导"]
            },
            "biology": {
                "name": "生物学",
                "concepts": ["进化", "共生", "新陈代谢", "神经网络", "免疫系统", "基因表达"]
            },
            "architecture": {
                "name": "建筑学",
                "concepts": ["包豪斯", "哥特式", "可持续设计", "模块化", "空间流动", "光影运用"]
            },
            "music": {
                "name": "音乐",
                "concepts": ["和声", "节奏", "不协和音", "变奏", "即兴", "复调"]
            }
        }
    
    def get_random_domain_concept(self) -> Dict[str, str]:
        """随机获取一个领域概念"""
        domain_key = random.choice(list(self.domains.keys()))
        domain = self.domains[domain_key]
        concept = random.choice(domain["concepts"])
        return {
            "domain": domain["name"],
            "concept": concept,
            "key": domain_key
        }
    
    def get_cross_domain_insight(self, topic: str) -> str:
        """获取跨领域洞察（简单版本，向后兼容）"""
        seed = self.get_random_domain_concept()
        return f"Consider the concept of '{seed['concept']}' from {seed['domain']}. How might that apply to {topic}?"
    
    def generate_cross_domain_insight(self, topic: str, context: str = "") -> Dict[str, str]:
        """生成跨领域创新洞察（LLM增强版）"""
        seed = self.get_random_domain_concept()
        
        prompt = f"""请进行"跨界创新"思考。
        
【当前主题】{topic}
【跨界领域】{seed['domain']}
【借用概念】{seed['concept']}

请思考：如何将"{seed['concept']}"的原理或特征，应用到"{topic}"中？
请提出一个具体的创新点（100字以内）。

格式要求：
1. 核心原理：简述该概念的核心机制
2. 跨界应用：具体的应用方案"""

        if self.llm_client:
            try:
                insight = self.llm_client.get_completion(
                    system_prompt="你是跨界创新专家，擅长将不同领域的知识进行连接和迁移。",
                    user_prompt=prompt,
                    model="gpt-5.1"
                )
            except Exception:
                insight = f"由于未连接LLM，无法生成深度洞察。请思考如何将{seed['domain']}中的{seed['concept']}应用到{topic}中。"
        else:
            insight = f"由于未连接LLM，无法生成深度洞察。请思考如何将{seed['domain']}中的{seed['concept']}应用到{topic}中。"
            
        return {
            "domain": seed['domain'],
            "concept": seed['concept'],
            "insight": insight
        }
    
    def find_connection(self, topic: str, domain_hint: str = None) -> str:
        """寻找特定领域的连接"""
        if domain_hint and domain_hint in self.domains:
            domain = self.domains[domain_hint]
            concept = random.choice(domain["concepts"])
            seed = {"domain": domain["name"], "concept": concept}
        else:
            seed = self.get_random_domain_concept()
            
        prompt = f"""请寻找以下两者之间的创新联系：

1. 主题：{topic}
2. 领域：{seed['domain']} (概念：{seed['concept']})

请用一句话描述这种可能的联系（50字以内）。"""

        if self.llm_client:
            try:
                return self.llm_client.get_completion(
                    system_prompt="你是联想思维专家。",
                    user_prompt=prompt,
                    model="gpt-5.1"
                )
            except Exception:
                return f"尝试将{seed['concept']}应用到{topic}中..."
        return f"尝试将{seed['concept']}应用到{topic}中..."
    
    def get_multiple_insights(self, topic: str, count: int = 3) -> List[Dict[str, str]]:
        """获取多个跨领域洞察"""
        insights = []
        used_domains = set()
        
        for _ in range(count):
            # 尝试获取不同领域的洞察
            for attempt in range(10):
                seed = self.get_random_domain_concept()
                if seed['key'] not in used_domains:
                    used_domains.add(seed['key'])
                    insight = self.generate_cross_domain_insight(topic)
                    insights.append(insight)
                    break
        
        return insights
