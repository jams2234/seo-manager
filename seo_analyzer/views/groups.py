"""
Page Group ViewSets
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Count, Avg

from ..models import PageGroup, PageGroupCategory
from ..serializers import (
    PageGroupSerializer,
    PageGroupCategorySerializer,
    PageListSerializer,
)


class PageGroupCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PageGroupCategory
    """
    queryset = PageGroupCategory.objects.all()
    serializer_class = PageGroupCategorySerializer

    def get_queryset(self):
        """Filter by domain if provided, with annotated counts to avoid N+1 queries"""
        queryset = super().get_queryset()
        domain_id = self.request.query_params.get('domain', None)
        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)
        # Add annotations for group_count and page_count to avoid N+1 queries
        queryset = queryset.annotate(
            annotated_group_count=Count('groups', distinct=True),
            annotated_page_count=Count('groups__pages', distinct=True)
        )
        return queryset.order_by('order', 'name')

    @action(detail=True, methods=['post'], url_path='reorder')
    def reorder(self, request, pk=None):
        """
        Update category display order
        POST /api/v1/page-group-categories/{id}/reorder/
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
        Auto-sort all categories in a domain by content
        POST /api/v1/page-group-categories/auto-sort/
        """
        domain_id = request.data.get('domain')
        if not domain_id:
            return Response({'error': 'domain parameter required'}, status=status.HTTP_400_BAD_REQUEST)

        categories = PageGroupCategory.objects.filter(
            domain_id=domain_id
        ).annotate(
            group_count=Count('groups', distinct=True),
            page_count=Count('groups__pages', distinct=True)
        ).order_by('-page_count', '-group_count', 'name')

        items_to_update = []
        for idx, category in enumerate(categories):
            new_order = (idx + 1) * 10
            if category.order != new_order:
                category.order = new_order
                items_to_update.append(category)

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
    """
    queryset = PageGroup.objects.all()
    serializer_class = PageGroupSerializer

    def get_queryset(self):
        """Filter by domain and/or category if provided, with annotated counts"""
        queryset = super().get_queryset()
        domain_id = self.request.query_params.get('domain', None)
        category_id = self.request.query_params.get('category', None)

        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)
        if category_id:
            if category_id == 'null' or category_id == 'none':
                queryset = queryset.filter(category__isnull=True)
                # Add annotations for page_count to avoid N+1 queries
                queryset = queryset.annotate(
                    annotated_page_count=Count('pages', distinct=True),
                    annotated_avg_seo_score=Avg('pages__seo_metrics__seo_score')
                )
                return queryset.order_by('order', 'name')
            else:
                queryset = queryset.filter(category_id=category_id)

        # Add annotations for page_count to avoid N+1 queries
        queryset = queryset.annotate(
            annotated_page_count=Count('pages', distinct=True),
            annotated_avg_seo_score=Avg('pages__seo_metrics__seo_score')
        )
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
        Auto-sort groups by content (page count)
        POST /api/v1/page-groups/auto-sort/
        """
        domain_id = request.data.get('domain')
        category_id = request.data.get('category')

        if category_id is None and not domain_id:
            return Response({'error': 'Either category or domain parameter required'}, status=status.HTTP_400_BAD_REQUEST)

        if category_id:
            groups = PageGroup.objects.filter(category_id=category_id)
        else:
            groups = PageGroup.objects.filter(domain_id=domain_id, category__isnull=True)

        groups = groups.annotate(
            page_count=Count('pages', distinct=True)
        ).order_by('-page_count', 'name')

        items_to_update = []
        for idx, group in enumerate(groups):
            new_order = (idx + 1) * 10
            if group.order != new_order:
                group.order = new_order
                items_to_update.append(group)

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
