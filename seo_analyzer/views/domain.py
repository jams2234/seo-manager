"""
Domain ViewSet
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count

from ..models import Domain, Page
from ..serializers import (
    DomainListSerializer,
    DomainDetailSerializer,
    DomainCreateSerializer,
    TreeStructureSerializer,
)
from ..services import DomainRefreshService
from ..utils import handle_api_error

logger = logging.getLogger(__name__)


class DomainViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Domain operations
    """
    queryset = Domain.objects.all().order_by('-updated_at')

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == 'list':
            return DomainListSerializer
        elif self.action == 'create':
            return DomainCreateSerializer
        return DomainDetailSerializer

    def perform_create(self, serializer):
        """Create domain with owner"""
        serializer.save(owner=self.request.user if self.request.user.is_authenticated else None)

    @action(detail=True, methods=['post'])
    def scan(self, request, pk=None):
        """
        Trigger full domain scan (background task or synchronous)
        POST /api/v1/domains/{id}/scan/
        """
        domain = self.get_object()

        # Try Celery first
        try:
            from ..tasks import refresh_domain_cache
            task = refresh_domain_cache.delay(domain.id)

            return Response({
                'message': 'Full scan started in background',
                'domain_id': domain.id,
                'domain_name': domain.domain_name,
                'task_id': task.id,
            })

        except Exception as e:
            logger.warning(f"Celery not available for domain {domain.id}, using synchronous scan: {e}")

            # Fall back to synchronous refresh with higher limits
            try:
                logger.info(f"Starting synchronous full scan for domain {domain.domain_name}")

                service = DomainRefreshService(max_pages=1000, max_metrics=1000, mobile_only=False)
                result = service.refresh_domain(domain)

                domain.refresh_from_db()

                serializer = DomainDetailSerializer(domain)
                return Response({
                    'message': 'Full scan completed successfully (synchronous)',
                    'pages_discovered': result['pages_discovered'],
                    'pages_processed': result['pages_processed'],
                    'metrics_fetched': result['metrics_fetched'],
                    'pages_in_db': domain.pages.count(),
                    'data': serializer.data,
                })

            except Exception as sync_error:
                return handle_api_error(
                    logger,
                    'scan domain',
                    sync_error,
                    domain_id=domain.id,
                    domain_name=domain.domain_name
                )

    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        """
        Refresh domain data (synchronous, real-time)
        POST /api/v1/domains/{id}/refresh/
        """
        domain = self.get_object()

        try:
            logger.info(f"Starting synchronous refresh for domain {domain.domain_name}")

            service = DomainRefreshService(max_pages=100, max_metrics=10, mobile_only=False)
            result = service.refresh_domain(domain)

            domain.refresh_from_db()

            serializer = DomainDetailSerializer(domain)
            return Response({
                'message': 'Domain refreshed successfully',
                'pages_discovered': result['pages_discovered'],
                'pages_processed': result['pages_processed'],
                'metrics_fetched': result['metrics_fetched'],
                'pages_in_db': domain.pages.count(),
                'data': serializer.data,
            })

        except Exception as e:
            return handle_api_error(
                logger,
                'refresh domain',
                e,
                domain_id=domain.id,
                domain_name=domain.domain_name
            )

    @action(detail=True, methods=['post'])
    def refresh_search_console(self, request, pk=None):
        """
        Refresh Search Console data only (lightweight, fast)
        POST /api/v1/domains/{id}/refresh_search_console/
        """
        domain = self.get_object()

        try:
            logger.info(f"Starting Search Console refresh for domain {domain.domain_name}")

            service = DomainRefreshService()
            result = service.refresh_search_console_only(domain)

            if result.get('error'):
                return Response(
                    {
                        'error': True,
                        'message': result.get('message', 'Search Console refresh failed'),
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            domain.refresh_from_db()

            serializer = DomainDetailSerializer(domain)
            return Response({
                'message': 'Search Console data refreshed successfully',
                'pages_updated': result['pages_updated'],
                'pages_failed': result['pages_failed'],
                'pages_in_db': domain.pages.count(),
                'elapsed_time': result.get('elapsed_time', 0),
                'data': serializer.data,
            })

        except Exception as e:
            return handle_api_error(
                logger,
                'refresh search console',
                e,
                domain_id=domain.id,
                domain_name=domain.domain_name
            )

    @action(detail=False, methods=['get'], url_path='task/(?P<task_id>[^/.]+)')
    def task_status(self, request, task_id=None):
        """
        Check Celery task status
        GET /api/v1/domains/task/{task_id}/
        """
        try:
            from celery.result import AsyncResult
            task = AsyncResult(task_id)

            response_data = {
                'task_id': task_id,
                'state': task.state,
                'ready': task.ready(),
            }

            if task.state == 'PROGRESS':
                response_data.update({
                    'current': task.info.get('current', 0),
                    'total': task.info.get('total', 100),
                    'status': task.info.get('status', ''),
                    'percent': task.info.get('percent', 0),
                })
            elif task.state == 'SUCCESS':
                response_data['result'] = task.result
            elif task.state == 'FAILURE':
                response_data['error'] = str(task.info)

            return Response(response_data)

        except Exception as e:
            return handle_api_error(
                logger,
                'get task status',
                e,
                task_id=task_id
            )

    @action(detail=True, methods=['post'], url_path='toggle-ai-analysis')
    def toggle_ai_analysis(self, request, pk=None):
        """
        Toggle sitemap AI analysis enabled status
        POST /api/v1/domains/{id}/toggle-ai-analysis/
        """
        domain = self.get_object()

        # Get the new value from request or toggle
        new_value = request.data.get('enabled')
        if new_value is None:
            domain.sitemap_ai_enabled = not domain.sitemap_ai_enabled
        else:
            domain.sitemap_ai_enabled = bool(new_value)

        domain.save(update_fields=['sitemap_ai_enabled'])

        return Response({
            'id': domain.id,
            'domain_name': domain.domain_name,
            'sitemap_ai_enabled': domain.sitemap_ai_enabled,
        })

    @action(detail=True, methods=['get'])
    def tree(self, request, pk=None):
        """
        Get domain tree structure for React Flow
        GET /api/v1/domains/{id}/tree/
        """
        domain = self.get_object()

        nodes = []
        edges = []

        # Get all pages with optimized queries
        pages = Page.objects.filter(domain=domain).select_related(
            'parent_page', 'group'
        ).prefetch_related('seo_metrics').annotate(children_count=Count('children'))

        # Calculate tree layout
        positions = self._calculate_tree_layout(pages)

        # Build nodes
        for page in pages:
            latest_metrics = page.seo_metrics.first()

            if page.is_subdomain and page.subdomain:
                label = page.subdomain
            elif page.path and page.path != '/':
                label = page.path.strip('/')
            else:
                label = domain.domain_name

            node = {
                'id': page.id,
                'label': label,
                'custom_label': page.custom_label,
                'url': page.url,
                'path': page.path,
                'seo_score': latest_metrics.seo_score if latest_metrics else None,
                'performance_score': latest_metrics.performance_score if latest_metrics else None,
                'accessibility_score': latest_metrics.accessibility_score if latest_metrics else None,
                'total_pages': page.children_count,
                'is_subdomain': page.is_subdomain,
                'is_visible': page.is_visible,
                'status': page.status,
                'depth_level': page.depth_level,
                'position': positions.get(page.id, {'x': 0, 'y': 0}),
                'group': {
                    'id': page.group.id,
                    'name': page.group.name,
                    'color': page.group.color
                } if page.group else None,
                'is_indexed': latest_metrics.is_indexed if latest_metrics else False,
                'index_status': latest_metrics.index_status if latest_metrics else None,
                'coverage_state': latest_metrics.coverage_state if latest_metrics else None,
                'avg_position': latest_metrics.avg_position if latest_metrics else None,
                'impressions': latest_metrics.impressions if latest_metrics else None,
                'clicks': latest_metrics.clicks if latest_metrics else None,
                'ctr': latest_metrics.ctr if latest_metrics else None,
                'top_queries': latest_metrics.top_queries if latest_metrics else None,
                # Sitemap mismatch tracking
                'sitemap_url': page.sitemap_url,
                'has_sitemap_mismatch': page.has_sitemap_mismatch,
                'redirect_chain': page.redirect_chain,
                'sitemap_entry': page.sitemap_entry,
                # Canonical URL index status
                'canonical_is_indexed': latest_metrics.canonical_is_indexed if latest_metrics else None,
                'canonical_index_status': latest_metrics.canonical_index_status if latest_metrics else None,
                'canonical_coverage_state': latest_metrics.canonical_coverage_state if latest_metrics else None,
            }
            nodes.append(node)

            if page.parent_page:
                edge = {
                    'source': page.parent_page.id,
                    'target': page.id,
                }
                edges.append(edge)

        tree_data = {
            'nodes': nodes,
            'edges': edges,
        }

        serializer = TreeStructureSerializer(tree_data)
        return Response(serializer.data)

    def _calculate_tree_layout(self, pages):
        """Calculate improved tree layout positions."""
        from ..services.tree_layout_service import TreeLayoutService

        layout_service = TreeLayoutService()
        return layout_service.calculate_positions(list(pages))
