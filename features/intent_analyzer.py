"""
意图分析引擎

分析用户输入的技术问题，识别：
- 问题类型（设计/调试/优化/选型等）
- 涉及的技术领域
- 将复杂问题分解为子问题
"""
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class ProblemIntent:
    """问题意图分析结果"""
    original_problem: str
    problem_type: str  # 设计/调试/优化/选型/分析/创新
    domains: List[str]  # 涉及的领域
    sub_problems: List[str]  # 分解后的子问题
    complexity: str  # simple/medium/complex
    keywords: List[str] = field(default_factory=list)  # 关键词
    confidence: float = 0.0
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# 领域关键词映射（用于初步识别）
DOMAIN_KEYWORDS = {
    "产品规划": ["产品", "市场", "用户需求", "定位", "规划", "策略"],
    "电控软件": ["电控", "软件", "代码", "程序", "控制器", "MCU", "固件"],
    "嵌入式": ["嵌入式", "单片机", "ARM", "RTOS", "驱动", "底层"],
    "IoT": ["物联网", "IoT", "联网", "WiFi", "蓝牙", "通信", "协议"],
    "TRIZ创新": ["创新", "专利", "突破", "矛盾", "发明"],
    "热技术": ["散热", "温度", "热管理", "导热", "热仿真", "冷却"],
    "流体": ["流体", "管路", "泵", "阀", "流量", "压力", "CFD"],
    "空气动力学": ["风道", "气流", "风扇", "风阻", "通风"],
    "结构": ["结构", "强度", "刚度", "振动", "模态", "变形", "CAE"],
    "燃烧": ["燃烧", "火焰", "燃气", "能效", "排放"],
    "硬件": ["电路", "PCB", "元器件", "焊接", "布局"],
    "声学": ["噪音", "噪声", "声学", "降噪", "静音", "分贝"],
    "电磁": ["电磁", "EMC", "EMI", "干扰", "屏蔽", "兼容"],
    "电机": ["电机", "马达", "转速", "扭矩", "驱动"],
    "变频": ["变频", "逆变", "功率", "谐波", "IGBT"],
    "制冷": ["制冷", "冷媒", "压缩机", "蒸发", "冷凝", "热泵"],
    "控制算法": ["PID", "控制", "算法", "调节", "反馈", "MPC"],
    "智能技术": ["智能", "语音", "APP", "交互", "联动"],
    "传感器": ["传感器", "检测", "测量", "信号", "传感"],
    "材料": ["材料", "塑料", "金属", "复合材料", "涂层"],
    "电化学": ["电池", "锂电", "充电", "BMS", "电化学"],
    "净水": ["净水", "过滤", "滤芯", "水质", "RO膜"],
    "营销": ["营销", "推广", "品牌", "销售", "渠道"],
    "健康营养": ["健康", "营养", "食品", "保健"],
    "医疗": ["医疗", "健康监测", "医疗器械", "认证"],
    "雷达": ["雷达", "感应", "毫米波", "测距", "探测"],
    "自动控制": ["自动化", "PLC", "工控", "自动"],
    "机器学习": ["机器学习", "ML", "模型", "训练", "数据"],
    "AI技术": ["AI", "人工智能", "大模型", "深度学习", "神经网络"]
}

# 问题类型关键词
PROBLEM_TYPE_KEYWORDS = {
    "设计": ["设计", "如何做", "怎么实现", "方案", "架构"],
    "调试": ["调试", "故障", "问题", "bug", "不工作", "异常", "报错"],
    "优化": ["优化", "改进", "提升", "提高", "降低", "减少"],
    "选型": ["选型", "选择", "哪个好", "推荐", "对比", "比较"],
    "分析": ["分析", "原因", "为什么", "原理", "机理"],
    "创新": ["创新", "新方案", "突破", "颠覆", "新思路"]
}


class IntentAnalyzer:
    """
    问题意图分析器
    
    使用 LLM 分析技术问题，识别领域和分解子问题。
    
    使用示例:
        analyzer = IntentAnalyzer(llm_client)
        intent = await analyzer.analyze("空调噪音大如何解决？")
        print(intent.domains)  # ["声学", "空气动力学", "结构"]
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    def _quick_domain_detect(self, problem: str) -> List[str]:
        """基于关键词的快速领域检测"""
        detected = []
        problem_lower = problem.lower()
        
        for domain, keywords in DOMAIN_KEYWORDS.items():
            for kw in keywords:
                if kw in problem_lower:
                    if domain not in detected:
                        detected.append(domain)
                    break
        
        return detected
    
    def _quick_type_detect(self, problem: str) -> str:
        """基于关键词的快速问题类型检测"""
        problem_lower = problem.lower()
        
        for ptype, keywords in PROBLEM_TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in problem_lower:
                    return ptype
        
        return "分析"  # 默认
    
    async def analyze(self, problem: str) -> ProblemIntent:
        """
        分析问题意图（异步）
        
        使用 LLM 深度分析问题，识别领域并分解子问题
        """
        # 先做快速检测
        quick_domains = self._quick_domain_detect(problem)
        quick_type = self._quick_type_detect(problem)
        
        # 使用 LLM 深度分析
        prompt = f"""请分析以下技术问题，用 JSON 格式返回分析结果。

【技术问题】
{problem}

【分析要求】
1. problem_type: 问题类型（设计/调试/优化/选型/分析/创新）
2. domains: 涉及的技术领域列表（从以下选择）
   可选领域：产品规划、电控软件、嵌入式、IoT、TRIZ创新、热技术、流体、
   空气动力学、结构、燃烧、硬件、声学、电磁、电机、变频、制冷、
   控制算法、智能技术、传感器、材料、电化学、净水、营销、健康营养、
   医疗、雷达、自动控制、机器学习、AI技术
3. sub_problems: 将问题分解为 2-5 个具体的子问题
4. complexity: 复杂度（simple/medium/complex）
5. keywords: 3-5 个关键词

【输出格式】
只输出 JSON，不要其他内容：
```json
{{
  "problem_type": "优化",
  "domains": ["热技术", "声学"],
  "sub_problems": ["子问题1", "子问题2"],
  "complexity": "medium",
  "keywords": ["关键词1", "关键词2"]
}}
```"""
        
        try:
            response = await self.llm_client.get_completion_async(
                system_prompt="你是技术问题分析专家，擅长识别问题领域并分解复杂问题。只输出 JSON。",
                user_prompt=prompt
            )
            
            # 解析 JSON
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            result = json.loads(json_str.strip())
            
            return ProblemIntent(
                original_problem=problem,
                problem_type=result.get("problem_type", quick_type),
                domains=result.get("domains", quick_domains),
                sub_problems=result.get("sub_problems", [problem]),
                complexity=result.get("complexity", "medium"),
                keywords=result.get("keywords", []),
                confidence=0.9
            )
            
        except Exception as e:
            print(f"[WARN] LLM analysis failed: {e}, using quick detection")
            # 回退到快速检测
            return ProblemIntent(
                original_problem=problem,
                problem_type=quick_type,
                domains=quick_domains if quick_domains else ["产品规划"],
                sub_problems=[problem],
                complexity="medium",
                keywords=[],
                confidence=0.5
            )
    
    def analyze_sync(self, problem: str) -> ProblemIntent:
        """
        同步分析（使用快速检测）
        """
        quick_domains = self._quick_domain_detect(problem)
        quick_type = self._quick_type_detect(problem)
        
        return ProblemIntent(
            original_problem=problem,
            problem_type=quick_type,
            domains=quick_domains if quick_domains else ["产品规划"],
            sub_problems=[problem],
            complexity="medium",
            keywords=[],
            confidence=0.5
        )
