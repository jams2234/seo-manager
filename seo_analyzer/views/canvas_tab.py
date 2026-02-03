"""
Canvas Tab Views
API endpoints for managing per-domain canvas tabs
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction

from ..models import Domain, CanvasTab
from ..serializers import (
    CanvasTabSerializer,
    CanvasTabCreateSerializer,
    CanvasTabUpdateSerializer,
)


class CanvasTabViewSet(viewsets.ViewSet):
    """
    ViewSet for managing Canvas Tabs within a Domain.

    Canvas tabs allow users to create multiple view configurations
    of the same domain tree. The 'main' tab is read-only and shows
    the actual deployed tree, while custom tabs can be edited.
    """

    def get_domain(self, domain_id):
        """Get domain by ID"""
        return get_object_or_404(Domain, pk=domain_id)

    @action(detail=False, methods=['get'], url_path='domain/(?P<domain_id>[^/.]+)')
    def list_tabs(self, request, domain_id=None):
        """
        List all canvas tabs for a domain.
        Creates main tab if it doesn't exist.
        """
        domain = self.get_domain(domain_id)

        # Ensure main tab exists
        CanvasTab.get_or_create_main_tab(domain)

        tabs = CanvasTab.objects.filter(domain=domain).order_by('order')
        serializer = CanvasTabSerializer(tabs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='domain/(?P<domain_id>[^/.]+)/add')
    def add_tab(self, request, domain_id=None):
        """
        Add a new canvas tab to a domain.
        """
        domain = self.get_domain(domain_id)

        serializer = CanvasTabCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get next order number
        max_order = CanvasTab.objects.filter(domain=domain).order_by('-order').values_list('order', flat=True).first()
        next_order = (max_order or 0) + 1

        # Generate tab name if not provided
        name = serializer.validated_data.get('name') or str(next_order)

        with transaction.atomic():
            # Create new tab
            tab = CanvasTab.objects.create(
                domain=domain,
                name=name,
                is_main=False,
                order=next_order,
                is_active=True,  # New tab becomes active
            )

            # Deactivate other tabs
            CanvasTab.objects.filter(domain=domain).exclude(pk=tab.pk).update(is_active=False)

        return Response(CanvasTabSerializer(tab).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['patch'], url_path='(?P<tab_id>[^/.]+)/update')
    def update_tab(self, request, tab_id=None):
        """
        Update a canvas tab.
        Main tab cannot update custom_positions.
        """
        tab = get_object_or_404(CanvasTab, pk=tab_id)

        serializer = CanvasTabUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        # Update allowed fields
        if 'name' in data and not tab.is_main:
            tab.name = data['name']

        if 'viewport' in data:
            tab.viewport = data['viewport']

        if 'custom_positions' in data:
            if tab.is_main:
                return Response(
                    {'error': 'main 탭은 커스텀 위치를 저장할 수 없습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            tab.custom_positions = data['custom_positions']

        if 'is_active' in data and data['is_active']:
            # Deactivate other tabs
            CanvasTab.objects.filter(domain=tab.domain).exclude(pk=tab.pk).update(is_active=False)
            tab.is_active = True

        tab.save()
        return Response(CanvasTabSerializer(tab).data)

    @action(detail=False, methods=['delete'], url_path='(?P<tab_id>[^/.]+)/delete')
    def delete_tab(self, request, tab_id=None):
        """
        Delete a canvas tab.
        Main tab cannot be deleted.
        """
        tab = get_object_or_404(CanvasTab, pk=tab_id)

        if tab.is_main:
            return Response(
                {'error': 'main 탭은 삭제할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        domain = tab.domain
        was_active = tab.is_active
        tab.delete()

        # If deleted tab was active, activate main tab
        if was_active:
            CanvasTab.objects.filter(domain=domain, is_main=True).update(is_active=True)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], url_path='(?P<tab_id>[^/.]+)/activate')
    def activate_tab(self, request, tab_id=None):
        """
        Activate a canvas tab.
        """
        tab = get_object_or_404(CanvasTab, pk=tab_id)

        with transaction.atomic():
            # Deactivate all tabs for this domain
            CanvasTab.objects.filter(domain=tab.domain).update(is_active=False)
            # Activate this tab
            tab.is_active = True
            tab.save(update_fields=['is_active'])

        return Response(CanvasTabSerializer(tab).data)

    @action(detail=False, methods=['post'], url_path='(?P<tab_id>[^/.]+)/save-positions')
    def save_positions(self, request, tab_id=None):
        """
        Save custom positions for a canvas tab.
        Main tab cannot save positions.
        """
        tab = get_object_or_404(CanvasTab, pk=tab_id)

        if tab.is_main:
            return Response(
                {'error': 'main 탭은 커스텀 위치를 저장할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        positions = request.data.get('positions', {})
        viewport = request.data.get('viewport')

        if positions:
            # Merge with existing positions
            tab.custom_positions.update(positions)

        if viewport:
            tab.viewport = viewport

        tab.save(update_fields=['custom_positions', 'viewport', 'updated_at'])

        return Response(CanvasTabSerializer(tab).data)
