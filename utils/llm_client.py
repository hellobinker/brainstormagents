import os
from openai import OpenAI
from typing import Iterator

class LLMClient:
    def __init__(self, api_key: str = None, base_url: str = None, timeout: float = 60.0):
        # Use a dummy key if none provided, to allow instantiation for mock mode
        key = api_key or os.environ.get("OPENAI_API_KEY") or "sk-mock-key-for-testing"
        base = base_url or os.environ.get("OPENAI_BASE_URL")
        try:
            self.client = OpenAI(api_key=key, base_url=base, timeout=timeout)
        except Exception as e:
            print(f"Error init client: {e}")
            self.client = OpenAI(api_key="mock", base_url="base", timeout=timeout)

    def get_completion(self, system_prompt: str, user_prompt: str, model: str = "gpt-3.5-turbo", timeout: float = None) -> str:
        """Get non-streaming completion"""
        # Check if we are using the mock key
        if self.client.api_key == "sk-mock-key-for-testing" or self.client.api_key == "mock":
            print("[WARN] No API Key found. Using Mock Response.")
            if "Markdown" in system_prompt or "Markdown" in user_prompt or "报告" in user_prompt:
                return """# 🚀 创新方案验证报告 (Mock)

## 1. 执行摘要
这是在测试模式下生成的模拟报告。实际运行时，这里将显示由 AI 生成的详细分析。

## 2. 核心观点
- **观点 A**: 模拟的观点内容...
- **观点 B**: 另一个模拟观点...

## 3. 建议
建议在正式环境配置有效的 API Key 以获取真实结果。
"""
            return f"[Mock Response] Interesting point about {user_prompt[:20]}... I think we should explore this further."

        try:
            # Create a temp client with custom timeout if specified, or use default with increased timeout
            # Note: OpenAI client instances are cheap to create if needed, but here we can just pass timeout to the request if supported?
            # Actually openai-python v1 passes timeout in the constructor. We can override it per request in .create()?
            # Yes, .create(..., timeout=...) is supported in newer versions, checking docs logic.
            # Assuming standard openai lib behavior:
            extra_args = {}
            if timeout:
                extra_args['timeout'] = timeout

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                **extra_args
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error calling LLM: {e}")
            return f"[Mock Response due to error] I agree with the previous point and suggest we consider the implications of {user_prompt[:10]}."
    
    def get_completion_stream(self, system_prompt: str, user_prompt: str, model: str = "gpt-3.5-turbo") -> Iterator[str]:
        """Get streaming completion - yields content chunks"""
        # Check if we are using the mock key
        if self.client.api_key == "sk-mock-key-for-testing":
            print("[WARN] No API Key found. Using Mock Streaming Response.")
            mock_response = f"[Mock Response] Interesting point about {user_prompt[:20]}... I think we should explore this further."
            # Simulate streaming by yielding word by word
            for word in mock_response.split():
                yield word + " "
            return

        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            print(f"Error calling LLM stream: {e}")
            yield f"[Mock Response due to error] I agree with the previous point and suggest we consider the implications of {user_prompt[:10]}."

    def list_models(self) -> list[str]:
        """List available models from the API"""
        if self.client.api_key == "sk-mock-key-for-testing" or self.client.api_key == "mock":
            return ["mock-model-default"]
            
        try:
            models = self.client.models.list()
            # Filter for chat models (exclude audio, embedding, etc based on common naming conventions)
            model_ids = [m.id for m in models.data]
            chat_models = [
                m for m in model_ids 
                if not any(x in m for x in ['embedding', 'audio', 'tts', 'dall-e', 'whisper', 'moderation'])
            ]
            # Prioritize common high-quality models in sorting
            priority = ['grok', 'gpt-5', 'gpt-4', 'claude-3', 'gemini']
            
            def sort_key(name):
                for i, p in enumerate(priority):
                    if p in name:
                        return (i, name)
                return (len(priority), name)
                
            return sorted(chat_models, key=sort_key)
        except Exception as e:
            print(f"Error listing models: {e}")
            return []
