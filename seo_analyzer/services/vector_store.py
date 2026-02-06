"""
Vector Store Service (Compatibility Wrapper)

This module redirects to the refactored ai/ package.
All functionality is now in services/ai/vector_store.py
"""
# Backward compatibility - redirect to new location
from .ai.vector_store import SEOVectorStore, get_vector_store

__all__ = ['SEOVectorStore', 'get_vector_store']
