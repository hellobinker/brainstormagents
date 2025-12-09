
import pytest
from core.session import BrainstormingSession
from core.agent import Agent
from core.protocol import Message
from utils.llm_client import LLMClient

@pytest.fixture
def sample_agents():
    return [
        Agent("Alice", "Innovator", "Tech", "Creative", ["Open"]),
        Agent("Bob", "Critic", "Finance", "Critical", ["Analytic"]),
    ]

def test_session_initialization(sample_agents, mock_llm_client):
    client = LLMClient()
    session = BrainstormingSession("Future of AI", sample_agents, client)
    
    assert session.topic == "Future of AI"
    assert len(session.agents) == 2
    assert session.rounds == 0
    assert len(session.history) == 0

def test_add_message(sample_agents, mock_llm_client):
    client = LLMClient()
    session = BrainstormingSession("Test Topic", sample_agents, client)
    
    msg = Message("User", "Hello", {"type": "test"})
    session.add_message(msg)
    
    assert len(session.history) == 1
    assert session.history[0].content == "Hello"
    # Verify agents updated history
    # (Assuming Agent.update_history doesn't store full history but we can check if it didn't crash)

def test_run_round(sample_agents, mock_llm_client):
    client = LLMClient()
    session = BrainstormingSession("Test Topic", sample_agents, client)
    
    # Run a round
    session.run_round()
    
    assert session.rounds == 1
    # Should resolve to 2 messages (one from each agent)
    assert len(session.history) == 2
    assert session.history[0].sender == "Alice"
    assert session.history[1].sender == "Bob"
    # Content should be our mocked value
    assert "[Mocked Content]" in session.history[0].content

