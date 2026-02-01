"""
Page ViewSet
"""
import logging
from collections import deque
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction

from ..models import Page
from ..serializers import (
    PageListSerializer,
    PageDetailSerializer,
    PageUpdateSerializer,
    SEOMetricsSerializer,
)
from ..utils import is_descendant

logger = logging.getLogger(__name__)


class PageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Page operations (supports create, read, update, delete)
    """
    queryset = Page.objects.all().select_related('domain')

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action in ['update', 'partial_update']:
            return PageUpdateSerializer
        elif self.action == 'list':
            return PageListSerializer
        return PageDetailSerializer

    def get_queryset(self):
        """Filter by domain if provided"""
        queryset = super().get_queryset()
        domain_id = self.request.query_params.get('domain', None)
        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)
        return queryset

    @action(detail=False, methods=['post'], url_path='bulk-update-positions')
    def bulk_update_positions(self, request):
        """
        Bulk update positions for multiple pages
        POST /api/v1/pages/bulk-update-positions/
        """
        updates = request.data.get('updates', [])

        if not updates:
            return Response(
                {'error': 'No updates provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            page_ids = [update['id'] for update in updates]
            for update in updates:
                if 'x' not in update or 'y' not in update:
                    return Response(
                        {'error': f"Missing x or y coordinate in update for page {update.get('id')}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        except KeyError:
            return Response(
                {'error': 'Missing id field in one or more updates'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            pages = Page.objects.filter(id__in=page_ids)
            existing_ids = set(pages.values_list('id', flat=True))

            missing_ids = set(page_ids) - existing_ids
            if missing_ids:
                return Response({
                    'error': 'Invalid page IDs',
                    'missing_ids': list(missing_ids)
                }, status=status.HTTP_400_BAD_REQUEST)

            pages_by_id = {page.id: page for page in pages}

            pages_to_update = []
            for update in updates:
                page = pages_by_id[update['id']]
                page.manual_position_x = update['x']
                page.manual_position_y = update['y']
                page.use_manual_position = True
                pages_to_update.append(page)

            Page.objects.bulk_update(
                pages_to_update,
                ['manual_position_x', 'manual_position_y', 'use_manual_position'],
                batch_size=100
            )

        return Response({
            'updated': len(pages_to_update),
            'total': len(updates)
        })

    @action(detail=True, methods=['post'], url_path='reset-position')
    def reset_position(self, request, pk=None):
        """
        Reset position to auto-layout
        POST /api/v1/pages/{id}/reset-position/
        """
        page = self.get_object()
        page.use_manual_position = False
        page.manual_position_x = None
        page.manual_position_y = None
        page.save(update_fields=['use_manual_position', 'manual_position_x', 'manual_position_y'])

        return Response({'message': 'Position reset to auto-layout'})

    @action(detail=True, methods=['post'], url_path='change-parent')
    def change_parent(self, request, pk=None):
        """
        Change parent page (reparent in tree)
        POST /api/v1/pages/{id}/change-parent/
        """
        page = self.get_object()
        parent_id = request.data.get('parent_id')

        if parent_id:
            try:
                new_parent = Page.objects.get(id=parent_id, domain=page.domain)
            except Page.DoesNotExist:
                return Response(
                    {'error': f'Parent page {parent_id} not found in this domain'},
                    status=status.HTTP_404_NOT_FOUND
                )

            if is_descendant(page, new_parent):
                return Response(
                    {'error': 'Cannot create circular parent relationship - target is a descendant'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            new_parent = None

        with transaction.atomic():
            page.parent_page = new_parent
            page.depth_level = (new_parent.depth_level + 1) if new_parent else 0
            page.save(update_fields=['parent_page', 'depth_level'])

            self._recalculate_descendant_depths(page)

        return Response({
            'message': 'Parent updated successfully',
            'new_depth': page.depth_level
        })

    @action(detail=False, methods=['post'], url_path='bulk-reparent')
    def bulk_reparent(self, request):
        """
        Bulk reparent multiple pages at once
        POST /api/v1/pages/bulk-reparent/
        """
        changes = request.data.get('changes', [])

        if not changes:
            return Response({'error': 'No changes provided'}, status=status.HTTP_400_BAD_REQUEST)

        results = {
            'success': [],
            'failed': [],
            'total': len(changes)
        }

        with transaction.atomic():
            for change in changes:
                page_id = change.get('page_id')
                parent_id = change.get('parent_id')

                try:
                    page = Page.objects.get(id=page_id)

                    if parent_id:
                        new_parent = Page.objects.get(id=parent_id, domain=page.domain)

                        if is_descendant(page, new_parent):
                            results['failed'].append({
                                'page_id': page_id,
                                'error': 'Circular relationship detected'
                            })
                            continue
                    else:
                        new_parent = None

                    page.parent_page = new_parent
                    page.depth_level = (new_parent.depth_level + 1) if new_parent else 0
                    page.save(update_fields=['parent_page', 'depth_level'])

                    self._recalculate_descendant_depths(page)

                    results['success'].append({
                        'page_id': page_id,
                        'new_depth': page.depth_level
                    })

                except Page.DoesNotExist:
                    results['failed'].append({
                        'page_id': page_id,
                        'error': 'Page not found'
                    })
                except Exception as e:
                    results['failed'].append({
                        'page_id': page_id,
                        'error': str(e)
                    })

        return Response({
            'message': f'Processed {results["total"]} changes: {len(results["success"])} succeeded, {len(results["failed"])} failed',
            'results': results
        })

    def _recalculate_descendant_depths(self, page):
        """Update depth levels for all descendants using BFS."""
        pages_to_update = []
        queue = deque([(page, page.depth_level)])

        while queue:
            current_page, parent_depth = queue.popleft()

            children = current_page.children.all()

            for child in children:
                new_depth = parent_depth + 1
                if child.depth_level != new_depth:
                    child.depth_level = new_depth
                    pages_to_update.append(child)

                queue.append((child, new_depth))

        if pages_to_update:
            Page.objects.bulk_update(pages_to_update, ['depth_level'], batch_size=100)

    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """
        Get latest metrics for a page
        GET /api/v1/pages/{id}/metrics/
        """
        page = self.get_object()
        latest_metrics = page.seo_metrics.first()

        if not latest_metrics:
            return Response({
                'message': 'No metrics available for this page'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = SEOMetricsSerializer(latest_metrics)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='metrics/history')
    def metrics_history(self, request, pk=None):
        """
        Get historical metrics for a page
        GET /api/v1/pages/{id}/metrics/history/
        """
        page = self.get_object()

        metrics = page.seo_metrics.all().order_by('-snapshot_date')[:30]

        serializer = SEOMetricsSerializer(metrics, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='analyze', permission_classes=[])
    def analyze(self, request, pk=None):
        """
        Run SEO analysis on this page
        POST /api/v1/pages/{id}/analyze/
        """
        from ..services.page_analysis_service import PageAnalysisService

        page = self.get_object()

        try:
            include_content = request.data.get('include_content_analysis', True)
            target_keywords = request.data.get('target_keywords', [])
            verify_mode = request.data.get('verify_mode', False)

            service = PageAnalysisService(logger_instance=logger)
            result = service.analyze_page(
                page,
                include_content=include_content,
                target_keywords=target_keywords,
                verify_mode=verify_mode
            )

            response_data = service.format_response_data(result)
            response_data['verify_mode'] = verify_mode
            return Response(response_data)

        except Exception as e:
            logger.error(f"Page analysis failed for {page.url}: {e}", exc_info=True)
            return Response(
                {'error': f'Analysis failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
