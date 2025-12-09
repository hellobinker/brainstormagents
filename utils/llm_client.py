import os
from openai import OpenAI
from typing import Iterator

class LLMClient:
    def __init__(self, api_key: str = None, base_url: str = None):
        # Use a dummy key if none provided, to allow instantiation for mock mode
        key = api_key or os.environ.get("OPENAI_API_KEY") or "sk-mock-key-for-testing"
        base = base_url or os.environ.get("OPENAI_BASE_URL")
        self.client = OpenAI(api_key=key, base_url=base)

    def get_completion(self, system_prompt: str, user_prompt: str, model: str = "gpt-3.5-turbo") -> str:
        """Get non-streaming completion"""
        # Check if we are using the mock key
        if self.client.api_key == "sk-mock-key-for-testing":
            print("[WARN] No API Key found. Using Mock Response.")
            return f"[Mock Response] Interesting point about {user_prompt[:20]}... I think we should explore this further."

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
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
