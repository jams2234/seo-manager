"""
AI Learning ViewSet
AI 학습 상태 관리 및 트리거 API
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from ..models import Domain, AILearningState, AIAnalysisRun
from ..tasks import ai_continuous_learning_sync, ai_auto_analysis

logger = logging.getLogger(__name__)


class AILearningViewSet(viewsets.ViewSet):
    """
    AI 학습 관리 API

    Endpoints:
    - GET /ai-learning/status/ - 학습 상태 조회
    - POST /ai-learning/trigger_sync/ - 수동 동기화 트리거
    - POST /ai-learning/trigger_analysis/ - 수동 AI 분석 트리거
    - GET /ai-learning/analysis_history/ - 분석 실행 이력
    - GET /ai-learning/vector_stats/ - 벡터 저장소 통계
    """

    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        모든 도메인 또는 특정 도메인의 AI 학습 상태 조회

        Query params:
        - domain_id: 특정 도메인 필터
        """
        domain_id = request.query_params.get('domain_id')

        if domain_id:
            states = AILearningState.objects.filter(domain_id=domain_id)
        else:
            states = AILearningState.objects.all()

        data = []
        for state in states.select_related('domain'):
            data.append({
                'domain_id': state.domain_id,
                'domain_name': state.domain.domain_name,
                'last_sync_at': state.last_sync_at,
                'pages_synced': state.pages_synced,
                'embeddings_updated': state.embeddings_updated,
                'sync_status': state.sync_status,
                'learning_quality_score': state.learning_quality_score,
                'total_fixes_learned': state.total_fixes_learned,
                'effective_fixes_count': state.effective_fixes_count,
                'last_error': state.last_error,
            })

        return Response(data)

    @action(detail=False, methods=['post'])
    def trigger_sync(self, request):
        """
        수동 AI 학습 동기화 트리거

        Body:
        - domain_id: 도메인 ID (필수)
        """
        domain_id = request.data.get('domain_id')

        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            return Response(
                {'error': 'Domain not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 학습 상태 업데이트
        learning_state, _ = AILearningState.objects.get_or_create(
            domain=domain,
            defaults={'sync_status': 'syncing'}
        )
        learning_state.sync_status = 'syncing'
        learning_state.save(update_fields=['sync_status'])

        # Celery 태스크 실행
        try:
            task = ai_continuous_learning_sync.delay(domain_id)
            return Response({
                'success': True,
                'task_id': task.id,
                'message': f'AI 학습 동기화가 시작되었습니다: {domain.domain_name}',
            })
        except Exception as e:
            logger.error(f"Failed to trigger sync: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def trigger_analysis(self, request):
        """
        수동 AI 분석 트리거

        Body:
        - domain_id: 도메인 ID (필수)
        """
        domain_id = request.data.get('domain_id')

        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            return Response(
                {'error': 'Domain not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Celery 태스크 실행
        try:
            task = ai_auto_analysis.delay(domain_id, trigger_type='manual')
            return Response({
                'success': True,
                'task_id': task.id,
                'message': f'AI 분석이 시작되었습니다: {domain.domain_name}',
            })
        except Exception as e:
            logger.error(f"Failed to trigger analysis: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def analysis_history(self, request):
        """
        AI 분석 실행 이력 조회

        Query params:
        - domain_id: 특정 도메인 필터
        - limit: 결과 수 제한 (기본 20)
        """
        domain_id = request.query_params.get('domain_id')
        limit = int(request.query_params.get('limit', 20))

        qs = AIAnalysisRun.objects.all()
        if domain_id:
            qs = qs.filter(domain_id=domain_id)

        runs = qs.select_related('domain').order_by('-created_at')[:limit]

        data = []
        for run in runs:
            data.append({
                'id': run.id,
                'domain_id': run.domain_id,
                'domain_name': run.domain.domain_name,
                'status': run.status,
                'trigger_type': run.trigger_type,
                'suggestions_count': run.suggestions_count,
                'insights_count': run.insights_count,
                'started_at': run.started_at,
                'completed_at': run.completed_at,
                'duration': run.duration,
                'result_summary': run.result_summary,
                'error_message': run.error_message,
            })

        return Response(data)

    @action(detail=False, methods=['get'])
    def vector_stats(self, request):
        """
        벡터 저장소 통계 조회
        """
        from ..services.vector_store import get_vector_store

        vector_store = get_vector_store()
        stats = vector_store.get_stats()

        return Response(stats)

    @action(detail=False, methods=['get'])
    def task_status(self, request):
        """
        Celery 태스크 상태 조회

        Query params:
        - task_id: Celery 태스크 ID
        """
        from celery.result import AsyncResult

        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response(
                {'error': 'task_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = AsyncResult(task_id)
            response = {
                'task_id': task_id,
                'status': result.status,
                'ready': result.ready(),
            }

            if result.ready():
                if result.successful():
                    response['result'] = result.result
                else:
                    response['error'] = str(result.result)
            elif result.status == 'PROGRESS':
                response['progress'] = result.info

            return Response(response)

        except Exception as e:
            logger.error(f"Failed to get task status: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
