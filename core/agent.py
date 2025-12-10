from typing import List, Dict, Any
from core.protocol import Message
from config import DEFAULT_MODEL

class Agent:
    def __init__(self, name: str, role: str, expertise: str, style: str, personality_traits: List[str], model_name: str = None):
        self.name = name
        self.role = role
        self.expertise = expertise
        self.style = style
        self.personality_traits = personality_traits
        self.model_name = model_name or DEFAULT_MODEL
        self.history: List[Message] = []
        self.current_emotion: str = "neutral"
        
    def update_history(self, message: Message):
        self.history.append(message)
        
    def generate_response(self, topic: str, session_history: List[Message], llm_client) -> str:
        # This method will be overridden or implemented to call the LLM
        raise NotImplementedError("Subclasses or instances must implement generate_response")

    def get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, a member of a brainstorming group.\n"
            f"Role: {self.role}\n"
            f"Expertise: {self.expertise}\n"
            f"Style: {self.style}\n"
            f"Personality: {', '.join(self.personality_traits)}\n"
            f"Current Emotion: {self.current_emotion}\n"
        )
