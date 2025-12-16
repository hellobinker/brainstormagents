# -*- coding: utf-8 -*-
"""
Tests for the new async LLM client and parallel techniques
"""
import pytest
import asyncio
from utils.async_llm_client import AsyncLLMClient, get_async_client
from features.async_techniques import AsyncParallelDivergence, AsyncChainDeepening, AsyncDebateMode


class MockAgent:
    """Mock agent for testing"""
    def __init__(self, name, role, expertise):
        self.name = name
        self.role = role
        self.expertise = expertise
        self.model_name = "gpt-4"
    
    def get_system_prompt(self):
        return f"You are {self.name}, a {self.role} expert in {self.expertise}."


@pytest.fixture
def async_client():
    """Create async client in mock mode"""
    return AsyncLLMClient(api_key="sk-mock-key-for-testing")


@pytest.fixture
def mock_agents():
    """Create mock agents for testing"""
    return [
        MockAgent("Alice", "Innovator", "AI"),
        MockAgent("Bob", "Critic", "Security"),
        MockAgent("Charlie", "Integrator", "Systems")
    ]


class TestAsyncLLMClient:
    """Tests for AsyncLLMClient"""
    
    def test_init_mock_mode(self, async_client):
        """Test client initializes in mock mode with invalid key"""
        assert async_client._mock_mode is True
    
    @pytest.mark.asyncio
    async def test_get_completion_async_mock(self, async_client):
        """Test async completion returns mock response"""
        response = await async_client.get_completion_async(
            system_prompt="Test system",
            user_prompt="Tell me about AI"
        )
        assert "[Mock Response]" in response
    
    @pytest.mark.asyncio
    async def test_get_parallel_completions(self, async_client):
        """Test parallel completions work"""
        prompts = [
            {"system_prompt": "Test", "user_prompt": "Prompt 1"},
            {"system_prompt": "Test", "user_prompt": "Prompt 2"},
            {"system_prompt": "Test", "user_prompt": "Prompt 3"}
        ]
        responses = await async_client.get_parallel_completions(prompts)
        
        assert len(responses) == 3
        for r in responses:
            assert "[Mock Response]" in r
    
    @pytest.mark.asyncio
    async def test_get_completion_stream_async(self, async_client):
        """Test async streaming completion"""
        chunks = []
        async for chunk in async_client.get_completion_stream_async(
            system_prompt="Test",
            user_prompt="Hello world"
        ):
            chunks.append(chunk)
        
        full_response = "".join(chunks)
        assert "[Mock Response]" in full_response


class TestAsyncParallelDivergence:
    """Tests for AsyncParallelDivergence"""
    
    @pytest.mark.asyncio
    async def test_generate_parallel_ideas(self, async_client, mock_agents):
        """Test parallel idea generation"""
        divergence = AsyncParallelDivergence(async_client)
        
        ideas = await divergence.generate_parallel_ideas_async(
            topic="Future of AI",
            agents=mock_agents
        )
        
        assert len(ideas) == len(mock_agents)
        for idea in ideas:
            assert "agent" in idea
            assert "role" in idea
            assert "ideas" in idea
    
    @pytest.mark.asyncio
    async def test_generate_and_cluster(self, async_client, mock_agents):
        """Test parallel generation with clustering"""
        divergence = AsyncParallelDivergence(async_client)
        
        result = await divergence.generate_and_cluster_async(
            topic="Smart Cities",
            agents=mock_agents
        )
        
        assert "parallel_ideas" in result
        assert "clustered" in result
        assert len(result["parallel_ideas"]) == len(mock_agents)


class TestAsyncDebateMode:
    """Tests for AsyncDebateMode"""
    
    @pytest.mark.asyncio
    async def test_run_debate(self, async_client, mock_agents):
        """Test debate mode execution"""
        debate = AsyncDebateMode(async_client)
        
        result = await debate.run_debate_async(
            idea="AI should be regulated",
            pro_agents=[mock_agents[0]],
            con_agents=[mock_agents[1]],
            topic="AI Regulation"
        )
        
        assert "pro_arguments" in result
        assert "con_arguments" in result
        assert "synthesis" in result
        assert len(result["pro_arguments"]) == 1
        assert len(result["con_arguments"]) == 1


class TestAsyncChainDeepening:
    """Tests for AsyncChainDeepening"""
    
    @pytest.mark.asyncio
    async def test_deepen_chain(self, async_client, mock_agents):
        """Test chain deepening"""
        chain = AsyncChainDeepening(async_client)
        
        result = await chain.deepen_chain_async(
            seed_idea="Universal Basic Income",
            agents=mock_agents,
            topic="Future of Work"
        )
        
        assert len(result) == len(mock_agents)
        for i, step in enumerate(result):
            assert step["step"] == i + 1
            assert "agent" in step
            assert "output" in step
