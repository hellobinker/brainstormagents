import sys
import os
import asyncio
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.session_manager import GlobalSessionManager, SessionState
from core.protocol import Message
from features.mention_parser import mention_parser

async def verify_human_interaction():
    print("=== Verifying Human Interaction and Metadata Fixes ===")
    
    # 1. Initialize Session
    sm = GlobalSessionManager()
    session_id = "test_session"
    state = SessionState(session_id)
    sm.sessions[session_id] = state
    
    # Simulate BrainstormingSession creation (mock)
    from core.session import BrainstormingSession
    class MockAgent:
        def __init__(self, name):
            self.name = name
            self.role = "Tester"
            self.expertise = "Testing"
        def update_history(self, msg): pass
        
    state.session = BrainstormingSession("Test Topic", [], None)
    
    # 2. Simulate User Message (using correct instantiation)
    # This was the bug: Message("sender", "content", {"type": "human"}) put dict in timestamp
    # Correct: Message("sender", "content", metadata={"type": "human"})
    
    sender = "TestUser"
    content = "This is a human message."
    
    # Manually creating message like server.py does now
    msg = Message(f"👤 {sender}", content, metadata={"type": "human"})
    state.session.add_message(msg)
    
    print(f"Message Created: {msg}")
    print(f"Metadata: {msg.metadata}")
    print(f"Timestamp type: {type(msg.timestamp)}")
    
    # 3. Verify Metadata
    if msg.metadata.get("type") != "human":
        print("❌ FAIL: Metadata 'type' is NOT 'human'")
        return False
    
    if isinstance(msg.timestamp, dict):
        print("❌ FAIL: Timestamp IS A DICT! (Bug regression)")
        return False
        
    print("✅ PASS: Message metadata and timestamp structure is correct.")
    
    # 4. Verify History Check Logic (from generate_phase_stream)
    recent_messages = state.session.history[-3:]
    human_instruction = ""
    found_human = False
    
    for m in reversed(recent_messages):
        if m.metadata.get("type") == "human":
            human_instruction = f"FOUND HUMAN: {m.content}"
            found_human = True
            break
            
    if found_human:
        print(f"✅ PASS: Detected human message in history. Instruction would be generated.")
    else:
        print("❌ FAIL: Did not detect human message in history.")
        return False
        
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(verify_human_interaction())
        if success:
            print("\n🎉 ALL TESTS PASSED")
            sys.exit(0)
        else:
            print("\n💥 TESTS FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
