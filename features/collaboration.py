from core.agent import Agent
from core.protocol import Message

class HumanAICollaboration:
    def __init__(self):
        pass

    def create_human_agent(self, name: str) -> Agent:
        """
        Creates a special agent that represents a human user.
        """
        # Human agent doesn't need LLM generation logic in the same way,
        # but we need to fit it into the system.
        # We'll handle human input separately in the main loop.
        return Agent(
            name=name,
            role="Human Participant",
            expertise="Human Intuition",
            style="Unpredictable",
            personality_traits=["Creative", "Adaptive"]
        )
