"""
Sitemap AI Analysis ViewSets
Provides API endpoints for AI-powered sitemap and SEO analysis.
"""
import logging
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Domain, SitemapEntry, AIConversation, AIMessage
from ..services import SitemapAIAnalyzerService
from ..services.claude_client import ClaudeAPIClient
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
            user_message = AIMessage.objects.create(
                conversation=conversation,
                role='user',
                content=message_content,
            )

            # Build context for AI
            context = self._build_conversation_context(conversation)

            # Get AI response
            client = ClaudeAPIClient()
            system_prompt = self._get_system_prompt(conversation)

            # Include conversation history
            messages_for_ai = []
            for msg in conversation.messages.order_by('created_at'):
                if msg.role in ['user', 'assistant']:
                    messages_for_ai.append({
                        'role': msg.role,
                        'content': msg.content
                    })

            # Call Claude API
            result = client.chat(
                messages=messages_for_ai,
                system=system_prompt
            )

            if not result.get('success'):
                return Response(
                    {'error': result.get('error', 'AI response failed')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Save assistant response
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

            return Response({
                'user_message': AIMessageSerializer(user_message).data,
                'assistant_message': AIMessageSerializer(assistant_message).data,
                'conversation': AIConversationSerializer(conversation).data,
            })

        except Exception as e:
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
        """Build context string from domain data"""
        if not conversation.domain:
            return ""

        domain = conversation.domain
        context_parts = [
            f"도메인: {domain.domain_name}",
            f"총 페이지: {domain.total_pages or 0}",
        ]

        if domain.avg_seo_score:
            context_parts.append(f"평균 SEO 점수: {domain.avg_seo_score:.1f}")

        return "\n".join(context_parts)

    def _get_system_prompt(self, conversation):
        """Get system prompt based on conversation type"""
        base_prompt = """당신은 SEO 전문가 AI 어시스턴트입니다. 한국어로 응답해주세요.

사용자의 질문에 대해 친절하고 전문적으로 답변하며, SEO와 사이트맵 최적화에 대한 조언을 제공합니다.
분석 결과가 있다면 그것을 참고하여 답변해주세요."""

        if conversation.domain:
            base_prompt += f"\n\n현재 분석 중인 도메인: {conversation.domain.domain_name}"

        return base_prompt
