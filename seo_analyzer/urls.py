"""
SEO Analyzer URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DomainViewSet,
    PageViewSet,
    PageGroupViewSet,
    PageGroupCategoryViewSet,
    SEOMetricsViewSet,
    SEOIssueViewSet,
    SEOAnalysisReportViewSet,
    SitemapConfigViewSet,
    SitemapHistoryViewSet,
    SitemapAnalysisView,
    # Sitemap Editor
    SitemapEntryViewSet,
    SitemapEditSessionViewSet,
    SitemapEntryChangeViewSet,
    # Sitemap AI
    SitemapAIViewSet,
    AIConversationViewSet,
    # Workspace
    WorkspaceViewSet,
)
from .views.canvas_tab import CanvasTabViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'domains', DomainViewSet, basename='domain')
router.register(r'pages', PageViewSet, basename='page')
router.register(r'page-groups', PageGroupViewSet, basename='pagegroup')
router.register(r'page-group-categories', PageGroupCategoryViewSet, basename='pagegroupcategory')
router.register(r'metrics', SEOMetricsViewSet, basename='seometrics')

# AI SEO Advisor routes (Day 2)
router.register(r'seo-issues', SEOIssueViewSet, basename='seoissue')
router.register(r'seo-reports', SEOAnalysisReportViewSet, basename='seoanalysisreport')
router.register(r'sitemap-configs', SitemapConfigViewSet, basename='sitemapconfig')
router.register(r'sitemap-history', SitemapHistoryViewSet, basename='sitemaphistory')

# Sitemap Analysis routes
router.register(r'sitemap-analysis', SitemapAnalysisView, basename='sitemapanalysis')

# Sitemap Editor routes
router.register(r'sitemap-editor/entries', SitemapEntryViewSet, basename='sitemapentry')
router.register(r'sitemap-editor/sessions', SitemapEditSessionViewSet, basename='sitemapeditsession')
router.register(r'sitemap-editor/changes', SitemapEntryChangeViewSet, basename='sitemapentrychange')

# Sitemap AI routes
router.register(r'sitemap-ai', SitemapAIViewSet, basename='sitemapai')

# AI Chat routes
router.register(r'ai-chat/conversations', AIConversationViewSet, basename='aiconversation')

# Workspace routes
router.register(r'workspaces', WorkspaceViewSet, basename='workspace')

# Canvas Tab routes (per-domain tabs)
router.register(r'canvas-tabs', CanvasTabViewSet, basename='canvastab')

urlpatterns = router.urls
