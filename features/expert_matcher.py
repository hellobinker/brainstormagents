"""
专家匹配器

根据问题意图，从专家目录中选择最合适的专家。
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# 导入专家目录
try:
    from brainstorm_adk.shared.expert_catalog import EXPERT_CATALOG, ExpertPreset
except ImportError:
    # 如果 ADK 模块不可用，定义本地版本
    @dataclass
    class ExpertPreset:
        name: str
        role: str
        expertise: str
        style: str
        personality_traits: List[str]
    
    EXPERT_CATALOG = []


# 领域到专家的映射
DOMAIN_TO_EXPERT_INDEX = {
    "产品规划": [0, 3],           # 产品经理, 产品企划专家
    "电控软件": [1],               # 电控软件专家
    "嵌入式": [2],                 # 嵌入式软件专家
    "IoT": [4],                    # IoT专家
    "TRIZ创新": [5],               # TRIZ创新专家
    "热技术": [6],                 # 热技术专家
    "流体": [7],                   # 流体技术专家
    "空气动力学": [8],             # 空气动力学专家
    "结构": [9],                   # 结构专家
    "燃烧": [10],                  # 燃烧专家
    "硬件": [11],                  # 硬件工程师
    "自媒体": [12],                # 自媒体运营专家
    "声学": [13],                  # 声学技术专家
    "电磁": [14],                  # 电磁技术专家
    "电机": [15],                  # 电机技术专家
    "变频": [16],                  # 变频技术专家
    "制冷": [17],                  # 制冷技术专家
    "控制算法": [18],              # 控制算法专家
    "智能技术": [19],              # 智能技术专家
    "传感器": [20],                # 传感器技术专家
    "材料": [21],                  # 材料学专家
    "电化学": [22],                # 电化学专家
    "净水": [23],                  # 净水技术专家
    "营销": [24],                  # 营销专家
    "健康营养": [25],              # 健康营养专家
    "医疗": [26],                  # 医疗领域技术专家
    "雷达": [27],                  # 雷达技术专家
    "自动控制": [28],              # 自动控制技术专家
    "机器学习": [29],              # 机器学习专家
    "AI技术": [30],                # AI技术专家
}


@dataclass
class MatchedExpert:
    """匹配的专家"""
    index: int
    name: str
    role: str
    expertise: str
    matched_domain: str
    relevance_score: float
    assigned_sub_problem: str = ""


class ExpertMatcher:
    """
    专家匹配器
    
    根据问题涉及的领域，选择最合适的专家。
    
    使用示例:
        matcher = ExpertMatcher()
        experts = matcher.match_by_domains(["热技术", "声学"], limit=3)
    """
    
    def __init__(self, expert_catalog: List = None):
        self.experts = expert_catalog or EXPERT_CATALOG
    
    def match_by_domains(
        self, 
        domains: List[str], 
        limit: int = 5,
        exclude_indices: List[int] = None
    ) -> List[MatchedExpert]:
        """
        根据领域匹配专家
        
        Args:
            domains: 领域列表
            limit: 最多返回的专家数
            exclude_indices: 排除的专家索引
        
        Returns:
            匹配的专家列表，按相关性排序
        """
        exclude = set(exclude_indices or [])
        matched = []
        
        for domain in domains:
            if domain in DOMAIN_TO_EXPERT_INDEX:
                for idx in DOMAIN_TO_EXPERT_INDEX[domain]:
                    if idx in exclude or idx >= len(self.experts):
                        continue
                    
                    expert = self.experts[idx]
                    
                    # 检查是否已添加
                    if any(m.index == idx for m in matched):
                        continue
                    
                    matched.append(MatchedExpert(
                        index=idx,
                        name=expert.name,
                        role=expert.role,
                        expertise=expert.expertise,
                        matched_domain=domain,
                        relevance_score=1.0
                    ))
        
        # 如果匹配不够，添加通用专家
        if len(matched) < limit:
            # 添加产品经理（通用视角）
            if 0 not in exclude and not any(m.index == 0 for m in matched):
                expert = self.experts[0]
                matched.append(MatchedExpert(
                    index=0,
                    name=expert.name,
                    role=expert.role,
                    expertise=expert.expertise,
                    matched_domain="通用",
                    relevance_score=0.5
                ))
            
            # 添加 TRIZ 创新专家
            if 5 not in exclude and not any(m.index == 5 for m in matched):
                expert = self.experts[5]
                matched.append(MatchedExpert(
                    index=5,
                    name=expert.name,
                    role=expert.role,
                    expertise=expert.expertise,
                    matched_domain="创新方法",
                    relevance_score=0.5
                ))
        
        # 按相关性排序，取前 limit 个
        matched.sort(key=lambda x: x.relevance_score, reverse=True)
        return matched[:limit]
    
    def match_with_sub_problems(
        self, 
        domains: List[str],
        sub_problems: List[str],
        limit: int = 5
    ) -> List[MatchedExpert]:
        """
        匹配专家并分配子问题
        
        尝试将子问题分配给最相关的专家
        """
        experts = self.match_by_domains(domains, limit=limit)
        
        if not experts or not sub_problems:
            return experts
        
        # 简单分配策略：轮询
        for i, sub_problem in enumerate(sub_problems):
            if i < len(experts):
                experts[i].assigned_sub_problem = sub_problem
            else:
                # 超出专家数量，分配给最相关的
                experts[i % len(experts)].assigned_sub_problem += f"\n{sub_problem}"
        
        return experts
    
    def get_expert_by_index(self, index: int) -> Optional[ExpertPreset]:
        """根据索引获取专家"""
        if 0 <= index < len(self.experts):
            return self.experts[index]
        return None
    
    def get_all_domains(self) -> List[str]:
        """获取所有可用领域"""
        return list(DOMAIN_TO_EXPERT_INDEX.keys())
    
    def search_expert(self, query: str) -> List[MatchedExpert]:
        """
        搜索专家（按名称或专业）
        """
        query_lower = query.lower()
        matched = []
        
        for i, expert in enumerate(self.experts):
            score = 0
            if query in expert.name:
                score = 1.0
            elif query_lower in expert.expertise.lower():
                score = 0.8
            elif query_lower in expert.role.lower():
                score = 0.6
            
            if score > 0:
                matched.append(MatchedExpert(
                    index=i,
                    name=expert.name,
                    role=expert.role,
                    expertise=expert.expertise,
                    matched_domain="搜索",
                    relevance_score=score
                ))
        
        matched.sort(key=lambda x: x.relevance_score, reverse=True)
        return matched


# 便捷函数
_default_matcher: Optional[ExpertMatcher] = None

def get_matcher() -> ExpertMatcher:
    global _default_matcher
    if _default_matcher is None:
        _default_matcher = ExpertMatcher()
    return _default_matcher


def match_experts(domains: List[str], limit: int = 5) -> List[MatchedExpert]:
    """快速匹配专家"""
    return get_matcher().match_by_domains(domains, limit)
