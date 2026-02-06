"""
AI Services Package

Refactored AI modules for SEO analysis and fixes.

Structure:
- base.py: Common utilities (page fetching, context building)
- content_fixer.py: Title, description, H1, content fixes
- seo_actions.py: Keywords, internal links, quick wins
- gsc_actions.py: Google Search Console actions
- git_deployer.py: Git deployment utilities
- analysis_engine.py: AI analysis engine
- vector_store.py: ChromaDB vector store
- claude_client.py: Claude API client
"""

# Re-export for backward compatibility
from .fixer import AIAutoFixer
from .analysis_engine import AIAnalysisEngine
from .vector_store import SEOVectorStore, get_vector_store
from .claude_client import ClaudeAPIClient

__all__ = [
    'AIAutoFixer',
    'AIAnalysisEngine',
    'SEOVectorStore',
    'get_vector_store',
    'ClaudeAPIClient',
]
