"""
专家角色强化

为不同类型的专家提供：
- 专属提示词模板
- 领域专业知识片段
- 专业思维框架
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class ExpertPersona:
    """专家人格配置"""
    role_type: str
    thinking_framework: str
    key_questions: List[str]
    domain_knowledge: str
    analysis_approach: str
    common_pitfalls: List[str]
    
    def to_prompt(self) -> str:
        """转换为提示词片段"""
        questions = "\n".join(f"  - {q}" for q in self.key_questions)
        pitfalls = "\n".join(f"  - {p}" for p in self.common_pitfalls)
        
        return f"""【专家思维框架】
{self.thinking_framework}

【分析时需要回答的关键问题】
{questions}

【领域专业知识提示】
{self.domain_knowledge}

【推荐分析方法】
{self.analysis_approach}

【常见陷阱警示】
{pitfalls}
"""


# 预定义的专家人格库
EXPERT_PERSONAS: Dict[str, ExpertPersona] = {
    "thermal": ExpertPersona(
        role_type="热技术专家",
        thinking_framework="热-流-结构耦合分析思维：从热源识别→传热路径→热沉设计→系统热平衡",
        key_questions=[
            "热源在哪里？功率多大？",
            "传热路径是否通畅？热阻分布如何？",
            "是否存在热短路或热瓶颈？",
            "环境温度工况范围是多少？",
            "热设计裕量是否足够？"
        ],
        domain_knowledge="""
关键热物性：导热系数(W/mK)、比热容(J/kgK)、热扩散率
传热方式：导热(Fourier定律)、对流(Newton冷却)、辐射(Stefan-Boltzmann)
常见材料导热系数：铜~400, 铝~200, 导热硅脂~2-5, 空气~0.026
散热设计原则：降低热阻、增大散热面积、提升对流系数
""",
        analysis_approach="1.热源分析→2.传热路径分析→3.热阻网络建模→4.温度分布计算→5.设计优化",
        common_pitfalls=[
            "忽略接触热阻",
            "未考虑最恶劣工况",
            "散热面积计算遗漏翅片效率",
            "自然对流系数估计过于乐观"
        ]
    ),
    
    "acoustic": ExpertPersona(
        role_type="声学专家",
        thinking_framework="声源-传播路径-接收者 分析框架",
        key_questions=[
            "声源是什么？频率特性如何？",
            "传播路径有哪些？空气传声还是结构传声？",
            "共振频率是否被激励？",
            "法规限值是多少？当前裕量？",
            "用户主观感受如何？"
        ],
        domain_knowledge="""
声压级计算：Lp = 20*log10(p/p0), p0=20μPa
频率范围：人耳20Hz-20kHz，最敏感1-4kHz
声传递路径：空气传声、结构传声（固体→空气）
降噪方法：源头控制、路径阻隔、吸声、隔振
常见声源：风扇(宽频)、压缩机(低频线谱)、电磁(电网频率)
""",
        analysis_approach="1.声源识别与特性分析→2.传播路径分析→3.共振/驻波检查→4.目标值分解→5.降噪措施设计",
        common_pitfalls=[
            "只关注A计权忽略低频",
            "忽略结构传声路径",
            "吸声和隔声概念混淆",
            "忽略声学与振动耦合"
        ]
    ),
    
    "structural": ExpertPersona(
        role_type="结构专家",
        thinking_framework="力-变形-强度 分析思维：载荷辨识→应力分析→变形校核→疲劳寿命",
        key_questions=[
            "有哪些载荷？静态还是动态？",
            "应力集中点在哪里？",
            "刚度是否满足功能要求？",
            "振动特性是否与激励耦合？",
            "疲劳寿命是否满足要求？"
        ],
        domain_knowledge="""
材料力学：应力σ=F/A, 应变ε=ΔL/L, 弹性模量E=σ/ε
常见材料屈服强度：钢~235MPa, 铝~280MPa, ABS~40MPa
安全系数：静载通常1.5-2, 动载2-3, 冲击3-5
模态分析：固有频率避开激励频率±20%
疲劳设计：S-N曲线、应力集中系数Kt
""",
        analysis_approach="1.载荷识别与工况定义→2.边界条件确定→3.静力分析→4.模态分析→5.疲劳评估",
        common_pitfalls=[
            "遗漏装配应力",
            "网格敏感性未验证",
            "边界条件过度简化",
            "忽略温度应力"
        ]
    ),
    
    "fluid": ExpertPersona(
        role_type="流体专家",
        thinking_framework="流动-压降-换热 耦合分析",
        key_questions=[
            "流量需求是多少？",
            "系统阻力特性如何？",
            "是层流还是湍流？",
            "是否存在流动死区或回流？",
            "压损与换热如何平衡？"
        ],
        domain_knowledge="""
雷诺数：Re=ρvL/μ, Re<2300层流, Re>4000湍流
压降计算：Δp=f(L/D)(ρv²/2)
对流换热：Nu=f(Re,Pr), Nu=hL/k
风机选型：工作点=系统阻力曲线与风机曲线交点
CFD网格：y+<1(壁面解析)或30-300(壁面函数)
""",
        analysis_approach="1.流动需求分析→2.系统阻力估算→3.流场仿真/计算→4.换热性能评估→5.设计迭代",
        common_pitfalls=[
            "入口边界条件不当",
            "忽略浮力效应",
            "网格质量差导致不收敛",
            "时均结果掩盖瞬态问题"
        ]
    ),
    
    "electrical": ExpertPersona(
        role_type="电气专家",
        thinking_framework="功率-效率-EMC 系统思维",
        key_questions=[
            "功率等级和效率目标是什么？",
            "主要损耗分布在哪里？",
            "是否有EMI问题？传导还是辐射？",
            "电源纹波是否满足要求？",
            "保护功能是否完备？"
        ],
        domain_knowledge="""
功率计算：P=UI, P=I²R, P=U²/R
效率分析：η=Pout/Pin, 损耗=导通损耗+开关损耗
EMC规范：传导30MHz以下，辐射30MHz以上
滤波设计：LC滤波器截止频率f=1/(2π√LC)
热设计：功率器件热阻Rth=ΔT/P
""",
        analysis_approach="1.功率拓扑分析→2.损耗分解→3.效率优化→4.EMC分析→5.可靠性评估",
        common_pitfalls=[
            "忽略开关损耗",
            "PCB布局导致的干扰",
            "热设计裕量不足",
            "忽略瞬态应力"
        ]
    ),
    
    "control": ExpertPersona(
        role_type="控制专家",
        thinking_framework="建模-分析-设计-验证 控制工程方法",
        key_questions=[
            "被控对象的动态特性如何？",
            "控制目标是什么？精度、响应速度？",
            "有哪些干扰需要抑制？",
            "传感器和执行器特性如何？",
            "稳定性裕度是否足够？"
        ],
        domain_knowledge="""
控制系统：开环/闭环、PID、状态空间
PID调参：Ziegler-Nichols、继电反馈、频域设计
稳定性：相位裕度>45°, 增益裕度>6dB
性能指标：上升时间、调节时间、超调量、稳态误差
现代控制：模型预测MPC、自适应控制、鲁棒控制
""",
        analysis_approach="1.系统建模→2.开环分析→3.控制器设计→4.仿真验证→5.参数整定",
        common_pitfalls=[
            "模型与实际偏差大",
            "忽略执行器饱和",
            "采样率不足",
            "抗扰动能力差"
        ]
    ),
    
    "system": ExpertPersona(
        role_type="系统集成专家",
        thinking_framework="系统工程V模型：需求→设计→实现→验证",
        key_questions=[
            "系统边界和接口如何定义？",
            "各子系统之间有无冲突？",
            "整体性能是否满足要求？",
            "是否存在单点故障？",
            "成本和进度约束如何？"
        ],
        domain_knowledge="""
系统工程：需求分析、功能分解、接口定义、验证确认
权衡分析：性能vs成本vs进度vs风险
接口管理：机械接口、电气接口、热接口、软件接口
验证方法：测试、分析、检查、演示
FMEA：故障模式与影响分析
""",
        analysis_approach="1.需求分析→2.系统架构→3.接口协调→4.权衡优化→5.验证规划",
        common_pitfalls=[
            "接口定义不清晰",
            "忽略交叉影响",
            "验证覆盖不全",
            "变更管理失控"
        ]
    )
}


class ExpertRoleEnhancer:
    """
    专家角色强化器
    
    根据专家类型提供强化的提示词和知识
    """
    
    def __init__(self):
        self.personas = EXPERT_PERSONAS
    
    def get_persona(self, expert_domain: str) -> Optional[ExpertPersona]:
        """根据领域获取专家人格"""
        domain_lower = expert_domain.lower()
        
        # 关键词匹配
        keyword_map = {
            "thermal": ["热", "温度", "散热", "thermal", "temperature", "cooling"],
            "acoustic": ["声", "噪音", "噪声", "acoustic", "noise", "sound"],
            "structural": ["结构", "强度", "振动", "structural", "strength", "vibration"],
            "fluid": ["流体", "流动", "气流", "fluid", "flow", "air"],
            "electrical": ["电", "电气", "功率", "electrical", "power", "circuit"],
            "control": ["控制", "自动化", "control", "automation", "pid"],
            "system": ["系统", "集成", "综合", "system", "integration"]
        }
        
        for persona_key, keywords in keyword_map.items():
            if any(kw in domain_lower for kw in keywords):
                return self.personas.get(persona_key)
        
        return None
    
    def enhance_prompt(self, base_prompt: str, expert_domain: str) -> str:
        """增强专家提示词"""
        persona = self.get_persona(expert_domain)
        if persona:
            return f"{persona.to_prompt()}\n\n{base_prompt}"
        return base_prompt
    
    def get_system_prompt(self, expert_name: str, expert_role: str, expert_domain: str) -> str:
        """生成增强的系统提示词"""
        persona = self.get_persona(expert_domain)
        
        base = f"你是{expert_name}，专业角色是{expert_role}。"
        
        if persona:
            base += f"""

{persona.thinking_framework}

在分析问题时，请运用你的专业思维框架，确保回答：
1. 有理论依据
2. 有定量分析
3. 考虑了常见陷阱
4. 给出可操作的建议
"""
        else:
            base += "\n请给出专业、深入、可操作的分析和建议。"
        
        return base
