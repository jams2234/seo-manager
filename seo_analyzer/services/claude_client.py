"""
Claude API Client Service (Compatibility Wrapper)

This module redirects to the refactored ai/ package.
All functionality is now in services/ai/claude_client.py
"""
# Backward compatibility - redirect to new location
from .ai.claude_client import (
    ClaudeAPIClient,
    ClaudeRateLimiter,
    ClaudeAnalyzer,
)

__all__ = ['ClaudeAPIClient', 'ClaudeRateLimiter', 'ClaudeAnalyzer']
