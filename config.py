# -*- coding: utf-8 -*-
"""
Centralized Configuration Management

All configurable values (model names, timeouts, API settings) should be defined here.
Import from this module instead of hardcoding values in individual files.
"""
import os

# =============================================================================
# API Configuration
# =============================================================================
API_KEY = os.environ.get("OPENAI_API_KEY", "sk-j3MQdosfgMzzOHOtA7MUnrxHSNIdaO44FzMlk7RRJIcjrf8r")
API_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://yunwu.ai/v1")

# =============================================================================
# Model Configuration
# =============================================================================
# Primary model for high-quality output
DEFAULT_MODEL = "gemini-2.5-flash-lite"

# Fallback models (in order of preference) when primary fails
FALLBACK_MODELS = ["gpt-5-chat", "grok-4.1-fast"]

# Model for summary generation (typically needs more capability)
SUMMARY_MODEL = "gemini-3-pro-preview"

# Available models shown in frontend dropdown
AVAILABLE_MODELS = [
    "gemini-2.5-flash-lite-thinking",
    "gemini-3-pro-preview",
    "grok-4.1-fast", 
    "gpt-5-mini", 
    "gemini-2.5-flash", 
    "gpt-4",
    "gpt-5-chat",
    "gemini-2.5-flash-lite"
]

# =============================================================================
# Timeout Configuration (in seconds)
# =============================================================================
# Default timeout for API calls
DEFAULT_TIMEOUT = 90.0

# Extended timeout for complex operations (summaries, phase openings)
EXTENDED_TIMEOUT = 120.0

# =============================================================================
# Session Configuration
# =============================================================================
# Default session ID when not specified
DEFAULT_SESSION_ID = "default"

# =============================================================================
# Phase Configuration
# =============================================================================
# Default rounds per phase
DEFAULT_PHASE_ROUNDS = {
    "define_topic": 1,
    "diverge": 2,
    "deepen": 2,
    "evaluate": 1,
    "integrate": 1
}
