from openai import OpenAI
import time

api_key = "sk-j3MQdosfgMzzOHOtA7MUnrxHSNIdaO44FzMlk7RRJIcjrf8r"
base_url = "https://yunwu.ai/v1"

client = OpenAI(api_key=api_key, base_url=base_url, timeout=15.0)

print("Testing gpt-5.1...")
start = time.time()
try:
    response = client.chat.completions.create(
        model="gpt-5.1",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=5
    )
    print(f"Success! Time: {time.time()-start:.2f}s")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Failed! Time: {time.time()-start:.2f}s")
    print(f"Error: {e}")
