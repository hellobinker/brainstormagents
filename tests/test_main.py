
import pytest
from unittest.mock import patch, MagicMock
import os
from main import main

@patch('builtins.print')
@patch('time.sleep')
@patch('utils.llm_client.LLMClient.get_completion') # Mock LLM at source
def test_main_simulation_flow(mock_completion, mock_sleep, mock_print):
    """
    Test the full CLI simulation flow in main.py.
    """
    # Setup mock returns
    mock_completion.return_value = "[Mocked Content] I have a great idea about Mars!"
    
    # Force Mock Key via environment variable specifically for this test
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-mock-key-for-testing"}):
        try:
            main()
        except Exception as e:
            pytest.fail(f"main() raised an exception: {e}")
            
    # Verification
    # Check if we printed "Session Complete."
    # We need to check all calls to print
    executed_full_session = False
    for call in mock_print.call_args_list:
        if "Session Complete" in str(call):
            executed_full_session = True
            break
            
    assert executed_full_session, "Did not complete the session (missing 'Session Complete' output)"
