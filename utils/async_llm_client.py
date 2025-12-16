# -*- coding: utf-8 -*-
"""
Async LLM Client - Non-blocking API calls using httpx
Provides true async operations for parallel agent execution
"""
import os
import httpx
import asyncio
from typing import AsyncIterator, List, Dict, Any, Optional
from config import DEFAULT_MODEL, FALLBACK_MODELS, DEFAULT_TIMEOUT, API_KEY, API_BASE_URL


class AsyncLLMClient:
    """Async LLM client using httpx for non-blocking API calls"""
    
    def __init__(self, api_key: str = None, base_url: str = None, timeout: float = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or API_KEY
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or API_BASE_URL).rstrip("/")
        self.timeout = timeout or DEFAULT_TIMEOUT
        
        # Validate configuration
        if not self.api_key or self.api_key == "sk-mock-key-for-testing":
            print("[WARN] No valid API key found. Mock mode enabled.")
            self._mock_mode = True
        else:
            self._mock_mode = False
    
    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def get_completion_async(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        model: str = None,
        timeout: float = None
    ) -> str:
        """Get non-streaming completion asynchronously"""
        model = model or DEFAULT_MODEL
        actual_timeout = timeout or self.timeout
        
        if self._mock_mode:
            await asyncio.sleep(0.1)  # Simulate API delay
            return f"[Mock Response] Interesting point about {user_prompt[:30]}... I think we should explore this further."
        
        candidate_models = [model] + [m for m in FALLBACK_MODELS if m != model]
        last_error = None
        
        async with httpx.AsyncClient(timeout=actual_timeout) as client:
            for attempt_model in candidate_models:
                try:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self.headers,
                        json={
                            "model": attempt_model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            "temperature": 0.7,
                            "stream": False
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"].strip()
                    
                except Exception as e:
                    print(f"[WARN] Async call failed for model {attempt_model}: {e}")
                    last_error = e
                    continue
        
        return f"[System Error] All models failed. Last error: {last_error}"
    
    async def get_completion_stream_async(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        model: str = None
    ) -> AsyncIterator[str]:
        """Get streaming completion asynchronously - yields content chunks"""
        model = model or DEFAULT_MODEL
        
        if self._mock_mode:
            mock_response = f"[Mock Response] Interesting point about {user_prompt[:20]}..."
            for word in mock_response.split():
                await asyncio.sleep(0.05)
                yield word + " "
            return
        
        candidate_models = [model] + [m for m in FALLBACK_MODELS if m != model]
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt_model in candidate_models:
                try:
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/chat/completions",
                        headers=self.headers,
                        json={
                            "model": attempt_model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            "temperature": 0.7,
                            "stream": True
                        }
                    ) as response:
                        response.raise_for_status()
                        
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str.strip() == "[DONE]":
                                    return
                                try:
                                    import json
                                    data = json.loads(data_str)
                                    content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if content:
                                        yield content
                                except:
                                    continue
                        return
                        
                except Exception as e:
                    print(f"[WARN] Async stream failed for model {attempt_model}: {e}")
                    continue
        
        yield "[System Error] All streaming models failed."
    
    async def get_parallel_completions(
        self, 
        prompts: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Execute multiple completions in parallel.
        
        Args:
            prompts: List of dicts with keys: system_prompt, user_prompt, model (optional)
        
        Returns:
            List of completion responses in the same order as input prompts
        """
        tasks = [
            self.get_completion_async(
                system_prompt=p["system_prompt"],
                user_prompt=p["user_prompt"],
                model=p.get("model")
            )
            for p in prompts
        ]
        return await asyncio.gather(*tasks)


# Convenience function for running async operations in sync context
def run_async(coro):
    """Run an async coroutine from sync code"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


# Global async client instance
_async_client: Optional[AsyncLLMClient] = None

def get_async_client(api_key: str = None, base_url: str = None) -> AsyncLLMClient:
    """Get or create global async client instance"""
    global _async_client
    if _async_client is None:
        _async_client = AsyncLLMClient(api_key=api_key, base_url=base_url)
    return _async_client
