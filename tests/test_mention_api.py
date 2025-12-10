import requests
import json
import uuid

def test_api():
    url = "http://localhost:8000/session/mention"
    payload = {
        "sender": "TestScript",
        "content": "API Verification Message",
        "session_id": "default"
    }
    
    print(f"Sending POST to {url}...")
    try:
        resp = requests.post(url, json=payload, timeout=5)
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.text}")
        
        if resp.status_code == 200:
            print("✅ API Success")
        else:
            print("❌ API Failed")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_api()
