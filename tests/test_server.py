
import pytest
from fastapi.testclient import TestClient
from server import app
from unittest.mock import patch

client = TestClient(app)

@pytest.fixture
def mock_llm_client_server(monkeypatch):
    """
    Mock LLM client specifically for server tests if needed, 
    though the conftest one might already apply to the server's imports 
    if we are careful. But server initializes its own invalid LLMClient 
    inside start_session.
    """
    # We need to mock the LLMClient class that server.py imports
    with patch("server.LLMClient") as MockClient:
        instance = MockClient.return_value
        instance.get_completion.return_value = "[Mocked Server Response]"
        yield instance

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    # It returns a FileResponse, depending on if file exists. 
    # If index.html exists, it returns 200.

def test_start_session(mock_llm_client_server):
    payload = {
        "topic": "Mars Colonization",
        "agents": [
            {
                "name": "Elon",
                "role": "Visionary",
                "expertise": "Rocketry",
                "style": "Bold",
                "personality_traits": ["Ambitions"],
                "model_name": "gpt-5.1"
            },
            {
                "name": "Scientist",
                "role": "Critic",
                "expertise": "Biology",
                "style": "Cautious",
                "personality_traits": ["Analytical"],
                "model_name": "gpt-4"
            }
        ]
    }
    response = client.post("/session/start", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Session started"
    assert data["topic"] == "Mars Colonization"
    assert data["agent_count"] == 2

def test_get_state_no_session():
    # Reset first
    client.post("/session/reset")
    response = client.get("/session/state")
    assert response.status_code == 200
    assert response.json()["status"] == "not_started"

def test_human_message_without_session():
    client.post("/session/reset")
    payload = {"user_name": "User", "content": "Hi"}
    response = client.post("/session/human_message", json=payload)
    assert response.status_code == 400  # Expect error

def test_creativity_technique(mock_llm_client_server):
    # Start session first
    test_start_session(mock_llm_client_server)
    
    payload = {"technique": "scamper", "agent_index": 0}
    response = client.post("/techniques/creativity", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Since we mocked the LLM client in the server, we expect success 
    # but the content relies on the mocked return. 
    # However, server.py imports LLMClient from utils.llm_client.
    # The patch in fixture should handle it.
    
    # Check if technique key exists in response
    assert "technique" in data
    assert "result" in data

