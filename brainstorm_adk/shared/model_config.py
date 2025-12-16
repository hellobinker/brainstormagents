"""
模型配置

配置 LiteLLM 使用 yunwu.ai 兼容 API
"""
import os
from google.adk.models.lite_llm import LiteLlm
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# API 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://yunwu.ai/v1")

# 默认模型
DEFAULT_MODEL = "gemini-2.5-flash"


def get_model():
    """获取配置好的 LiteLLM 模型实例
    
    使用 yunwu.ai 兼容 API，模型为 gemini-2.5-flash
    
    Returns:
        LiteLlm: 配置好的模型实例
    """
    return LiteLlm(
        model=f"openai/{DEFAULT_MODEL}",
        api_base=OPENAI_BASE_URL,
        api_key=OPENAI_API_KEY
    )


# 预创建模型实例供 agent 使用
model = get_model()
