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
)

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

urlpatterns = router.urls
