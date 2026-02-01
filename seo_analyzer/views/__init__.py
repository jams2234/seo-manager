"""
SEO Analyzer Views

All ViewSets are imported here for backward compatibility.
"""
from .domain import DomainViewSet
from .page import PageViewSet
from .metrics import SEOMetricsViewSet
from .groups import PageGroupCategoryViewSet, PageGroupViewSet
from .seo_issues import SEOIssueViewSet
from .reports import SEOAnalysisReportViewSet
from .sitemap import SitemapConfigViewSet, SitemapHistoryViewSet, SitemapAnalysisView
from .sitemap_editor import (
    SitemapEntryViewSet,
    SitemapEditSessionViewSet,
    SitemapEntryChangeViewSet,
)
from .sitemap_ai import SitemapAIViewSet, AIConversationViewSet

__all__ = [
    'DomainViewSet',
    'PageViewSet',
    'SEOMetricsViewSet',
    'PageGroupCategoryViewSet',
    'PageGroupViewSet',
    'SEOIssueViewSet',
    'SEOAnalysisReportViewSet',
    'SitemapConfigViewSet',
    'SitemapHistoryViewSet',
    'SitemapAnalysisView',
    # Sitemap Editor
    'SitemapEntryViewSet',
    'SitemapEditSessionViewSet',
    'SitemapEntryChangeViewSet',
    # Sitemap AI
    'SitemapAIViewSet',
    'AIConversationViewSet',
]
