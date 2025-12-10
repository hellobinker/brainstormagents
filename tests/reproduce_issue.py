import requests
import json
import sys
import time

BASE_URL = "http://localhost:8000"

def test_session_flow():
    # 1. Start Session with 1 agent
    print("Starting session...")
    start_payload = {
        "topic": "Test Topic for Graph & Summary",
        "agents": [
            {"name": "Agent_Single", "role": "Tester", "expertise": "Testing", "style": "Rigorous", "personality_traits": ["Detail"], "model_name": "mock"}
        ],
        "session_id": "test_session_automated",
        "api_key": "sk-mock-key-for-testing",
        "phase_rounds": {"opening": 1, "divergence": 0, "convergence": 0} 
    }
    
    try:
        res = requests.post(f"{BASE_URL}/session/start", json=start_payload)
        if res.status_code != 200:
            print(f"Failed to start session: {res.text}")
            return
        print("Session started.")
    except Exception as e:
        print(f"Failed to start session ex: {e}")
        return

    # 2. Stream Full Session
    print("Streaming session...")
    url = f"{BASE_URL}/session/stream_full?session_id=test_session_automated"
    
    received_summary = False
    graph_nodes = 0
    event_type = None
    
    try:
        with requests.get(url, stream=True) as response:
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('event: '):
                        event_type = decoded_line[7:].strip()
                    elif decoded_line.startswith('data: '):
                        data_str = decoded_line[6:]
                        try:
                            data = json.loads(data_str)
                            if event_type == 'summary':
                                print("Received SUMMARY event!")
                                content = data.get('content', '')
                                print(f"Summary content: {content[:50]}...")
                                if content:
                                    received_summary = True
                            
                            if event_type == 'graph_update':
                                # Check number of agent nodes
                                nodes = data.get('nodes', [])
                                agent_nodes = [n for n in nodes if n.get('type') == 'agent']
                                graph_nodes = len(agent_nodes)
                                # print(f"Graph update: {graph_nodes} agents")
                                
                        except json.JSONDecodeError:
                            pass
    except Exception as e:
        print(f"Streaming error: {e}")

    print("-" * 30)
    print(f"Final Graph Agent Nodes: {graph_nodes}")
    if graph_nodes == 1:
        print("PASS: Correct number of agent nodes (1).")
    else:
        print(f"FAIL: Expected 1 agent node, got {graph_nodes}")
        
    if received_summary:
         print("PASS: Received summary event.")
    else:
         print("FAIL: Did not receive summary event.")

if __name__ == "__main__":
    test_session_flow()
