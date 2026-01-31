"""
SEO Analyzer Views
"""
import logging
from datetime import datetime, timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import (
    Domain, Page, PageGroup, PageGroupCategory, SEOMetrics, HistoricalMetrics,
    SEOIssue, SitemapConfig, SitemapHistory, SEOAnalysisReport
)
from .serializers import (
    DomainListSerializer,
    DomainDetailSerializer,
    DomainCreateSerializer,
    PageListSerializer,
    PageDetailSerializer,
    PageUpdateSerializer,
    PageGroupSerializer,
    PageGroupCategorySerializer,
    SEOMetricsSerializer,
    TreeStructureSerializer,
    HistoricalMetricsSerializer,
    SEOIssueSerializer,
    SEOIssueListSerializer,
    SitemapConfigSerializer,
    SitemapHistorySerializer,
    SEOAnalysisReportSerializer,
    SEOAnalysisReportListSerializer,
)
from .services import (
    DomainRefreshService,
)
from .services.auto_fix_service import AutoFixService
from .services.git_deployer import GitDeployer
from .utils import (
    is_descendant,
    handle_api_error,
    handle_validation_error,
    handle_not_found_error,
)

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

        This tries to trigger a Celery background task, but falls back to
        synchronous refresh if Celery is not available.
        """
        domain = self.get_object()

        # Try Celery first
        try:
            from .tasks import refresh_domain_cache
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

                # Use higher limits for full scan (includes desktop analysis)
                service = DomainRefreshService(max_pages=1000, max_metrics=1000, mobile_only=False)
                result = service.refresh_domain(domain)

                # Reload domain to get updated data
                domain.refresh_from_db()

                # Return updated data
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

        This performs a full scan of the domain:
        1. Discover pages from sitemap/crawling
        2. Fetch SEO metrics from PageSpeed Insights
        3. Fetch Search Console data
        4. Update database

        Note: Limited to 100 pages and 5 metrics for sync operation
        """
        domain = self.get_object()

        try:
            logger.info(f"Starting synchronous refresh for domain {domain.domain_name}")

            # Use DomainRefreshService (includes desktop analysis)
            service = DomainRefreshService(max_pages=100, max_metrics=10, mobile_only=False)
            result = service.refresh_domain(domain)

            # Reload domain to get updated data
            domain.refresh_from_db()

            # Return updated data
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

        This updates only Search Console data without re-running PageSpeed scans:
        1. Update index status via URL Inspection API
        2. Update search analytics (impressions, clicks, CTR, position)
        3. Update domain statistics

        Use cases:
        - Daily index status checks
        - After fixing indexing issues
        - When you don't need to re-run expensive PageSpeed scans

        Advantages:
        - Much faster than full refresh
        - Doesn't consume PageSpeed API quota
        - Can be run more frequently
        """
        domain = self.get_object()

        try:
            logger.info(f"Starting Search Console refresh for domain {domain.domain_name}")

            # Use DomainRefreshService with Search Console only mode
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

            # Reload domain to get updated data
            domain.refresh_from_db()

            # Return updated data
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

    @action(detail=True, methods=['get'])
    def tree(self, request, pk=None):
        """
        Get domain tree structure for React Flow
        GET /api/v1/domains/{id}/tree/
        """
        domain = self.get_object()

        # Build tree structure
        nodes = []
        edges = []

        # Get all pages for this domain with optimized queries
        from django.db.models import Count
        pages = Page.objects.filter(domain=domain).select_related('parent_page', 'group').prefetch_related('seo_metrics').annotate(children_count=Count('children'))

        # Calculate improved tree layout
        positions = self._calculate_tree_layout(pages)

        # Build nodes
        for page in pages:
            # Get latest metrics (already prefetched)
            latest_metrics = page.seo_metrics.first()

            # Create readable label from path or subdomain
            if page.is_subdomain and page.subdomain:
                label = page.subdomain
            elif page.path and page.path != '/':
                label = page.path.strip('/')
            else:
                label = domain.domain_name  # Use domain from context instead of page.domain

            node = {
                'id': page.id,
                'label': label,
                'custom_label': page.custom_label,
                'url': page.url,
                'path': page.path,
                'seo_score': latest_metrics.seo_score if latest_metrics else None,
                'performance_score': latest_metrics.performance_score if latest_metrics else None,
                'accessibility_score': latest_metrics.accessibility_score if latest_metrics else None,
                'total_pages': page.children_count,  # Use annotated count to avoid N+1 query
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
                # Index status from Search Console
                'is_indexed': latest_metrics.is_indexed if latest_metrics else False,
                'index_status': latest_metrics.index_status if latest_metrics else None,
                'coverage_state': latest_metrics.coverage_state if latest_metrics else None,
            }
            nodes.append(node)

            # Build edges (connections)
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
        """
        Calculate improved tree layout positions.
        Delegates to TreeLayoutService for separation of concerns.
        """
        from .services.tree_layout_service import TreeLayoutService

        layout_service = TreeLayoutService()
        return layout_service.calculate_positions(list(pages))


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
        Body: {
            "updates": [
                {"id": 1, "x": 100, "y": 200},
                {"id": 2, "x": 300, "y": 400}
            ]
        }
        """
        updates = request.data.get('updates', [])

        if not updates:
            return Response(
                {'error': 'No updates provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate all required fields before processing
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
            # Fetch all pages at once and validate they all exist
            pages = Page.objects.filter(id__in=page_ids)
            existing_ids = set(pages.values_list('id', flat=True))

            missing_ids = set(page_ids) - existing_ids
            if missing_ids:
                return Response({
                    'error': 'Invalid page IDs',
                    'missing_ids': list(missing_ids)
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create a mapping for quick lookup
            pages_by_id = {page.id: page for page in pages}

            # Update pages
            pages_to_update = []
            for update in updates:
                page = pages_by_id[update['id']]
                page.manual_position_x = update['x']
                page.manual_position_y = update['y']
                page.use_manual_position = True
                pages_to_update.append(page)

            # Bulk update in single query
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
        Body: {"parent_id": 123 or null}
        """
        page = self.get_object()
        parent_id = request.data.get('parent_id')

        # Get new parent if provided
        if parent_id:
            try:
                new_parent = Page.objects.get(id=parent_id, domain=page.domain)
            except Page.DoesNotExist:
                return Response(
                    {'error': f'Parent page {parent_id} not found in this domain'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Validate no circular relationships
            if is_descendant(page, new_parent):
                return Response(
                    {'error': 'Cannot create circular parent relationship - target is a descendant'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            new_parent = None

        # Update page and recalculate depth
        with transaction.atomic():
            page.parent_page = new_parent
            page.depth_level = (new_parent.depth_level + 1) if new_parent else 0
            page.save(update_fields=['parent_page', 'depth_level'])

            # Recalculate depth for all descendants
            self._recalculate_descendant_depths(page)

        return Response({
            'message': 'Parent updated successfully',
            'new_depth': page.depth_level
        })

    @action(detail=False, methods=['post'], url_path='bulk-reparent')
    def bulk_reparent(self, request):
        """
        Bulk reparent multiple pages at once (for performance)
        POST /api/v1/pages/bulk-reparent/
        Body: {"changes": [{"page_id": 1, "parent_id": 2 or null}, ...]}
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

                    # Get new parent if provided
                    if parent_id:
                        new_parent = Page.objects.get(id=parent_id, domain=page.domain)

                        # Validate no circular relationships
                        if is_descendant(page, new_parent):
                            results['failed'].append({
                                'page_id': page_id,
                                'error': 'Circular relationship detected'
                            })
                            continue
                    else:
                        new_parent = None

                    # Update page
                    page.parent_page = new_parent
                    page.depth_level = (new_parent.depth_level + 1) if new_parent else 0
                    page.save(update_fields=['parent_page', 'depth_level'])

                    # Recalculate depth for descendants
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
        """
        Update depth levels for all descendants using bulk update.
        Uses BFS (Breadth-First Search) to avoid recursion and minimize queries.
        """
        from collections import deque

        pages_to_update = []
        queue = deque([(page, page.depth_level)])

        while queue:
            current_page, parent_depth = queue.popleft()

            # Get all children of current page
            children = current_page.children.all()

            for child in children:
                new_depth = parent_depth + 1
                if child.depth_level != new_depth:
                    child.depth_level = new_depth
                    pages_to_update.append(child)

                # Add child to queue for processing its descendants
                queue.append((child, new_depth))

        # Bulk update all changed pages in a single query
        if pages_to_update:
            Page.bulk_update(pages_to_update, ['depth_level'], batch_size=100)

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

        # Get all metrics ordered by date
        metrics = page.seo_metrics.all().order_by('-snapshot_date')[:30]  # Last 30 entries

        serializer = SEOMetricsSerializer(metrics, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='analyze', permission_classes=[])
    def analyze(self, request, pk=None):
        """
        Run SEO analysis on this page
        POST /api/v1/pages/{id}/analyze/
        Body: {
            "include_content_analysis": true,
            "target_keywords": ["seo", "optimization"],
            "verify_mode": false  // If true, verify deployed fixes against actual website
        }
        """
        from .services.page_analysis_service import PageAnalysisService

        page = self.get_object()

        try:
            # Get parameters
            include_content = request.data.get('include_content_analysis', True)
            target_keywords = request.data.get('target_keywords', [])
            verify_mode = request.data.get('verify_mode', False)

            # Use service to perform analysis
            service = PageAnalysisService(logger_instance=logger)
            result = service.analyze_page(
                page,
                include_content=include_content,
                target_keywords=target_keywords,
                verify_mode=verify_mode
            )

            # Format response
            response_data = service.format_response_data(result)
            response_data['verify_mode'] = verify_mode
            return Response(response_data)

        except Exception as e:
            logger.error(f"Page analysis failed for {page.url}: {e}", exc_info=True)
            return Response(
                {'error': f'Analysis failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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


class PageGroupCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PageGroupCategory
    Supports CRUD operations for managing group categories
    """
    queryset = PageGroupCategory.objects.all()
    serializer_class = PageGroupCategorySerializer

    def get_queryset(self):
        """Filter by domain if provided"""
        queryset = super().get_queryset()
        domain_id = self.request.query_params.get('domain', None)
        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)
        return queryset.order_by('order', 'name')

    @action(detail=True, methods=['post'], url_path='reorder')
    def reorder(self, request, pk=None):
        """
        Update category display order
        POST /api/v1/page-group-categories/{id}/reorder/
        Body: { "order": 5 }
        """
        category = self.get_object()
        new_order = request.data.get('order')
        if new_order is not None:
            category.order = new_order
            category.save(update_fields=['order'])
            return Response({'message': 'Order updated', 'order': category.order})
        return Response({'error': 'Order not provided'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='groups')
    def groups(self, request, pk=None):
        """
        Get all groups in this category
        GET /api/v1/page-group-categories/{id}/groups/
        """
        category = self.get_object()
        groups = category.groups.all()
        serializer = PageGroupSerializer(groups, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='toggle-expand')
    def toggle_expand(self, request, pk=None):
        """
        Toggle category expansion state
        POST /api/v1/page-group-categories/{id}/toggle-expand/
        """
        category = self.get_object()
        category.is_expanded = not category.is_expanded
        category.save(update_fields=['is_expanded'])
        return Response({'is_expanded': category.is_expanded})

    @action(detail=False, methods=['post'], url_path='auto-sort')
    @transaction.atomic
    def auto_sort(self, request):
        """
        Auto-sort all categories in a domain by content (page count, then group count)
        POST /api/v1/page-group-categories/auto-sort/
        Body: { "domain": 11 }
        """
        from django.db.models import Count

        domain_id = request.data.get('domain')
        if not domain_id:
            return Response({'error': 'domain parameter required'}, status=status.HTTP_400_BAD_REQUEST)

        # Get all categories with annotated counts (single query instead of N+1)
        categories = PageGroupCategory.objects.filter(
            domain_id=domain_id
        ).annotate(
            group_count=Count('groups', distinct=True),
            page_count=Count('groups__pages', distinct=True)
        ).order_by('-page_count', '-group_count', 'name')

        # Assign order values (10, 20, 30, ...) and collect items to update
        items_to_update = []
        for idx, category in enumerate(categories):
            new_order = (idx + 1) * 10
            if category.order != new_order:
                category.order = new_order
                items_to_update.append(category)

        # Bulk update (single query instead of N)
        updated_count = 0
        if items_to_update:
            PageGroupCategory.objects.bulk_update(
                items_to_update,
                ['order'],
                batch_size=100
            )
            updated_count = len(items_to_update)

        return Response({
            'message': f'Auto-sorted {categories.count()} categories',
            'updated': updated_count
        })


class PageGroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PageGroup
    Supports CRUD operations for managing page groups
    Now supports category assignment
    """
    queryset = PageGroup.objects.all()
    serializer_class = PageGroupSerializer

    def get_queryset(self):
        """Filter by domain and/or category if provided"""
        queryset = super().get_queryset()
        domain_id = self.request.query_params.get('domain', None)
        category_id = self.request.query_params.get('category', None)

        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)
        if category_id:
            if category_id == 'null' or category_id == 'none':
                # For uncategorized groups, don't order by category
                queryset = queryset.filter(category__isnull=True)
                return queryset.order_by('order', 'name')
            else:
                queryset = queryset.filter(category_id=category_id)

        # For categorized groups or no category filter
        return queryset.select_related('category').order_by('category__order', 'order', 'name')

    @action(detail=True, methods=['get'], url_path='pages')
    def pages(self, request, pk=None):
        """
        Get all pages in this group
        GET /api/v1/page-groups/{id}/pages/
        """
        group = self.get_object()
        pages = group.pages.all()
        serializer = PageListSerializer(pages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='reorder')
    def reorder(self, request, pk=None):
        """
        Update group display order
        POST /api/v1/page-groups/{id}/reorder/
        Body: { "order": 5 }
        """
        group = self.get_object()
        new_order = request.data.get('order')
        if new_order is not None:
            group.order = new_order
            group.save(update_fields=['order'])
            return Response({'message': 'Order updated', 'order': group.order})
        return Response({'error': 'Order not provided'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='auto-sort')
    @transaction.atomic
    def auto_sort(self, request):
        """
        Auto-sort groups by content (page count) within a category or domain
        POST /api/v1/page-groups/auto-sort/
        Body: { "category": 2 } or { "domain": 11, "category": null } for uncategorized
        """
        from django.db.models import Count

        domain_id = request.data.get('domain')
        category_id = request.data.get('category')

        if category_id is None and not domain_id:
            return Response({'error': 'Either category or domain parameter required'}, status=status.HTTP_400_BAD_REQUEST)

        # Get groups to sort with annotated page count (single query instead of N+1)
        if category_id:
            groups = PageGroup.objects.filter(category_id=category_id)
        else:
            # Sort uncategorized groups in domain
            groups = PageGroup.objects.filter(domain_id=domain_id, category__isnull=True)

        # Annotate with page count and order by it
        groups = groups.annotate(
            page_count=Count('pages', distinct=True)
        ).order_by('-page_count', 'name')

        # Assign order values (10, 20, 30, ...) and collect items to update
        items_to_update = []
        for idx, group in enumerate(groups):
            new_order = (idx + 1) * 10
            if group.order != new_order:
                group.order = new_order
                items_to_update.append(group)

        # Bulk update (single query instead of N)
        updated_count = 0
        if items_to_update:
            PageGroup.objects.bulk_update(
                items_to_update,
                ['order'],
                batch_size=100
            )
            updated_count = len(items_to_update)

        return Response({
            'message': f'Auto-sorted {groups.count()} groups',
            'updated': updated_count
        })


# ============================================================================
# AI SEO Advisor ViewSets (Day 2)
# ============================================================================

class SEOIssueViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SEO Issues
    Provides CRUD operations and auto-fix functionality
    """
    queryset = SEOIssue.objects.all().select_related('page').order_by('-detected_at')

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == 'list':
            return SEOIssueListSerializer
        return SEOIssueSerializer

    def get_queryset(self):
        """Filter by page, domain, severity, or status"""
        queryset = super().get_queryset()

        page_id = self.request.query_params.get('page_id')  # Changed from 'page' to 'page_id' to avoid pagination conflict
        domain_id = self.request.query_params.get('domain')
        severity = self.request.query_params.get('severity')
        status_param = self.request.query_params.get('status')
        auto_fixable = self.request.query_params.get('auto_fixable')

        if page_id:
            queryset = queryset.filter(page_id=page_id)
        if domain_id:
            queryset = queryset.filter(page__domain_id=domain_id)
        if severity:
            queryset = queryset.filter(severity=severity)
        if status_param:
            queryset = queryset.filter(status=status_param)
        if auto_fixable == 'true':
            queryset = queryset.filter(auto_fix_available=True, status='open')

        return queryset

    @action(detail=True, methods=['post'], url_path='auto-fix')
    @transaction.atomic
    def auto_fix(self, request, pk=None):
        """
        Auto-fix a specific issue (saves to database only)
        POST /api/v1/seo-issues/{id}/auto-fix/
        Note: Use deploy-pending endpoint to deploy fixes to Git
        """
        from seo_analyzer.services.auto_fix_service import AutoFixService

        issue = self.get_object()

        if not issue.auto_fix_available:
            return Response(
                {'error': 'This issue is not auto-fixable'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if issue.status != 'open':
            return Response(
                {'error': f'Issue is already {issue.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Use AutoFixService to fix the issue
            logger.info(f"Auto-fixing issue {issue.id}: {issue.title} (DB only)")

            auto_fix_service = AutoFixService()
            result = auto_fix_service.fix_issue(issue)

            if not result.get('success'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Return response with fix details
            return Response({
                'message': result.get('message'),
                'issue_id': issue.id,
                'method': result.get('method'),
                'old_value': result.get('old_value'),
                'new_value': result.get('new_value'),
                'deployed_to_git': False,  # Not deployed yet
            })

        except Exception as e:
            logger.error(f"Auto-fix failed for issue {issue.id}: {e}", exc_info=True)
            return Response(
                {'error': f'Auto-fix failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='bulk-fix')
    @transaction.atomic
    def bulk_fix(self, request):
        """
        Auto-fix multiple issues at once (saves to database only)
        POST /api/v1/seo-issues/bulk-fix/
        Body: {
            "issue_ids": [1, 2, 3]
        }
        Note: Use deploy-pending endpoint to deploy fixes to Git
        """
        issue_ids = request.data.get('issue_ids', [])

        if not issue_ids:
            return Response(
                {'error': 'No issue IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch all eligible issues at once
        issues = SEOIssue.objects.filter(
            id__in=issue_ids,
            auto_fix_available=True,
            status='open'
        ).select_related('page', 'page__domain')

        if not issues.exists():
            return Response({
                'message': 'No eligible issues found',
                'fixed_count': 0,
                'total_requested': len(issue_ids)
            })

        # Auto-fix each issue
        auto_fix_service = AutoFixService()
        results = []
        fixed_count = 0
        failed_count = 0

        for issue in issues:
            try:
                result = auto_fix_service.fix_issue(issue)
                results.append({
                    'issue_id': issue.id,
                    'issue_type': issue.issue_type,
                    'success': result.get('success'),
                    'message': result.get('message'),
                })

                if result.get('success'):
                    fixed_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                logger.error(f"Bulk auto-fix failed for issue {issue.id}: {e}", exc_info=True)
                results.append({
                    'issue_id': issue.id,
                    'issue_type': issue.issue_type,
                    'success': False,
                    'message': f'Error: {str(e)}',
                })
                failed_count += 1

        return Response({
            'message': f'Auto-fixed {fixed_count} out of {len(issue_ids)} issues (DB only)',
            'fixed_count': fixed_count,
            'failed_count': failed_count,
            'total_requested': len(issue_ids),
            'results': results,
            'deployed_to_git': False,  # Not deployed yet
        })

    @action(detail=True, methods=['patch'], url_path='update-fix')
    @transaction.atomic
    def update_fix_value(self, request, pk=None):
        """
        Update the suggested fix value manually
        PATCH /api/v1/seo-issues/{id}/update-fix/
        Body: {
            "suggested_value": "new value"
        }
        """
        issue = self.get_object()

        if issue.status not in ['auto_fixed', 'fixed']:
            return Response(
                {'error': 'Can only update fix value for fixed issues'},
                status=status.HTTP_400_BAD_REQUEST
            )

        suggested_value = request.data.get('suggested_value')
        if not suggested_value:
            return Response(
                {'error': 'suggested_value is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            old_value = issue.suggested_value
            was_deployed = issue.deployed_to_git

            issue.suggested_value = suggested_value

            # If issue was previously deployed, mark as needing redeployment
            if was_deployed:
                issue.deployed_to_git = False
                issue.deployment_commit_hash = None
                issue.deployed_at = None
                issue.save(update_fields=['suggested_value', 'deployed_to_git', 'deployment_commit_hash', 'deployed_at'])
                logger.info(f"Updated fix value for deployed issue {issue.id}: {old_value} → {suggested_value}. Marked for redeployment.")
            else:
                issue.save(update_fields=['suggested_value'])
                logger.info(f"Updated fix value for issue {issue.id}: {old_value} → {suggested_value}")

            return Response({
                'message': 'Fix value updated successfully',
                'issue_id': issue.id,
                'old_value': old_value,
                'new_value': suggested_value,
                'needs_redeployment': was_deployed,
            })

        except Exception as e:
            logger.error(f"Failed to update fix value for issue {issue.id}: {e}", exc_info=True)
            return Response(
                {'error': f'Update failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='deploy-pending')
    @transaction.atomic
    def deploy_pending_fixes(self, request):
        """
        Deploy all pending fixes to Git (issues that are fixed but not deployed)
        POST /api/v1/seo-issues/deploy-pending/
        Body: {
            "page_id": 123  # Optional: filter by page
        }
        """
        page_id = request.data.get('page_id')

        # Filter fixed but not deployed issues
        queryset = SEOIssue.objects.filter(
            status__in=['auto_fixed', 'fixed'],
            deployed_to_git=False
        ).select_related('page', 'page__domain')

        if page_id:
            queryset = queryset.filter(page_id=page_id)

        pending_issues = list(queryset)

        if not pending_issues:
            return Response({
                'message': 'No pending fixes to deploy',
                'deployed_count': 0
            })

        # Group by domain
        domain_groups = {}
        for issue in pending_issues:
            domain_id = issue.page.domain.id
            if domain_id not in domain_groups:
                domain_groups[domain_id] = {
                    'domain': issue.page.domain,
                    'issues': []
                }
            domain_groups[domain_id]['issues'].append(issue)

        deployment_results = []
        total_deployed = 0

        for domain_id, group in domain_groups.items():
            domain = group['domain']
            issues = group['issues']

            if not domain.git_enabled:
                logger.warning(f"Git not enabled for domain {domain.domain_name}, skipping deployment")
                deployment_results.append({
                    'domain': domain.domain_name,
                    'success': False,
                    'message': 'Git not enabled for this domain',
                    'issues_count': len(issues)
                })
                continue

            # Prepare Git fixes
            git_fixes = []
            for issue in issues:
                field = None
                if 'title' in issue.issue_type:
                    field = 'title'
                elif 'description' in issue.issue_type:
                    field = 'description'

                if field and issue.suggested_value:
                    git_fixes.append({
                        'page_url': issue.page.url,
                        'field': field,
                        'old_value': issue.current_value,
                        'new_value': issue.suggested_value,
                    })

            if not git_fixes:
                logger.warning(f"No Git-deployable fixes for domain {domain.domain_name}")
                deployment_results.append({
                    'domain': domain.domain_name,
                    'success': False,
                    'message': 'No Git-deployable fixes found',
                    'issues_count': len(issues)
                })
                continue

            # Deploy to Git
            try:
                logger.info(f"Deploying {len(git_fixes)} fixes to Git for domain {domain.domain_name}")
                deployer = GitDeployer(domain)
                deployment_result = deployer.deploy_fixes(git_fixes)

                if deployment_result.get('success'):
                    from django.utils import timezone
                    commit_hash = deployment_result.get('commit_hash')
                    deployed_at = timezone.now()

                    # Update deployment status and set verification to pending
                    issue_ids = [issue.id for issue in issues]
                    SEOIssue.objects.filter(id__in=issue_ids).update(
                        deployed_to_git=True,
                        deployed_at=deployed_at,
                        deployment_commit_hash=commit_hash,
                        verification_status='pending'  # 검증 대기 상태로 설정
                    )

                    total_deployed += len(issue_ids)
                    deployment_results.append({
                        'domain': domain.domain_name,
                        'success': True,
                        'commit_hash': commit_hash,
                        'issues_count': len(issues),
                        'message': f'Successfully deployed {len(issues)} fixes'
                    })
                    logger.info(f"Successfully deployed {len(issues)} fixes for domain {domain.domain_name}")
                else:
                    deployment_results.append({
                        'domain': domain.domain_name,
                        'success': False,
                        'message': deployment_result.get('message', 'Deployment failed'),
                        'issues_count': len(issues)
                    })

            except Exception as e:
                logger.error(f"Git deployment failed for domain {domain.domain_name}: {e}", exc_info=True)
                deployment_results.append({
                    'domain': domain.domain_name,
                    'success': False,
                    'message': f'Deployment error: {str(e)}',
                    'issues_count': len(issues)
                })

        return Response({
            'message': f'Deployed {total_deployed} out of {len(pending_issues)} pending fixes',
            'total_pending': len(pending_issues),
            'deployed_count': total_deployed,
            'deployment_results': deployment_results
        })

    @action(detail=True, methods=['post'], url_path='revert')
    @transaction.atomic
    def revert_fix(self, request, pk=None):
        """
        Revert a fixed issue back to open state
        POST /api/v1/seo-issues/{id}/revert/
        Body: {
            "deploy_to_git": true  # Optional: deploy revert to Git repository
        }
        """
        issue = self.get_object()

        if issue.status not in ['auto_fixed', 'fixed']:
            return Response(
                {'error': f'Cannot revert issue with status: {issue.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            logger.info(f"Reverting issue {issue.id}: {issue.title}")

            # Store old values for response
            old_suggested_value = issue.suggested_value
            old_current_value = issue.current_value

            # Revert to open state
            issue.status = 'open'
            issue.fixed_at = None

            # Clear suggested value (keep current value as is)
            if issue.suggested_value:
                issue.suggested_value = None

            issue.save(update_fields=['status', 'fixed_at', 'suggested_value'])

            response_data = {
                'message': f'Issue reverted to open state',
                'issue_id': issue.id,
                'old_status': 'auto_fixed' if issue.status == 'open' else 'fixed',
                'new_status': 'open',
            }

            # Optionally deploy revert to Git
            deploy_to_git = request.data.get('deploy_to_git', False)
            domain = issue.page.domain

            if deploy_to_git and domain.git_enabled and issue.deployed_to_git:
                # Determine field type
                field = None
                if 'title' in issue.issue_type:
                    field = 'title'
                elif 'description' in issue.issue_type:
                    field = 'description'

                if field:
                    try:
                        logger.info(f"Deploying revert for issue {issue.id} to Git")
                        deployer = GitDeployer(domain)
                        git_fixes = [{
                            'page_url': issue.page.url,
                            'field': field,
                            'old_value': old_suggested_value,  # What it was changed to
                            'new_value': old_current_value,  # Revert back to original
                        }]
                        deployment_result = deployer.deploy_fixes(git_fixes)

                        if deployment_result.get('success'):
                            # Clear deployment status since we reverted
                            issue.deployed_to_git = False
                            issue.deployed_at = None
                            issue.deployment_commit_hash = None
                            issue.save(update_fields=['deployed_to_git', 'deployed_at', 'deployment_commit_hash'])

                            response_data['deployment'] = {
                                'success': True,
                                'commit_hash': deployment_result.get('commit_hash'),
                                'message': 'Revert deployed to Git successfully'
                            }
                            logger.info(f"Git revert successful for issue {issue.id}")
                        else:
                            response_data['deployment'] = {
                                'success': False,
                                'message': deployment_result.get('message', 'Git revert failed')
                            }

                    except Exception as deploy_error:
                        logger.error(f"Git revert error for issue {issue.id}: {deploy_error}", exc_info=True)
                        response_data['deployment'] = {
                            'success': False,
                            'message': f'Git revert error: {str(deploy_error)}'
                        }

            return Response(response_data)

        except Exception as e:
            logger.error(f"Revert failed for issue {issue.id}: {e}", exc_info=True)
            return Response(
                {'error': f'Revert failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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

        page_id = self.request.query_params.get('page_id')  # Changed from 'page' to 'page_id' to avoid pagination conflict
        domain_id = self.request.query_params.get('domain')
        report_type = self.request.query_params.get('report_type')

        if page_id:
            queryset = queryset.filter(page_id=page_id)
        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)
        if report_type:
            queryset = queryset.filter(report_type=report_type)

        return queryset


class SitemapConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Sitemap Configuration
    """
    queryset = SitemapConfig.objects.all().select_related('domain').order_by('-created_at')
    serializer_class = SitemapConfigSerializer

    def get_queryset(self):
        """Filter by domain"""
        queryset = super().get_queryset()
        domain_id = self.request.query_params.get('domain')

        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)

        return queryset

    @action(detail=True, methods=['post'], url_path='generate')
    def generate(self, request, pk=None):
        """
        Generate sitemap for this configuration
        POST /api/v1/sitemap-configs/{id}/generate/
        """
        config = self.get_object()

        try:
            from .services import SitemapManager

            manager = SitemapManager()
            result = manager.generate(config.domain)

            if result.get('error'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Create history record
            SitemapHistory.objects.create(
                domain=config.domain,
                url_count=result.get('url_count', 0),
                file_size_bytes=result.get('size_bytes', 0),
                generated=True,
                deployed=False
            )

            # Update config
            config.last_generated_at = datetime.now(timezone.utc)
            config.save()

            return Response({
                'message': 'Sitemap generated successfully',
                'url_count': result.get('url_count'),
                'size_bytes': result.get('size_bytes'),
                'type': result.get('type')
            })

        except Exception as e:
            logger.error(f"Sitemap generation failed: {e}", exc_info=True)
            return Response(
                {'error': f'Generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='deploy')
    def deploy(self, request, pk=None):
        """
        Deploy sitemap using configured method
        POST /api/v1/sitemap-configs/{id}/deploy/
        """
        config = self.get_object()

        try:
            from .services import SitemapManager

            # First generate if not recently generated
            manager = SitemapManager()
            result = manager.generate(config.domain)

            if result.get('error'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Deploy
            deploy_result = manager.deploy(config, result.get('xml_content'))

            if not deploy_result.get('success'):
                return Response(
                    {'error': deploy_result.get('error')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Update config and history
            config.last_deployed_at = datetime.now(timezone.utc)
            config.save()

            SitemapHistory.objects.create(
                domain=config.domain,
                url_count=result.get('url_count', 0),
                file_size_bytes=result.get('size_bytes', 0),
                generated=True,
                deployed=True
            )

            return Response({
                'message': 'Sitemap deployed successfully',
                'method': deploy_result.get('method'),
                'path': deploy_result.get('path')
            })

        except Exception as e:
            logger.error(f"Sitemap deployment failed: {e}", exc_info=True)
            return Response(
                {'error': f'Deployment failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='import')
    def import_sitemap(self, request, pk=None):
        """
        Import existing sitemap from URL
        POST /api/v1/sitemap-configs/{id}/import/
        Body: { "sitemap_url": "https://example.com/sitemap.xml" }
        """
        config = self.get_object()
        sitemap_url = request.data.get('sitemap_url') or config.existing_sitemap_url

        if not sitemap_url:
            return Response(
                {'error': 'Sitemap URL is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from .services import SitemapManager

            manager = SitemapManager()
            result = manager.import_existing_sitemap(sitemap_url, config.domain)

            if result.get('error'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Create history record
            SitemapHistory.objects.create(
                domain=config.domain,
                url_count=result.get('url_count', 0),
                file_size_bytes=0,  # Unknown for imports
                sitemap_url=sitemap_url,
                generated=False,
                deployed=False
            )

            return Response({
                'message': 'Sitemap imported successfully',
                'sitemap_url': sitemap_url,
                'url_count': result.get('url_count'),
                'type': result.get('type')
            })

        except Exception as e:
            logger.error(f"Sitemap import failed: {e}", exc_info=True)
            return Response(
                {'error': f'Import failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SitemapHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Sitemap History (Read-only)
    """
    queryset = SitemapHistory.objects.all().select_related('domain').order_by('-created_at')
    serializer_class = SitemapHistorySerializer

    def get_queryset(self):
        """Filter by domain"""
        queryset = super().get_queryset()
        domain_id = self.request.query_params.get('domain')

        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)

        return queryset
