"""
AI Auto-Fixer Service (Compatibility Wrapper)

This module redirects to the refactored ai/ package.
All functionality is now in services/ai/fixer.py
"""
# Backward compatibility - redirect to new location
from .ai.fixer import AIAutoFixer

__all__ = ['AIAutoFixer']
