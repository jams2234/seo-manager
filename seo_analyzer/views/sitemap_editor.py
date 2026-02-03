"""
Sitemap Editor ViewSets
Provides API endpoints for sitemap editing, sessions, and deployment.
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import (
    Domain,
    SitemapEntry,
    SitemapEditSession,
    SitemapEntryChange,
)
from ..serializers import (
    SitemapEntrySerializer,
    SitemapEntryCreateSerializer,
    SitemapEntryUpdateSerializer,
    SitemapEditSessionSerializer,
    SitemapEditSessionCreateSerializer,
    SitemapEntryChangeSerializer,
    SitemapDeployRequestSerializer,
    SitemapSyncRequestSerializer,
    SitemapValidationResultSerializer,
    SitemapDiffSerializer,
    BulkEntryImportSerializer,
)
from ..services import SitemapEditorService
from ..utils import handle_api_error

logger = logging.getLogger(__name__)


class SitemapEntryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Sitemap Entry CRUD operations.

    Endpoints:
    - GET /api/v1/sitemap-editor/entries/ - List entries
    - POST /api/v1/sitemap-editor/entries/ - Create entry
    - GET /api/v1/sitemap-editor/entries/{id}/ - Get entry
    - PATCH /api/v1/sitemap-editor/entries/{id}/ - Update entry
    - DELETE /api/v1/sitemap-editor/entries/{id}/ - Delete entry
    - POST /api/v1/sitemap-editor/entries/{id}/check-status/ - Check URL status
    """
    queryset = SitemapEntry.objects.all().select_related('domain', 'page').order_by('loc')
    serializer_class = SitemapEntrySerializer

    def get_queryset(self):
        """Filter by domain and other params"""
        queryset = super().get_queryset()
        params = self.request.query_params

        # Filter by domain
        domain_id = params.get('domain')
        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)

        # Filter by status
        entry_status = params.get('status')
        if entry_status:
            queryset = queryset.filter(status=entry_status)

        # Filter by validity
        is_valid = params.get('is_valid')
        if is_valid is not None:
            queryset = queryset.filter(is_valid=is_valid.lower() == 'true')

        # Filter by AI suggested
        ai_suggested = params.get('ai_suggested')
        if ai_suggested is not None:
            queryset = queryset.filter(ai_suggested=ai_suggested.lower() == 'true')

        # Search by URL
        search = params.get('search')
        if search:
            queryset = queryset.filter(loc__icontains=search)

        return queryset

    def create(self, request, *args, **kwargs):
        """Create a new sitemap entry"""
        serializer = SitemapEntryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        domain_id = request.data.get('domain_id')

        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            domain = Domain.objects.get(id=domain_id)
            service = SitemapEditorService()

            result = service.add_entry(
                domain=domain,
                session_id=data['session_id'],
                loc=data['loc'],
                lastmod=data.get('lastmod').isoformat() if data.get('lastmod') else None,
                changefreq=data.get('changefreq'),
                priority=float(data['priority']) if data.get('priority') else None,
                user=request.user if request.user.is_authenticated else None,
            )

            if result.get('error'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(result, status=status.HTTP_201_CREATED)

        except Domain.DoesNotExist:
            return Response(
                {'error': 'Domain not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return handle_api_error(logger, 'create sitemap entry', e)

    def partial_update(self, request, *args, **kwargs):
        """Update a sitemap entry"""
        serializer = SitemapEntryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        entry_id = kwargs.get('pk')

        if not data.get('session_id'):
            return Response(
                {'error': 'session_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            service = SitemapEditorService()

            # Build updates dict
            updates = {}
            if 'loc' in data:
                updates['loc'] = data['loc']
            if 'lastmod' in data:
                updates['lastmod'] = data['lastmod'].isoformat() if data['lastmod'] else None
            if 'changefreq' in data:
                updates['changefreq'] = data['changefreq']
            if 'priority' in data:
                updates['priority'] = float(data['priority']) if data['priority'] else None

            result = service.update_entry(
                entry_id=int(entry_id),
                session_id=data['session_id'],
                updates=updates,
                user=request.user if request.user.is_authenticated else None,
            )

            if result.get('error'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(result)

        except Exception as e:
            return handle_api_error(logger, 'update sitemap entry', e)

    def destroy(self, request, *args, **kwargs):
        """Mark entry for removal"""
        entry_id = kwargs.get('pk')
        session_id = request.data.get('session_id') or request.query_params.get('session_id')

        if not session_id:
            return Response(
                {'error': 'session_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            service = SitemapEditorService()

            result = service.remove_entry(
                entry_id=int(entry_id),
                session_id=int(session_id),
                user=request.user if request.user.is_authenticated else None,
            )

            if result.get('error'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(result)

        except Exception as e:
            return handle_api_error(logger, 'remove sitemap entry', e)

    @action(detail=True, methods=['post'], url_path='check-status')
    def check_status(self, request, pk=None):
        """
        Check HTTP status of entry URL.
        POST /api/v1/sitemap-editor/entries/{id}/check-status/
        """
        try:
            service = SitemapEditorService()
            result = service.check_entry_status(int(pk))

            if result.get('error'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(result)

        except Exception as e:
            return handle_api_error(logger, 'check entry status', e)

    @action(detail=True, methods=['post'], url_path='toggle-ai')
    def toggle_ai(self, request, pk=None):
        """
        Toggle AI analysis enabled for entry.
        POST /api/v1/sitemap-editor/entries/{id}/toggle-ai/
        """
        try:
            entry = SitemapEntry.objects.get(id=pk)
            new_value = request.data.get('enabled')

            if new_value is None:
                entry.ai_analysis_enabled = not entry.ai_analysis_enabled
            else:
                entry.ai_analysis_enabled = bool(new_value)

            entry.save(update_fields=['ai_analysis_enabled'])

            return Response({
                'id': entry.id,
                'loc': entry.loc,
                'ai_analysis_enabled': entry.ai_analysis_enabled,
            })

        except SitemapEntry.DoesNotExist:
            return Response(
                {'error': 'Entry not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return handle_api_error(logger, 'toggle entry AI', e)

    @action(detail=False, methods=['post'], url_path='bulk-toggle-ai')
    def bulk_toggle_ai(self, request):
        """
        Bulk toggle AI analysis enabled for multiple entries.
        POST /api/v1/sitemap-editor/entries/bulk-toggle-ai/
        Body: { entry_ids: [1,2,3], enabled: true }
        """
        try:
            entry_ids = request.data.get('entry_ids', [])
            enabled = request.data.get('enabled', True)

            if not entry_ids:
                return Response(
                    {'error': 'entry_ids is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            updated = SitemapEntry.objects.filter(id__in=entry_ids).update(
                ai_analysis_enabled=enabled
            )

            return Response({
                'updated_count': updated,
                'enabled': enabled,
            })

        except Exception as e:
            return handle_api_error(logger, 'bulk toggle AI', e)


class SitemapEditSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Sitemap Edit Sessions.

    Endpoints:
    - GET /api/v1/sitemap-editor/sessions/ - List sessions
    - POST /api/v1/sitemap-editor/sessions/ - Create session
    - GET /api/v1/sitemap-editor/sessions/{id}/ - Get session
    - DELETE /api/v1/sitemap-editor/sessions/{id}/ - Cancel session
    - POST /api/v1/sitemap-editor/sessions/{id}/preview/ - Generate preview
    - POST /api/v1/sitemap-editor/sessions/{id}/validate/ - Validate session
    - POST /api/v1/sitemap-editor/sessions/{id}/deploy/ - Deploy session
    - GET /api/v1/sitemap-editor/sessions/{id}/diff/ - Get session diff
    - POST /api/v1/sitemap-editor/sessions/{id}/sync/ - Sync from live sitemap
    """
    queryset = SitemapEditSession.objects.all().select_related(
        'domain', 'created_by'
    ).order_by('-created_at')
    serializer_class = SitemapEditSessionSerializer

    def get_queryset(self):
        """Filter by domain and status"""
        queryset = super().get_queryset()
        params = self.request.query_params

        domain_id = params.get('domain')
        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)

        session_status = params.get('status')
        if session_status:
            queryset = queryset.filter(status=session_status)

        return queryset

    def create(self, request, *args, **kwargs):
        """Create a new edit session"""
        serializer = SitemapEditSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            domain = Domain.objects.get(id=data['domain_id'])
            service = SitemapEditorService()

            result = service.create_edit_session(
                domain=domain,
                user=request.user if request.user.is_authenticated else None,
                name=data.get('name'),
            )

            if result.get('error'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(result, status=status.HTTP_201_CREATED)

        except Domain.DoesNotExist:
            return Response(
                {'error': 'Domain not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return handle_api_error(logger, 'create edit session', e)

    def destroy(self, request, *args, **kwargs):
        """Cancel edit session"""
        try:
            session = self.get_object()
            session.status = 'cancelled'
            session.save(update_fields=['status', 'updated_at'])

            return Response({'message': 'Session cancelled'})

        except Exception as e:
            return handle_api_error(logger, 'cancel session', e)

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """
        Generate sitemap XML preview.
        POST /api/v1/sitemap-editor/sessions/{id}/preview/
        """
        try:
            session = self.get_object()
            service = SitemapEditorService()

            result = service.generate_preview_xml(
                domain=session.domain,
                session_id=session.id,
            )

            if result.get('error'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(result)

        except Exception as e:
            return handle_api_error(logger, 'generate preview', e)

    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """
        Validate session entries before deployment.
        POST /api/v1/sitemap-editor/sessions/{id}/validate/
        """
        try:
            service = SitemapEditorService()
            result = service.validate_session(int(pk))

            if result.get('error'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(result)

        except Exception as e:
            return handle_api_error(logger, 'validate session', e)

    @action(detail=True, methods=['post'])
    def deploy(self, request, pk=None):
        """
        Deploy sitemap via Git.
        POST /api/v1/sitemap-editor/sessions/{id}/deploy/
        """
        commit_message = request.data.get('commit_message')

        try:
            service = SitemapEditorService()
            result = service.deploy_session(
                session_id=int(pk),
                commit_message=commit_message,
            )

            if result.get('error'):
                return Response(
                    {'error': result.get('message'), 'issues': result.get('issues', [])},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(result)

        except Exception as e:
            return handle_api_error(logger, 'deploy session', e)

    @action(detail=True, methods=['get'])
    def diff(self, request, pk=None):
        """
        Get session change diff.
        GET /api/v1/sitemap-editor/sessions/{id}/diff/
        """
        try:
            service = SitemapEditorService()
            result = service.get_session_diff(int(pk))

            if result.get('error'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(result)

        except Exception as e:
            return handle_api_error(logger, 'get session diff', e)

    @action(detail=False, methods=['post'], url_path='link-pages')
    def link_pages(self, request):
        """
        Link existing sitemap entries to matching Page records.
        POST /api/v1/sitemap-editor/sessions/link-pages/

        Useful for entries created before auto-linking was added.
        """
        domain_id = request.data.get('domain_id')

        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            domain = Domain.objects.get(id=domain_id)
            service = SitemapEditorService()

            result = service.link_entries_to_pages(domain)

            if result.get('error'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(result)

        except Domain.DoesNotExist:
            return Response(
                {'error': 'Domain not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return handle_api_error(logger, 'link entries to pages', e)

    @action(detail=False, methods=['post'])
    def sync(self, request):
        """
        Sync entries from live sitemap or existing pages to database.
        POST /api/v1/sitemap-editor/sessions/sync/

        If sitemap_url fails, automatically falls back to existing pages.
        Set source='pages' to explicitly sync from existing pages.
        """
        serializer = SitemapSyncRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            domain = Domain.objects.get(id=data['domain_id'])
            service = SitemapEditorService()
            user = request.user if request.user.is_authenticated else None

            # Check if explicitly requesting pages sync
            source = request.data.get('source', 'sitemap')

            if source == 'pages':
                # Explicitly sync from existing pages
                result = service.populate_from_pages(domain=domain, user=user)
            else:
                # Try sitemap first
                result = service.sync_entries_from_sitemap(
                    domain=domain,
                    sitemap_url=data.get('sitemap_url'),
                    user=user,
                )

                # If sitemap failed, fallback to pages
                if result.get('error'):
                    logger.info(f"Sitemap sync failed, falling back to pages: {result.get('message')}")
                    result = service.populate_from_pages(domain=domain, user=user)
                    if not result.get('error'):
                        result['fallback'] = True
                        result['fallback_reason'] = 'Sitemap not available, populated from existing pages'

            if result.get('error'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(result)

        except Domain.DoesNotExist:
            return Response(
                {'error': 'Domain not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return handle_api_error(logger, 'sync from sitemap', e)

    @action(detail=True, methods=['post'], url_path='bulk-import')
    def bulk_import(self, request, pk=None):
        """
        Bulk import entries to session.
        POST /api/v1/sitemap-editor/sessions/{id}/bulk-import/
        """
        serializer = BulkEntryImportSerializer(data={
            'session_id': pk,
            'entries': request.data.get('entries', [])
        })
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            session = self.get_object()
            service = SitemapEditorService()

            results = {
                'created': 0,
                'errors': [],
            }

            for entry_data in data['entries']:
                result = service.add_entry(
                    domain=session.domain,
                    session_id=session.id,
                    loc=entry_data.get('loc'),
                    lastmod=entry_data.get('lastmod'),
                    changefreq=entry_data.get('changefreq'),
                    priority=entry_data.get('priority'),
                    user=request.user if request.user.is_authenticated else None,
                    source='bulk_import',
                )

                if result.get('error'):
                    results['errors'].append({
                        'loc': entry_data.get('loc'),
                        'error': result.get('message')
                    })
                else:
                    results['created'] += 1

            return Response({
                'message': f"Imported {results['created']} entries",
                'created': results['created'],
                'errors': results['errors'],
            })

        except Exception as e:
            return handle_api_error(logger, 'bulk import', e)


class SitemapEntryChangeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing entry change history (read-only).

    Endpoints:
    - GET /api/v1/sitemap-editor/changes/ - List changes
    - GET /api/v1/sitemap-editor/changes/{id}/ - Get change detail
    """
    queryset = SitemapEntryChange.objects.all().select_related(
        'session', 'entry', 'changed_by'
    ).order_by('-created_at')
    serializer_class = SitemapEntryChangeSerializer

    def get_queryset(self):
        """Filter by session and entry"""
        queryset = super().get_queryset()
        params = self.request.query_params

        session_id = params.get('session')
        if session_id:
            queryset = queryset.filter(session_id=session_id)

        entry_id = params.get('entry')
        if entry_id:
            queryset = queryset.filter(entry_id=entry_id)

        change_type = params.get('change_type')
        if change_type:
            queryset = queryset.filter(change_type=change_type)

        return queryset
