"""
Sitemap AI Analysis ViewSets
Provides API endpoints for AI-powered sitemap and SEO analysis.
"""
import logging
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Domain, Page, SitemapEntry, SEOIssue, AIConversation, AIMessage, AIFixHistory
from ..services import SitemapAIAnalyzerService
from ..services.claude_client import ClaudeAPIClient
from ..services.ai_auto_fixer import AIAutoFixer
from ..serializers import (
    AIConversationSerializer,
    AIConversationListSerializer,
    AIConversationCreateSerializer,
    AIChatRequestSerializer,
    AIMessageSerializer,
)
from ..utils import handle_api_error

logger = logging.getLogger(__name__)


class SitemapAIViewSet(viewsets.ViewSet):
    """
    ViewSet for AI-powered sitemap analysis.

    Endpoints:
    - POST /api/v1/sitemap-ai/analyze/ - Analyze domain sitemap
    - GET /api/v1/sitemap-ai/suggestions/{entry_id}/ - Get entry suggestions
    - POST /api/v1/sitemap-ai/apply-suggestions/ - Apply AI suggestions
    - POST /api/v1/sitemap-ai/issues/ - Analyze SEO issues
    - POST /api/v1/sitemap-ai/report/ - Generate full report
    """

    @action(detail=False, methods=['post'])
    def analyze(self, request):
        """
        Analyze sitemap entries for a domain using AI.
        POST /api/v1/sitemap-ai/analyze/

        Request body:
        {
            "domain_id": 1
        }
        """
        domain_id = request.data.get('domain_id')

        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            domain = Domain.objects.get(id=domain_id)
            service = SitemapAIAnalyzerService()

            result = service.analyze_domain_sitemap(domain)

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
            return handle_api_error(logger, 'AI sitemap analysis', e)

    @action(detail=False, methods=['get'], url_path='suggestions/(?P<entry_id>[^/.]+)')
    def suggestions(self, request, entry_id=None):
        """
        Get AI suggestions for a specific sitemap entry.
        GET /api/v1/sitemap-ai/suggestions/{entry_id}/
        """
        include_metrics = request.query_params.get('include_metrics', 'true').lower() == 'true'

        try:
            service = SitemapAIAnalyzerService()
            result = service.get_entry_suggestions(
                entry_id=int(entry_id),
                include_metrics=include_metrics
            )

            if result.get('error'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(result)

        except Exception as e:
            return handle_api_error(logger, 'get entry suggestions', e)

    @action(detail=False, methods=['post'], url_path='apply-suggestions')
    def apply_suggestions(self, request):
        """
        Apply AI suggestions to sitemap entries.
        POST /api/v1/sitemap-ai/apply-suggestions/

        Request body:
        {
            "domain_id": 1,
            "session_id": 1,
            "suggestions": [
                {
                    "entry_id": 1,
                    "priority": 0.8,
                    "changefreq": "weekly",
                    "reason": "High traffic page"
                }
            ]
        }
        """
        domain_id = request.data.get('domain_id')
        session_id = request.data.get('session_id')
        suggestions = request.data.get('suggestions', [])

        if not all([domain_id, session_id, suggestions]):
            return Response(
                {'error': 'domain_id, session_id, and suggestions are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            domain = Domain.objects.get(id=domain_id)
            service = SitemapAIAnalyzerService()

            result = service.apply_ai_suggestions(
                domain=domain,
                session_id=int(session_id),
                suggestions=suggestions,
                user=request.user if request.user.is_authenticated else None
            )

            if result.get('error'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(result)

        except Domain.DoesNotExist:
            return Response(
                {'error': 'Domain not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return handle_api_error(logger, 'apply AI suggestions', e)

    @action(detail=False, methods=['post'])
    def issues(self, request):
        """
        Analyze SEO issues for a domain using AI.
        POST /api/v1/sitemap-ai/issues/

        Request body:
        {
            "domain_id": 1
        }
        """
        domain_id = request.data.get('domain_id')

        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            domain = Domain.objects.get(id=domain_id)
            service = SitemapAIAnalyzerService()

            result = service.analyze_seo_issues(domain)

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
            return handle_api_error(logger, 'AI SEO issues analysis', e)

    @action(detail=False, methods=['post'])
    def report(self, request):
        """
        Generate comprehensive AI analysis report for a domain.
        POST /api/v1/sitemap-ai/report/

        Request body:
        {
            "domain_id": 1
        }
        """
        domain_id = request.data.get('domain_id')

        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            domain = Domain.objects.get(id=domain_id)
            service = SitemapAIAnalyzerService()

            result = service.generate_full_report(domain)

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
            return handle_api_error(logger, 'generate AI report', e)

    @action(detail=False, methods=['get'], url_path='domain-knowledge/(?P<domain_id>[^/.]+)')
    def domain_knowledge(self, request, domain_id=None):
        """
        Get structured SEO knowledge context for a domain.
        GET /api/v1/sitemap-ai/domain-knowledge/{domain_id}/

        Returns semantic analysis of domain's SEO structure.
        """
        try:
            from ..models import Domain
            from ..services.seo_knowledge_builder import SEOKnowledgeBuilder

            domain = Domain.objects.get(id=domain_id)
            builder = SEOKnowledgeBuilder(domain)

            return Response({
                'domain_id': int(domain_id),
                'knowledge': builder.build_full_context(),
            })

        except Domain.DoesNotExist:
            return Response(
                {'error': 'Domain not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return handle_api_error(logger, 'get domain knowledge', e)

    @action(detail=False, methods=['get'], url_path='node-analysis/(?P<page_id>[^/.]+)')
    def node_analysis(self, request, page_id=None):
        """
        Get AI-ready analysis context for a specific page/node.
        GET /api/v1/sitemap-ai/node-analysis/{page_id}/

        Returns structured analysis for the web tree node.
        """
        try:
            from ..models import Page
            from ..services.seo_knowledge_builder import SEOKnowledgeBuilder

            page = Page.objects.select_related('domain').get(id=page_id)
            builder = SEOKnowledgeBuilder(page.domain)

            return Response({
                'page_id': int(page_id),
                'analysis': builder.build_node_context(page),
            })

        except Page.DoesNotExist:
            return Response(
                {'error': 'Page not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return handle_api_error(logger, 'get node analysis', e)

    @action(detail=False, methods=['post'], url_path='auto-fix/generate')
    def auto_fix_generate(self, request):
        """
        Generate AI fix for a single SEO issue.
        POST /api/v1/sitemap-ai/auto-fix/generate/

        Request body:
        {
            "issue_id": 1,
            "fetch_live": true  // optional, default true
        }
        """
        issue_id = request.data.get('issue_id')
        fetch_live = request.data.get('fetch_live', True)

        if not issue_id:
            return Response(
                {'error': 'issue_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            issue = SEOIssue.objects.select_related('page', 'page__domain').get(id=issue_id)
            fixer = AIAutoFixer()

            # Check if issue type is supported
            if not fixer.can_fix(issue.issue_type):
                return Response({
                    'success': False,
                    'error': f'Issue type "{issue.issue_type}" is not supported for AI fix',
                    'supported_types': fixer.SUPPORTED_ISSUE_TYPES,
                })

            # Build page context
            page_context = fixer.build_page_context(issue.page, fetch_live=fetch_live)

            # Add content snippet from live data or existing
            if page_context.get('live', {}).get('seo_elements'):
                page_context['content_snippet'] = page_context['live'].get('text_content', '')[:500]
                # Extract keyword strings from top_queries (which are dicts with 'query' key)
                top_queries = page_context.get('db_metrics', {}).get('top_queries', [])
                if top_queries and isinstance(top_queries[0], dict):
                    page_context['keywords'] = [q.get('query', '') for q in top_queries if q.get('query')]
                else:
                    page_context['keywords'] = top_queries if top_queries else []

            # Build domain context
            domain_context = {
                'brand_name': issue.page.domain.domain_name.split('.')[0].title(),
            }

            # Generate fix
            issue_data = {
                'issue_type': issue.issue_type,
                'current_value': issue.current_value,
            }
            result = fixer.generate_fix(issue_data, page_context, domain_context)

            if result.get('success'):
                return Response({
                    'success': True,
                    'issue_id': issue_id,
                    'issue_type': issue.issue_type,
                    'current_value': issue.current_value,
                    'suggested_value': result.get('suggested_value'),
                    'explanation': result.get('explanation'),
                    'confidence': result.get('confidence'),
                    'metadata': result.get('metadata', {}),
                    'page_context': {
                        'url': page_context.get('url'),
                        'title': page_context.get('title'),
                        'fetch_method': page_context.get('live', {}).get('fetch_method'),
                    }
                })
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except SEOIssue.DoesNotExist:
            return Response(
                {'error': 'Issue not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return handle_api_error(logger, 'generate AI fix', e)

    @action(detail=False, methods=['post'], url_path='auto-fix/batch')
    def auto_fix_batch(self, request):
        """
        Generate AI fixes for multiple issues on the same page.
        POST /api/v1/sitemap-ai/auto-fix/batch/

        Request body:
        {
            "page_id": 1,
            "issue_ids": [1, 2, 3],  // optional - if not provided, all open issues for page
            "fetch_live": true
        }
        """
        page_id = request.data.get('page_id')
        issue_ids = request.data.get('issue_ids')
        fetch_live = request.data.get('fetch_live', True)

        if not page_id:
            return Response(
                {'error': 'page_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            page = Page.objects.select_related('domain').get(id=page_id)
            fixer = AIAutoFixer()

            # Get issues
            if issue_ids:
                issues = SEOIssue.objects.filter(
                    id__in=issue_ids,
                    page=page,
                    status='open'
                )
            else:
                issues = SEOIssue.objects.filter(
                    page=page,
                    status='open'
                )

            # Filter to supported issues
            issues_list = [
                {'id': i.id, 'issue_type': i.issue_type, 'current_value': i.current_value}
                for i in issues if fixer.can_fix(i.issue_type)
            ]

            if not issues_list:
                return Response({
                    'success': True,
                    'fixes': [],
                    'message': 'No supported issues found for AI fix',
                })

            # Build page context
            page_context = fixer.build_page_context(page, fetch_live=fetch_live)
            if page_context.get('live', {}).get('seo_elements'):
                page_context['content_snippet'] = page_context['live'].get('text_content', '')[:500]
                # Extract keyword strings from top_queries (which are dicts with 'query' key)
                top_queries = page_context.get('db_metrics', {}).get('top_queries', [])
                if top_queries and isinstance(top_queries[0], dict):
                    page_context['keywords'] = [q.get('query', '') for q in top_queries if q.get('query')]
                else:
                    page_context['keywords'] = top_queries if top_queries else []

            domain_context = {
                'brand_name': page.domain.domain_name.split('.')[0].title(),
            }

            # Generate batch fixes
            result = fixer.generate_batch_fixes(issues_list, page_context, domain_context)

            return Response({
                'success': result.get('success', False),
                'page_id': page_id,
                'page_url': page.url,
                'fixes': result.get('fixes', []),
                'overall_explanation': result.get('overall_explanation', ''),
                'issues_processed': len(issues_list),
            })

        except Page.DoesNotExist:
            return Response(
                {'error': 'Page not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return handle_api_error(logger, 'batch AI fix', e)

    @action(detail=False, methods=['post'], url_path='auto-fix/apply')
    def auto_fix_apply(self, request):
        """
        Apply an AI-generated fix to an issue.
        POST /api/v1/sitemap-ai/auto-fix/apply/

        Request body:
        {
            "issue_id": 1,
            "suggested_value": "New title here",
            "confidence": 0.9,
            "explanation": "AI explanation"
        }

        This also records the fix in AIFixHistory for future reference.
        """
        issue_id = request.data.get('issue_id')
        suggested_value = request.data.get('suggested_value')
        confidence = request.data.get('confidence')
        explanation = request.data.get('explanation')

        if not issue_id or not suggested_value:
            return Response(
                {'error': 'issue_id and suggested_value are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            issue = SEOIssue.objects.select_related('page', 'page__domain').get(id=issue_id)
            fixer = AIAutoFixer()

            # Build page context for history recording
            page_context = fixer.build_page_context(issue.page, fetch_live=False)

            # Apply fix using AIAutoFixer (records history)
            result = fixer.apply_fix(
                issue_id=issue_id,
                suggested_value=suggested_value,
                ai_explanation=explanation,
                ai_confidence=confidence,
                page_context=page_context,
            )

            if result.get('success'):
                # Reload issue to get updated values
                issue.refresh_from_db()

                return Response({
                    'success': True,
                    'issue_id': issue_id,
                    'fix_history_id': result.get('fix_history_id'),
                    'message': 'AI fix applied and recorded to history',
                    'issue': {
                        'id': issue.id,
                        'issue_type': issue.issue_type,
                        'current_value': issue.current_value,
                        'suggested_value': issue.suggested_value,
                        'ai_fix_generated': issue.ai_fix_generated,
                        'ai_fix_confidence': issue.ai_fix_confidence,
                    }
                })
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except SEOIssue.DoesNotExist:
            return Response(
                {'error': 'Issue not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return handle_api_error(logger, 'apply AI fix', e)

    @action(detail=False, methods=['get'], url_path='auto-fix/supported-types')
    def auto_fix_supported_types(self, request):
        """
        Get list of issue types supported for AI auto-fix.
        GET /api/v1/sitemap-ai/auto-fix/supported-types/
        """
        fixer = AIAutoFixer()
        return Response({
            'supported_types': fixer.SUPPORTED_ISSUE_TYPES,
            'descriptions': {
                'title_too_short': '제목이 너무 짧음 (50자 미만)',
                'title_too_long': '제목이 너무 김 (60자 초과)',
                'title_missing': '제목 태그 없음',
                'meta_description_too_short': '메타 설명이 너무 짧음 (120자 미만)',
                'meta_description_too_long': '메타 설명이 너무 김 (160자 초과)',
                'meta_description_missing': '메타 설명 없음',
                'h1_missing': 'H1 태그 없음',
                'h1_multiple': 'H1 태그가 여러 개',
                'low_word_count': '콘텐츠 단어 수 부족',
                'missing_alt_text': '이미지 alt 텍스트 없음',
            }
        })

    @action(detail=False, methods=['post'], url_path='auto-fix/fetch-page')
    def auto_fix_fetch_page(self, request):
        """
        Fetch live page content for analysis.
        POST /api/v1/sitemap-ai/auto-fix/fetch-page/

        Request body:
        {
            "url": "https://example.com/page",
            "use_js_rendering": false
        }
        """
        url = request.data.get('url')
        use_js_rendering = request.data.get('use_js_rendering', False)

        if not url:
            return Response(
                {'error': 'url is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            fixer = AIAutoFixer()
            result = fixer.fetch_page_content(url, use_js_rendering=use_js_rendering)

            if result.get('success'):
                # Don't return full HTML to reduce response size
                return Response({
                    'success': True,
                    'url': url,
                    'method': result.get('method'),
                    'seo_elements': result.get('seo_elements', {}),
                    'text_content_preview': result.get('text_content', '')[:500],
                    'status_code': result.get('status_code'),
                })
            else:
                return Response({
                    'success': False,
                    'error': result.get('error'),
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return handle_api_error(logger, 'fetch page', e)

    @action(detail=False, methods=['get'], url_path='fix-history')
    def fix_history(self, request):
        """
        Get AI fix history for a page.
        GET /api/v1/sitemap-ai/fix-history/?page_id=1&issue_type=title_too_short

        Query params:
        - page_id: Required - Page ID to get history for
        - issue_type: Optional - Filter by issue type
        - limit: Optional - Number of records (default 20)
        """
        from ..models import AIFixHistory

        page_id = request.query_params.get('page_id')
        issue_type = request.query_params.get('issue_type')
        limit = int(request.query_params.get('limit', 20))

        if not page_id:
            return Response(
                {'error': 'page_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            page = Page.objects.get(id=page_id)

            qs = AIFixHistory.objects.filter(page=page)
            if issue_type:
                qs = qs.filter(issue_type=issue_type)

            history = qs.order_by('-created_at')[:limit]

            # Summary stats
            total_fixes = AIFixHistory.objects.filter(page=page).count()
            effective_fixes = AIFixHistory.objects.filter(
                page=page, effectiveness='effective'
            ).count()
            recurred_fixes = AIFixHistory.objects.filter(
                page=page, issue_recurred=True
            ).count()

            return Response({
                'success': True,
                'page_id': page_id,
                'page_url': page.url,
                'summary': {
                    'total_fixes': total_fixes,
                    'effective_fixes': effective_fixes,
                    'recurred_fixes': recurred_fixes,
                    'effectiveness_rate': round(effective_fixes / total_fixes * 100, 1) if total_fixes > 0 else 0,
                },
                'history': [
                    {
                        'id': h.id,
                        'issue_type': h.issue_type,
                        'original_value': h.original_value,
                        'fixed_value': h.fixed_value,
                        'ai_explanation': h.ai_explanation,
                        'ai_confidence': h.ai_confidence,
                        'fix_status': h.fix_status,
                        'effectiveness': h.effectiveness,
                        'issue_recurred': h.issue_recurred,
                        'recurrence_count': h.recurrence_count,
                        'deployed_to_git': h.deployed_to_git,
                        'created_at': h.created_at.isoformat(),
                        'pre_fix_metrics': h.pre_fix_metrics,
                        'post_fix_metrics': h.post_fix_metrics,
                    }
                    for h in history
                ]
            })

        except Page.DoesNotExist:
            return Response(
                {'error': 'Page not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return handle_api_error(logger, 'get fix history', e)

    @action(detail=False, methods=['post'], url_path='fix-history/evaluate')
    def evaluate_fix_effectiveness(self, request):
        """
        Evaluate the effectiveness of a fix based on post-fix metrics.
        POST /api/v1/sitemap-ai/fix-history/evaluate/

        Request body:
        {
            "fix_history_id": 1,
            "effectiveness": "effective|partial|ineffective|negative",
            "post_fix_metrics": {...}
        }
        """
        from ..models import AIFixHistory

        fix_history_id = request.data.get('fix_history_id')
        effectiveness = request.data.get('effectiveness')
        post_fix_metrics = request.data.get('post_fix_metrics', {})

        if not fix_history_id or not effectiveness:
            return Response(
                {'error': 'fix_history_id and effectiveness are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_effectiveness = ['effective', 'partial', 'ineffective', 'negative']
        if effectiveness not in valid_effectiveness:
            return Response(
                {'error': f'effectiveness must be one of: {valid_effectiveness}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            fix_history = AIFixHistory.objects.get(id=fix_history_id)

            fix_history.effectiveness = effectiveness
            fix_history.effectiveness_evaluated_at = timezone.now()
            if post_fix_metrics:
                fix_history.post_fix_metrics = post_fix_metrics

            fix_history.save(update_fields=[
                'effectiveness', 'effectiveness_evaluated_at', 'post_fix_metrics'
            ])

            return Response({
                'success': True,
                'fix_history_id': fix_history_id,
                'effectiveness': effectiveness,
                'message': 'Fix effectiveness evaluated successfully',
            })

        except AIFixHistory.DoesNotExist:
            return Response(
                {'error': 'Fix history not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return handle_api_error(logger, 'evaluate fix effectiveness', e)


class AIConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AI Conversations.

    Endpoints:
    - GET /api/v1/ai-chat/conversations/ - List conversations
    - POST /api/v1/ai-chat/conversations/ - Create conversation
    - GET /api/v1/ai-chat/conversations/{id}/ - Get conversation with messages
    - DELETE /api/v1/ai-chat/conversations/{id}/ - Delete conversation
    - POST /api/v1/ai-chat/conversations/{id}/send/ - Send message
    - POST /api/v1/ai-chat/conversations/{id}/analyze/ - Run analysis in conversation
    """
    queryset = AIConversation.objects.all()
    serializer_class = AIConversationSerializer

    def get_queryset(self):
        """Filter conversations by domain or user"""
        queryset = super().get_queryset()
        params = self.request.query_params

        # Filter by domain
        domain_id = params.get('domain')
        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)

        # Filter by status
        conv_status = params.get('status')
        if conv_status:
            queryset = queryset.filter(status=conv_status)

        # Filter by type
        conv_type = params.get('type')
        if conv_type:
            queryset = queryset.filter(conversation_type=conv_type)

        return queryset.select_related('domain')

    def get_serializer_class(self):
        if self.action == 'list':
            return AIConversationListSerializer
        if self.action == 'create':
            return AIConversationCreateSerializer
        return AIConversationSerializer

    def create(self, request, *args, **kwargs):
        """Create a new AI conversation"""
        serializer = AIConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        domain_id = data.get('domain_id')

        try:
            domain = None
            if domain_id:
                domain = Domain.objects.get(id=domain_id)

            conversation = AIConversation.objects.create(
                domain=domain,
                conversation_type=data.get('conversation_type', 'general'),
                title=data.get('title', ''),
                created_by=request.user if request.user.is_authenticated else None,
            )

            # Add initial message if provided
            initial_message = data.get('initial_message')
            if initial_message:
                AIMessage.objects.create(
                    conversation=conversation,
                    role='user',
                    content=initial_message,
                )
                conversation.total_messages = 1
                conversation.last_message_at = timezone.now()
                conversation.save()

            result_serializer = AIConversationSerializer(conversation)
            return Response(result_serializer.data, status=status.HTTP_201_CREATED)

        except Domain.DoesNotExist:
            return Response(
                {'error': 'Domain not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return handle_api_error(logger, 'create conversation', e)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """
        Send a message and get AI response.
        POST /api/v1/ai-chat/conversations/{id}/send/
        """
        conversation = self.get_object()
        message_content = request.data.get('message', '').strip()

        if not message_content:
            return Response(
                {'error': 'Message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Save user message
            logger.info(f"Creating user message for conversation {conversation.id}")
            user_message = AIMessage.objects.create(
                conversation=conversation,
                role='user',
                content=message_content,
            )

            # Get AI response
            logger.info("Building system prompt...")
            client = ClaudeAPIClient()
            system_prompt = self._get_system_prompt(conversation)
            logger.info(f"System prompt length: {len(system_prompt)}")

            # Include conversation history
            messages_for_ai = []
            for msg in conversation.messages.order_by('created_at'):
                if msg.role in ['user', 'assistant']:
                    messages_for_ai.append({
                        'role': msg.role,
                        'content': msg.content
                    })
            logger.info(f"Messages for AI: {len(messages_for_ai)}")

            # Call Claude API (disable cache for conversations)
            logger.info("Calling Claude API...")
            result = client.chat(
                messages=messages_for_ai,
                system=system_prompt,
                use_cache=False
            )
            logger.info(f"Claude API result success: {result.get('success')}")

            if not result.get('success'):
                logger.error(f"Claude API failed: {result.get('error')}")
                return Response(
                    {'error': result.get('error', 'AI response failed')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Save assistant response
            logger.info("Saving assistant message...")
            assistant_message = AIMessage.objects.create(
                conversation=conversation,
                role='assistant',
                content=result.get('response', ''),
                input_tokens=result.get('usage', {}).get('input_tokens', 0),
                output_tokens=result.get('usage', {}).get('output_tokens', 0),
            )

            # Update conversation stats
            conversation.total_messages = conversation.messages.count()
            conversation.total_tokens_used += (
                assistant_message.input_tokens + assistant_message.output_tokens
            )
            conversation.last_message_at = timezone.now()
            conversation.save()
            logger.info("Response saved successfully")

            return Response({
                'user_message': AIMessageSerializer(user_message).data,
                'assistant_message': AIMessageSerializer(assistant_message).data,
                'conversation': AIConversationSerializer(conversation).data,
            })

        except Exception as e:
            logger.error(f"Send message error: {e}", exc_info=True)
            return handle_api_error(logger, 'send message', e)

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        """
        Run analysis and save results to conversation.
        POST /api/v1/ai-chat/conversations/{id}/analyze/
        """
        conversation = self.get_object()
        analysis_type = request.data.get('analysis_type', 'sitemap')

        if not conversation.domain:
            return Response(
                {'error': 'Conversation must have a domain for analysis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            service = SitemapAIAnalyzerService()

            # Add system message about analysis start
            AIMessage.objects.create(
                conversation=conversation,
                role='system',
                message_type='text',
                content=f'{analysis_type} 분석을 시작합니다...',
            )

            # Run analysis based on type
            if analysis_type == 'sitemap':
                result = service.analyze_domain_sitemap(conversation.domain)
            elif analysis_type == 'seo_issues':
                result = service.analyze_seo_issues(conversation.domain)
            elif analysis_type == 'full_report':
                result = service.generate_full_report(conversation.domain)
            else:
                return Response(
                    {'error': f'Unknown analysis type: {analysis_type}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if result.get('error'):
                # Save error message
                AIMessage.objects.create(
                    conversation=conversation,
                    role='assistant',
                    message_type='error',
                    content=f"분석 실패: {result.get('message')}",
                )
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Format analysis result as message
            analysis_data = result.get('analysis', result.get('report', result))
            summary = ''

            if isinstance(analysis_data, dict):
                summary = analysis_data.get('summary', '')
                if not summary and 'executive_summary' in analysis_data:
                    summary = analysis_data.get('executive_summary', '')

            # Save analysis result as assistant message
            assistant_message = AIMessage.objects.create(
                conversation=conversation,
                role='assistant',
                message_type='analysis',
                content=summary or f'{analysis_type} 분석이 완료되었습니다.',
                structured_data=analysis_data,
            )

            # Update conversation
            conversation.total_messages = conversation.messages.count()
            conversation.last_message_at = timezone.now()
            conversation.save()

            return Response({
                'analysis': analysis_data,
                'message': AIMessageSerializer(assistant_message).data,
                'conversation': AIConversationSerializer(conversation).data,
            })

        except Exception as e:
            return handle_api_error(logger, 'run analysis', e)

    def _build_conversation_context(self, conversation):
        """
        Build context string from domain data using SEO Knowledge Builder.

        Uses structured knowledge representation for richer AI context.
        """
        if not conversation.domain:
            return ""

        domain = conversation.domain

        try:
            # Use SEO Knowledge Builder for structured context
            from ..services.seo_knowledge_builder import SEOKnowledgeBuilder
            builder = SEOKnowledgeBuilder(domain)

            # Get full AI-friendly context
            context = builder.to_ai_context()

            # Add selected URLs for analysis
            from ..models import SitemapEntry
            entries = SitemapEntry.objects.filter(
                domain=domain,
                ai_analysis_enabled=True
            ).values('loc', 'priority', 'changefreq', 'lastmod', 'is_valid', 'http_status_code')[:50]

            if entries:
                context += f"\n\n=== AI 분석 대상 URL ({len(entries)}개) ===\n"
                for entry in entries:
                    lastmod_str = entry['lastmod'].isoformat() if entry['lastmod'] else 'N/A'
                    context += (
                        f"- {entry['loc']} (priority: {entry['priority']}, "
                        f"changefreq: {entry['changefreq']}, lastmod: {lastmod_str}, "
                        f"status: {entry['http_status_code'] or 'N/A'})\n"
                    )

            # Add previous analysis context
            analysis_messages = conversation.messages.filter(
                message_type='analysis'
            ).order_by('-created_at')[:1]

            if analysis_messages.exists():
                last_analysis = analysis_messages.first()
                if last_analysis.structured_data:
                    context += "\n=== 이전 AI 분석 결과 ===\n"
                    analysis_data = last_analysis.structured_data
                    if isinstance(analysis_data, dict):
                        if 'summary' in analysis_data:
                            context += f"요약: {analysis_data['summary']}\n"

            return context

        except Exception as e:
            logger.warning(f"Failed to build knowledge context: {e}, falling back to basic")
            # Fallback to basic context
            return f"도메인: {domain.domain_name}\n총 페이지: {domain.total_pages or 0}"

    def _get_system_prompt(self, conversation):
        """Get system prompt based on conversation type with sitemap context"""
        # Build context with actual sitemap data
        context = self._build_conversation_context(conversation)

        base_prompt = f"""당신은 SEO 전문가 AI 어시스턴트입니다. 한국어로 응답해주세요.

사용자의 질문에 대해 친절하고 전문적으로 답변하며, SEO와 사이트맵 최적화에 대한 조언을 제공합니다.

{context}

위의 사이트맵 데이터를 기반으로 사용자 질문에 답변하세요.
구체적인 URL과 데이터를 참조하여 실질적인 조언을 제공해주세요."""

        return base_prompt
