"""
SEO Metrics ViewSet
"""
from rest_framework import viewsets

from ..models import SEOMetrics
from ..serializers import SEOMetricsSerializer


class SEOMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for SEO Metrics (read-only)
    """
    queryset = SEOMetrics.objects.all().select_related('page')
    serializer_class = SEOMetricsSerializer

    def get_queryset(self):
        """Filter by page if provided"""
        queryset = super().get_queryset()
        page_id = self.request.query_params.get('page', None)
        if page_id:
            queryset = queryset.filter(page_id=page_id)
        return queryset.order_by('-snapshot_date')
