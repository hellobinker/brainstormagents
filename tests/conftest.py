
import pytest
from unittest.mock import MagicMock
from utils.llm_client import LLMClient

@pytest.fixture
def mock_llm_client(monkeypatch):
    """
    Fixture that mocks the LLMClient.get_completion method.
    """
    mock = MagicMock(return_value="[Mocked Content] This is a test response.")
    
    # Patch the class method directly so any instance uses it
    monkeypatch.setattr(LLMClient, "get_completion", mock)
    
    return mock
