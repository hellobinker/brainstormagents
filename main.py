import os
import time
from core.agent import Agent
from core.session import BrainstormingSession
from utils.llm_client import LLMClient
from features.role_switcher import DynamicRoleSwitcher
from features.emotion_engine import EmotionalIntelligenceEngine
from features.knowledge import CrossDomainConnector
from features.visualization import RealTimeVisualizer
from features.collaboration import HumanAICollaboration

def main():
    print("Initializing Multi-Agent Brainstorming System...")
    
    # Initialize components
    # User provided configuration
    api_key = "sk-j3MQdosfgMzzOHOtA7MUnrxHSNIdaO44FzMlk7RRJIcjrf8r"
    base_url = "https://yunwu.ai/v1"
    # Available models: grok-4.1-fast, gemini-3-pro-preview
    # Using gemini-3-pro-preview as default for high quality
    default_model = "gemini-3-pro-preview" 
    
    llm_client = LLMClient(api_key=api_key, base_url=base_url)
    role_switcher = DynamicRoleSwitcher()
    emotion_engine = EmotionalIntelligenceEngine()
    knowledge_connector = CrossDomainConnector()
    visualizer = RealTimeVisualizer()
    human_collab = HumanAICollaboration()
    
    # Define Agents
    agents = [
        Agent("Alice", "Innovator", "AI & ML", "Creative", ["Open", "Imaginative"]),
        Agent("Bob", "Critic", "Cybersecurity", "Analytical", ["Cautious", "Logical"]),
        Agent("Charlie", "Integrator", "Systems Engineering", "Holistic", ["Organized", "Diplomatic"])
    ]
    
    # Add a human agent (mocked for this script)
    human_agent = human_collab.create_human_agent("Dave (Human)")
    # For the purpose of this automated script, we won't add the human to the active loop 
    # to avoid blocking on input, but we acknowledge the capability.
    
    topic = "Designing a sustainable city on Mars"
    session = BrainstormingSession(topic, agents, llm_client)
    
    print(f"Topic: {topic}")
    print("Starting Session...")
    
    for i in range(1, 4): # Run 3 rounds
        print(f"\n=== Round {i} ===")
        
        # 1. Inject Cross-Domain Knowledge
        if i == 2:
            insight = knowledge_connector.get_cross_domain_insight(topic)
            print(f"\n[System] Injecting Cross-Domain Insight: {insight}\n")
            # Add insight as a system message to history (hacky but works)
            from core.protocol import Message
            session.add_message(Message("System", insight))
            
        # 2. Update Emotions
        emotion_engine.update_emotions(agents, session.history)
        for agent in agents:
            modifier = emotion_engine.get_emotional_prompt_modifier(agent)
            if modifier:
                print(f"[{agent.name} Emotion Update]: {agent.current_emotion} -> {modifier}")
        
        # 3. Run Round
        session.run_round()
        
        # 4. Analyze and Switch Roles
        changes = role_switcher.analyze_and_switch(agents, session.history)
        for change in changes:
            print(f"[Role Switch]: {change}")
            
        # 5. Update Visualization
        visualizer.update_graph(session.history)
        
    print("\nSession Complete.")
    print("Visualization Data (Snippet):")
    print(visualizer.export_data()[:200] + "...")

if __name__ == "__main__":
    main()
