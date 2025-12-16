"""
多模型提供商客户端

使用 LiteLLM 支持 100+ AI 模型提供商，包括：
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini)
- Azure OpenAI
- AWS Bedrock
- 自定义 OpenAI 兼容端点 (如 yunwu.ai)

配置方法：在 .env 文件中设置对应的 API 密钥
"""
import os
import asyncio
from typing import List, Dict, Any, Optional, AsyncIterator
from dotenv import load_dotenv

# 加载 .env
load_dotenv()

try:
    import litellm
    from litellm import acompletion, completion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    print("[WARN] LiteLLM not installed. Run: pip install litellm")


class MultiProviderClient:
    """
    多模型提供商统一客户端
    
    支持的模型格式:
    - openai/gpt-4
    - anthropic/claude-3-opus
    - gemini/gemini-pro
    - azure/deployment-name
    - 自定义: openai/model-name (配合 OPENAI_BASE_URL)
    
    使用示例:
        client = MultiProviderClient()
        
        # 同步调用
        response = client.complete("openai/gpt-4", "Hello!")
        
        # 异步调用
        response = await client.acomplete("anthropic/claude-3-opus", "Hello!")
        
        # 并行调用多个模型
        responses = await client.parallel_complete([
            {"model": "openai/gpt-4", "prompt": "Task 1"},
            {"model": "gemini/gemini-pro", "prompt": "Task 2"},
        ])
    """
    
    def __init__(self, default_model: str = None):
        """
        初始化客户端
        
        Args:
            default_model: 默认模型，如 "openai/gpt-4"
        """
        if not LITELLM_AVAILABLE:
            raise ImportError("LiteLLM is required. Install with: pip install litellm")
        
        self.default_model = default_model or os.getenv("DEFAULT_MODEL", "openai/gpt-4")
        
        # 配置 LiteLLM
        litellm.set_verbose = False  # 关闭详细日志
        
        # 从环境变量加载配置
        self._load_env_config()
    
    def _load_env_config(self):
        """从 .env 加载 API 配置"""
        # OpenAI 兼容端点 (如 yunwu.ai)
        if os.getenv("OPENAI_BASE_URL"):
            os.environ["OPENAI_API_BASE"] = os.getenv("OPENAI_BASE_URL")
        
        # 其他提供商的 API 密钥会自动从环境变量读取
        # ANTHROPIC_API_KEY, GOOGLE_API_KEY, AZURE_API_KEY 等
    
    def _format_model(self, model: str) -> str:
        """格式化模型名称"""
        # 如果没有提供商前缀，添加 openai/
        if "/" not in model:
            return f"openai/{model}"
        return model
    
    def complete(
        self,
        model: str = None,
        prompt: str = "",
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = None,
        **kwargs
    ) -> str:
        """
        同步调用（阻塞）
        
        Args:
            model: 模型名称，如 "openai/gpt-4"
            prompt: 用户提示
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大 token 数
        """
        model = self._format_model(model or self.default_model)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[ERROR] LiteLLM completion failed: {e}")
            return f"[Error] {str(e)}"
    
    async def acomplete(
        self,
        model: str = None,
        prompt: str = "",
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = None,
        **kwargs
    ) -> str:
        """
        异步调用（非阻塞）
        
        用于并行调用多个模型
        """
        model = self._format_model(model or self.default_model)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[ERROR] LiteLLM async completion failed: {e}")
            return f"[Error] {str(e)}"
    
    async def parallel_complete(
        self,
        requests: List[Dict[str, Any]]
    ) -> List[str]:
        """
        并行调用多个模型
        
        Args:
            requests: [
                {"model": "openai/gpt-4", "prompt": "...", "system_prompt": "..."},
                {"model": "anthropic/claude-3", "prompt": "..."},
            ]
        
        Returns:
            List of responses in same order
        """
        tasks = [
            self.acomplete(
                model=req.get("model"),
                prompt=req.get("prompt", ""),
                system_prompt=req.get("system_prompt", ""),
                temperature=req.get("temperature", 0.7)
            )
            for req in requests
        ]
        return await asyncio.gather(*tasks)
    
    async def astream(
        self,
        model: str = None,
        prompt: str = "",
        system_prompt: str = "",
        **kwargs
    ) -> AsyncIterator[str]:
        """
        异步流式调用
        
        使用方法:
            async for chunk in client.astream("openai/gpt-4", "Hello"):
                print(chunk, end="")
        """
        model = self._format_model(model or self.default_model)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await acompletion(
                model=model,
                messages=messages,
                stream=True,
                **kwargs
            )
            
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"[Stream Error] {str(e)}"


# 便捷函数 - 快速使用
_default_client: Optional[MultiProviderClient] = None

def get_client() -> MultiProviderClient:
    """获取默认客户端实例"""
    global _default_client
    if _default_client is None:
        _default_client = MultiProviderClient()
    return _default_client


async def quick_complete(model: str, prompt: str, system_prompt: str = "") -> str:
    """快速异步调用"""
    return await get_client().acomplete(model, prompt, system_prompt)


# 支持的提供商列表
SUPPORTED_PROVIDERS = {
    "openai": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "o1-preview"],
    "anthropic": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
    "google": ["gemini-pro", "gemini-1.5-pro", "gemini-2.5-flash"],
    "azure": ["配置后的部署名称"],
    "custom": ["任何 OpenAI 兼容端点的模型"],
}
