"""
SEO Analysis Reports ViewSet
"""
from rest_framework import viewsets

from ..models import SEOAnalysisReport
from ..serializers import SEOAnalysisReportSerializer, SEOAnalysisReportListSerializer


class SEOAnalysisReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for SEO Analysis Reports (Read-only)
    Reports are created via Page analysis action
    """
    queryset = SEOAnalysisReport.objects.all().select_related('domain', 'page').order_by('-analyzed_at')

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == 'list':
            return SEOAnalysisReportListSerializer
        return SEOAnalysisReportSerializer

    def get_queryset(self):
        """Filter by page or domain"""
        queryset = super().get_queryset()

        page_id = self.request.query_params.get('page_id')
        domain_id = self.request.query_params.get('domain')
        report_type = self.request.query_params.get('report_type')

        if page_id:
            queryset = queryset.filter(page_id=page_id)
        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)
        if report_type:
            queryset = queryset.filter(report_type=report_type)

        return queryset
