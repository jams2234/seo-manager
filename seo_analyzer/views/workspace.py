"""
Workspace Views
API endpoints for managing tree workspaces and tabs
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count

from ..models import Workspace, WorkspaceTab, Domain
from ..serializers import (
    WorkspaceSerializer,
    WorkspaceListSerializer,
    WorkspaceCreateSerializer,
    WorkspaceTabSerializer,
    WorkspaceTabCreateSerializer,
    WorkspaceTabUpdateSerializer,
    WorkspaceTabReorderSerializer,
)


class WorkspaceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Workspaces

    Endpoints:
    - GET /api/workspaces/ - List all workspaces
    - POST /api/workspaces/ - Create new workspace
    - GET /api/workspaces/{id}/ - Get workspace detail with tabs
    - PUT /api/workspaces/{id}/ - Update workspace
    - DELETE /api/workspaces/{id}/ - Delete workspace
    - POST /api/workspaces/{id}/tabs/ - Add tab to workspace
    - PUT /api/workspaces/{id}/tabs/{tab_id}/ - Update tab
    - DELETE /api/workspaces/{id}/tabs/{tab_id}/ - Remove tab
    - POST /api/workspaces/{id}/tabs/reorder/ - Reorder tabs
    - GET /api/workspaces/default/ - Get or create default workspace
    """
    queryset = Workspace.objects.all()
    serializer_class = WorkspaceSerializer

    def get_queryset(self):
        """Filter by owner if authenticated"""
        queryset = Workspace.objects.annotate(tab_count=Count('tabs'))
        # TODO: Filter by owner when auth is implemented
        # if self.request.user.is_authenticated:
        #     queryset = queryset.filter(owner=self.request.user)
        return queryset.order_by('-updated_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkspaceListSerializer
        if self.action == 'create':
            return WorkspaceCreateSerializer
        return WorkspaceSerializer

    def create(self, request, *args, **kwargs):
        """Create a new workspace with optional initial tabs"""
        serializer = WorkspaceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        # Create workspace
        workspace = Workspace.objects.create(
            name=data['name'],
            description=data.get('description', ''),
            is_default=data.get('is_default', False),
            owner=request.user if request.user.is_authenticated else None,
        )

        # Add initial tabs if provided
        initial_domain_ids = data.get('initial_domain_ids', [])
        for order, domain_id in enumerate(initial_domain_ids):
            try:
                domain = Domain.objects.get(id=domain_id)
                WorkspaceTab.objects.create(
                    workspace=workspace,
                    domain=domain,
                    order=order,
                    is_active=(order == 0),  # First tab is active
                )
            except Domain.DoesNotExist:
                continue

        # Return full workspace data
        response_serializer = WorkspaceSerializer(workspace)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        """Get workspace detail and update last_opened_at"""
        instance = self.get_object()
        instance.last_opened_at = timezone.now()
        instance.save(update_fields=['last_opened_at'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def default(self, request):
        """Get or create default workspace"""
        # Try to find existing default workspace
        workspace = Workspace.objects.filter(is_default=True).first()

        if not workspace:
            # Create default workspace
            workspace = Workspace.objects.create(
                name='기본 워크스페이스',
                description='기본 트리 워크스페이스',
                is_default=True,
                owner=request.user if request.user.is_authenticated else None,
            )

        workspace.last_opened_at = timezone.now()
        workspace.save(update_fields=['last_opened_at'])

        serializer = WorkspaceSerializer(workspace)
        return Response(serializer.data)

    # ==========================================================================
    # Tab Management Actions
    # ==========================================================================

    @action(detail=True, methods=['post'], url_path='tabs')
    def add_tab(self, request, pk=None):
        """Add a new tab to the workspace"""
        workspace = self.get_object()
        serializer = WorkspaceTabCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        domain = get_object_or_404(Domain, id=data['domain_id'])

        # Get next order number
        max_order = workspace.tabs.aggregate(max_order=models.Max('order'))['max_order']
        next_order = (max_order or -1) + 1

        # Create tab
        tab = WorkspaceTab.objects.create(
            workspace=workspace,
            domain=domain,
            name=data.get('name', ''),
            order=next_order,
            is_active=data.get('is_active', True),
        )

        response_serializer = WorkspaceTabSerializer(tab)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['put', 'patch'], url_path='tabs/(?P<tab_id>[^/.]+)')
    def update_tab(self, request, pk=None, tab_id=None):
        """Update a specific tab"""
        workspace = self.get_object()
        tab = get_object_or_404(WorkspaceTab, id=tab_id, workspace=workspace)

        serializer = WorkspaceTabUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        # Update fields
        if 'name' in data:
            tab.name = data['name']
        if 'is_active' in data:
            tab.is_active = data['is_active']
        if 'viewport' in data:
            tab.viewport = data['viewport']
        if 'preferences' in data:
            tab.preferences.update(data['preferences'])
        if 'custom_positions' in data:
            tab.custom_positions.update(data['custom_positions'])
        if 'has_unsaved_changes' in data:
            tab.has_unsaved_changes = data['has_unsaved_changes']

        tab.save()

        response_serializer = WorkspaceTabSerializer(tab)
        return Response(response_serializer.data)

    @action(detail=True, methods=['delete'], url_path='tabs/(?P<tab_id>[^/.]+)/delete')
    def remove_tab(self, request, pk=None, tab_id=None):
        """Remove a tab from the workspace"""
        workspace = self.get_object()
        tab = get_object_or_404(WorkspaceTab, id=tab_id, workspace=workspace)

        was_active = tab.is_active
        tab.delete()

        # If removed tab was active, activate the first remaining tab
        if was_active:
            first_tab = workspace.tabs.first()
            if first_tab:
                first_tab.is_active = True
                first_tab.save(update_fields=['is_active'])

        return Response({'message': '탭이 삭제되었습니다.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='tabs/reorder')
    def reorder_tabs(self, request, pk=None):
        """Reorder tabs in the workspace"""
        workspace = self.get_object()
        serializer = WorkspaceTabReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tab_ids = serializer.validated_data['tab_ids']

        # Update order for each tab
        for order, tab_id in enumerate(tab_ids):
            WorkspaceTab.objects.filter(
                id=tab_id,
                workspace=workspace
            ).update(order=order)

        # Return updated workspace
        workspace.refresh_from_db()
        response_serializer = WorkspaceSerializer(workspace)
        return Response(response_serializer.data)

    @action(detail=True, methods=['post'], url_path='tabs/(?P<tab_id>[^/.]+)/activate')
    def activate_tab(self, request, pk=None, tab_id=None):
        """Activate a specific tab"""
        workspace = self.get_object()
        tab = get_object_or_404(WorkspaceTab, id=tab_id, workspace=workspace)

        # Deactivate all other tabs
        workspace.tabs.exclude(id=tab.id).update(is_active=False)

        # Activate this tab
        tab.is_active = True
        tab.save(update_fields=['is_active'])

        response_serializer = WorkspaceTabSerializer(tab)
        return Response(response_serializer.data)

    @action(detail=True, methods=['post'], url_path='tabs/(?P<tab_id>[^/.]+)/save-positions')
    def save_tab_positions(self, request, pk=None, tab_id=None):
        """Save custom node positions for a tab"""
        workspace = self.get_object()
        tab = get_object_or_404(WorkspaceTab, id=tab_id, workspace=workspace)

        positions = request.data.get('positions', {})

        tab.custom_positions = positions
        tab.has_unsaved_changes = False
        tab.save(update_fields=['custom_positions', 'has_unsaved_changes', 'updated_at'])

        return Response({
            'message': '위치가 저장되었습니다.',
            'saved_count': len(positions)
        })


# Import models for aggregate
from django.db import models
