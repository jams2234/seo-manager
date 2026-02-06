"""
AI Suggestions ViewSet
AI 제안 관리 및 액션 API
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer, SerializerMethodField
from django.utils import timezone

from ..models import AISuggestion, AIFeedback

logger = logging.getLogger(__name__)


class AISuggestionSerializer(ModelSerializer):
    """AI 제안 시리얼라이저"""
    domain_name = SerializerMethodField()
    page_url = SerializerMethodField()

    class Meta:
        model = AISuggestion
        fields = [
            'id', 'domain', 'domain_name', 'page', 'page_url',
            'analysis_run', 'suggestion_type', 'priority',
            'title', 'description', 'expected_impact',
            'action_data', 'is_auto_applicable', 'status',
            'rejected_reason', 'user_feedback',
            'accepted_at', 'applied_at', 'rejected_at', 'deferred_until',
            # 추적 관련 필드
            'tracking_started_at', 'tracking_ended_at', 'tracking_days',
            'baseline_metrics', 'final_metrics', 'impact_analysis',
            'effectiveness_score',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'domain_name', 'page_url', 'created_at', 'updated_at',
            'accepted_at', 'applied_at', 'rejected_at',
            'tracking_started_at', 'tracking_ended_at', 'tracking_days',
            'baseline_metrics', 'final_metrics', 'impact_analysis',
            'effectiveness_score',
        ]

    def get_domain_name(self, obj):
        return obj.domain.domain_name if obj.domain else None

    def get_page_url(self, obj):
        return obj.page.url if obj.page else None


class AISuggestionListSerializer(ModelSerializer):
    """AI 제안 목록 시리얼라이저"""
    domain_name = SerializerMethodField()
    page_url = SerializerMethodField()

    class Meta:
        model = AISuggestion
        fields = [
            'id', 'domain', 'domain_name', 'page', 'page_url',
            'suggestion_type', 'priority', 'title', 'description',
            'expected_impact', 'action_data',
            'is_auto_applicable', 'status', 'created_at',
        ]

    def get_domain_name(self, obj):
        return obj.domain.domain_name if obj.domain else None

    def get_page_url(self, obj):
        return obj.page.url if obj.page else None


class AISuggestionViewSet(viewsets.ModelViewSet):
    """
    AI 제안 관리 ViewSet

    Endpoints:
    - GET /ai-suggestions/ - 제안 목록
    - GET /ai-suggestions/{id}/ - 제안 상세
    - POST /ai-suggestions/{id}/accept/ - 제안 수락
    - POST /ai-suggestions/{id}/reject/ - 제안 거절
    - POST /ai-suggestions/{id}/defer/ - 제안 보류
    - POST /ai-suggestions/{id}/feedback/ - 피드백 제출
    """

    queryset = AISuggestion.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return AISuggestionListSerializer
        return AISuggestionSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        # 도메인 필터
        domain_id = self.request.query_params.get('domain_id')
        if domain_id:
            qs = qs.filter(domain_id=domain_id)

        # 상태 필터
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        # 유형 필터
        suggestion_type = self.request.query_params.get('type')
        if suggestion_type:
            qs = qs.filter(suggestion_type=suggestion_type)

        # 우선순위 필터
        priority = self.request.query_params.get('priority')
        if priority:
            qs = qs.filter(priority=int(priority))

        # 페이지 필터
        page_id = self.request.query_params.get('page_id')
        if page_id:
            qs = qs.filter(page_id=page_id)

        return qs.select_related('domain', 'page', 'analysis_run').order_by('priority', '-created_at')

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """
        제안 수락

        자동 적용 가능한 제안은 바로 적용하고 추적을 시작함
        수동 적용이 필요한 제안은 가이드 제공

        Body (optional):
        - deploy_to_git: true/false - Git 저장소에 배포 여부
        - start_tracking: true/false - 자동 적용 후 추적 시작 여부 (기본: true)
        """
        suggestion = self.get_object()
        deploy_to_git = request.data.get('deploy_to_git', False)
        start_tracking = request.data.get('start_tracking', True)  # 기본값: 자동 추적 시작

        if suggestion.status not in ['pending', 'deferred']:
            return Response(
                {'error': f'Cannot accept suggestion with status: {suggestion.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 자동 적용 시도
        # 페이지가 없어도 도메인 레벨 액션 (sitemap 제출, 색인 요청, bulk fix 등)은 적용 가능
        domain_level_types = [
            'priority_action', 'quick_win',
            'bulk_fix_descriptions', 'bulk_fix_titles'
        ]
        can_auto_apply = suggestion.is_auto_applicable and (
            suggestion.page is not None or
            suggestion.suggestion_type in domain_level_types
        )

        if can_auto_apply:
            try:
                from ..services.ai_auto_fixer import AIAutoFixer

                fixer = AIAutoFixer()
                result = fixer.apply_suggestion(suggestion, deploy_to_git=deploy_to_git)

                if result.get('success'):
                    suggestion.status = 'applied'
                    suggestion.applied_at = timezone.now()
                    suggestion.save()

                    # 피드백 기록
                    AIFeedback.objects.create(
                        suggestion=suggestion,
                        feedback_type='accept',
                        comment='Auto-applied successfully'
                    )

                    # 자동 추적 시작 (페이지가 있는 경우에만)
                    tracking_result = None
                    if start_tracking and suggestion.page:
                        try:
                            from ..services.suggestion_tracking import suggestion_tracking_service
                            tracking_result = suggestion_tracking_service.start_tracking(suggestion.id)
                            if tracking_result.get('success'):
                                logger.info(f"Auto-started tracking for suggestion {suggestion.id}")
                        except Exception as te:
                            logger.warning(f"Failed to auto-start tracking: {te}")
                            # 추적 시작 실패해도 적용 성공은 유지

                    return Response({
                        'success': True,
                        'message': '제안이 자동으로 적용되었습니다.' + (
                            ' 효과 추적이 시작되었습니다.' if tracking_result and tracking_result.get('success') else ''
                        ),
                        'result': result,
                        'tracking': tracking_result,
                        'status': suggestion.status,  # 'tracking' if tracking started
                    })
                else:
                    return Response({
                        'success': False,
                        'message': '자동 적용 실패. 수동 적용이 필요합니다.',
                        'error': result.get('error'),
                        'guide': suggestion.action_data.get('manual_guide') or result.get('manual_guide'),
                    })
            except Exception as e:
                logger.error(f"Auto-apply failed: {e}")
                # 자동 적용 실패 -> 수동 적용으로 전환
                suggestion.status = 'accepted'
                suggestion.accepted_at = timezone.now()
                suggestion.save()

                return Response({
                    'success': True,
                    'message': '자동 적용 실패. 제안이 수락되었습니다. 수동 적용이 필요합니다.',
                    'error': str(e),
                    'guide': suggestion.action_data.get('manual_guide'),
                })
        else:
            # 수동 적용
            suggestion.status = 'accepted'
            suggestion.accepted_at = timezone.now()
            suggestion.save()

            # 피드백 기록
            AIFeedback.objects.create(
                suggestion=suggestion,
                feedback_type='accept',
                comment='Manual application required'
            )

            return Response({
                'success': True,
                'message': '제안이 수락되었습니다. 수동 적용이 필요합니다.',
                'guide': suggestion.action_data.get('manual_guide'),
            })

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        제안 거절

        Body:
        - reason: 거절 사유 (선택)
        """
        suggestion = self.get_object()

        if suggestion.status not in ['pending', 'deferred', 'accepted']:
            return Response(
                {'error': f'Cannot reject suggestion with status: {suggestion.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '')

        suggestion.status = 'rejected'
        suggestion.rejected_reason = reason
        suggestion.rejected_at = timezone.now()
        suggestion.save()

        # 피드백 기록
        AIFeedback.objects.create(
            suggestion=suggestion,
            feedback_type='reject',
            comment=reason
        )

        return Response({
            'success': True,
            'message': '제안이 거절되었습니다.',
        })

    @action(detail=True, methods=['post'])
    def defer(self, request, pk=None):
        """
        제안 보류

        Body:
        - until: 보류 기한 (ISO 형식, 선택)
        """
        suggestion = self.get_object()

        if suggestion.status not in ['pending']:
            return Response(
                {'error': f'Cannot defer suggestion with status: {suggestion.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        until = request.data.get('until')

        suggestion.status = 'deferred'
        if until:
            try:
                from django.utils.dateparse import parse_datetime
                suggestion.deferred_until = parse_datetime(until)
            except Exception:
                pass
        suggestion.save()

        return Response({
            'success': True,
            'message': '제안이 보류되었습니다.',
            'deferred_until': suggestion.deferred_until,
        })

    @action(detail=True, methods=['post'])
    def feedback(self, request, pk=None):
        """
        피드백 제출

        Body:
        - feedback_type: helpful, not_helpful, incorrect
        - comment: 코멘트 (선택)
        """
        suggestion = self.get_object()

        feedback_type = request.data.get('feedback_type')
        comment = request.data.get('comment', '')

        if feedback_type not in ['helpful', 'not_helpful', 'incorrect']:
            return Response(
                {'error': 'Invalid feedback_type. Must be: helpful, not_helpful, incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 사용자 피드백 저장
        suggestion.user_feedback = comment if comment else feedback_type
        suggestion.save(update_fields=['user_feedback', 'updated_at'])

        # 피드백 기록
        AIFeedback.objects.create(
            suggestion=suggestion,
            feedback_type=feedback_type,
            comment=comment
        )

        return Response({
            'success': True,
            'message': '피드백이 제출되었습니다.',
        })

    @action(detail=True, methods=['post'])
    def mark_applied(self, request, pk=None):
        """
        수동 적용 완료 표시

        수락된 제안을 수동으로 적용한 후 호출
        """
        suggestion = self.get_object()

        if suggestion.status != 'accepted':
            return Response(
                {'error': 'Only accepted suggestions can be marked as applied'},
                status=status.HTTP_400_BAD_REQUEST
            )

        suggestion.status = 'applied'
        suggestion.applied_at = timezone.now()
        suggestion.save()

        return Response({
            'success': True,
            'message': '제안이 적용 완료로 표시되었습니다.',
        })

    @action(detail=True, methods=['get'])
    def preview_deployment(self, request, pk=None):
        """
        배포 미리보기

        제안 수락 시 어떤 변경이 이루어지는지 미리보기 제공

        Returns:
        - db_changes: DB에 적용될 변경사항
        - git_changes: Git에 배포될 파일 변경사항
        - git_config: Git 설정 상태
        """
        suggestion = self.get_object()

        if not suggestion.page:
            return Response({
                'success': False,
                'error': '페이지가 연결되지 않은 제안입니다.',
            })

        domain = suggestion.domain
        page = suggestion.page
        action_data = suggestion.action_data or {}

        # DB 변경 미리보기
        db_changes = []
        if suggestion.suggestion_type == 'title':
            new_title = action_data.get('new_title', '')
            if new_title:
                db_changes.append({
                    'table': 'Page',
                    'field': 'title',
                    'current': page.title or '(없음)',
                    'new': new_title,
                    'page_url': page.url,
                })
        elif suggestion.suggestion_type == 'description':
            new_desc = action_data.get('new_description', '')
            if new_desc:
                db_changes.append({
                    'table': 'Page',
                    'field': 'description',
                    'current': page.description or '(없음)',
                    'new': new_desc,
                    'page_url': page.url,
                })
        elif suggestion.suggestion_type == 'structure':
            # Sitemap 변경
            new_priority = action_data.get('new_priority')
            new_changefreq = action_data.get('new_changefreq')

            from ..models import SitemapEntry
            sitemap_entry = SitemapEntry.objects.filter(
                domain=domain, page=page
            ).first()

            if new_priority:
                db_changes.append({
                    'table': 'SitemapEntry',
                    'field': 'priority',
                    'current': str(sitemap_entry.priority) if sitemap_entry else '(없음)',
                    'new': str(new_priority),
                    'page_url': page.url,
                })
            if new_changefreq:
                db_changes.append({
                    'table': 'SitemapEntry',
                    'field': 'changefreq',
                    'current': sitemap_entry.changefreq if sitemap_entry else '(없음)',
                    'new': new_changefreq,
                    'page_url': page.url,
                })

        # Git 변경 미리보기
        git_changes = []
        git_config = {
            'enabled': domain.git_enabled,
            'repository': domain.git_repository,
            'branch': getattr(domain, 'git_branch', 'main'),
            'has_token': bool(domain.git_token),
            'can_deploy': bool(domain.git_enabled and domain.git_repository and domain.git_token),
        }

        if git_config['can_deploy']:
            # 프로젝트 타입 감지해서 어떤 파일이 변경될지 예측
            if suggestion.suggestion_type in ['title', 'description']:
                # Next.js 또는 HTML 파일 변경 예측
                target_path = getattr(domain, 'git_target_path', 'public')

                # URL을 파일 경로로 변환
                page_path = page.path or '/'
                if page_path == '/':
                    possible_files = [
                        f'pages/index.tsx',
                        f'pages/index.js',
                        f'app/page.tsx',
                        f'app/page.js',
                        f'{target_path}/index.html',
                    ]
                else:
                    clean_path = page_path.strip('/')
                    possible_files = [
                        f'pages/{clean_path}.tsx',
                        f'pages/{clean_path}/index.tsx',
                        f'app/{clean_path}/page.tsx',
                        f'{target_path}/{clean_path}.html',
                        f'{target_path}/{clean_path}/index.html',
                    ]

                field = 'title' if suggestion.suggestion_type == 'title' else 'meta description'
                new_value = action_data.get('new_title') or action_data.get('new_description') or ''

                git_changes.append({
                    'type': 'metadata_update',
                    'field': field,
                    'new_value': new_value,
                    'possible_files': possible_files[:3],  # 상위 3개만
                    'description': f'{field} 태그가 업데이트됩니다.',
                })

            elif suggestion.suggestion_type == 'structure':
                git_changes.append({
                    'type': 'sitemap_update',
                    'file': 'public/sitemap.xml',
                    'description': 'sitemap.xml 파일이 재생성됩니다.',
                    'changes': [
                        f'priority: {action_data.get("new_priority")}' if action_data.get("new_priority") else None,
                        f'changefreq: {action_data.get("new_changefreq")}' if action_data.get("new_changefreq") else None,
                    ],
                })

        return Response({
            'success': True,
            'suggestion_id': suggestion.id,
            'suggestion_type': suggestion.suggestion_type,
            'page_url': page.url,
            'is_auto_applicable': suggestion.is_auto_applicable,
            'db_changes': db_changes,
            'git_changes': git_changes,
            'git_config': git_config,
            'warnings': self._get_deployment_warnings(suggestion, git_config),
        })

    def _get_deployment_warnings(self, suggestion, git_config):
        """배포 관련 경고 메시지"""
        warnings = []

        if not suggestion.is_auto_applicable:
            warnings.append({
                'type': 'manual_required',
                'message': '이 제안은 자동 적용이 불가능합니다. 수동 적용이 필요합니다.',
            })

        if not git_config['enabled']:
            warnings.append({
                'type': 'git_disabled',
                'message': 'Git 배포가 비활성화되어 있습니다. DB 변경만 적용됩니다.',
            })
        elif not git_config['repository']:
            warnings.append({
                'type': 'git_no_repo',
                'message': 'Git 저장소가 설정되지 않았습니다.',
            })
        elif not git_config['has_token']:
            warnings.append({
                'type': 'git_no_token',
                'message': 'Git 토큰이 설정되지 않았습니다.',
            })

        return warnings

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        제안 요약 통계

        Query params:
        - domain_id: 도메인 필터 (선택)
        """
        domain_id = request.query_params.get('domain_id')

        qs = AISuggestion.objects.all()
        if domain_id:
            qs = qs.filter(domain_id=domain_id)

        # 상태별 카운트
        status_counts = {}
        for status_choice in ['pending', 'accepted', 'applied', 'rejected', 'deferred']:
            status_counts[status_choice] = qs.filter(status=status_choice).count()

        # 유형별 카운트
        type_counts = {}
        for type_choice in qs.values_list('suggestion_type', flat=True).distinct():
            type_counts[type_choice] = qs.filter(suggestion_type=type_choice).count()

        # 우선순위별 카운트
        priority_counts = {}
        for priority in [1, 2, 3]:
            priority_counts[priority] = qs.filter(priority=priority).count()

        # 추적중 카운트 추가
        status_counts['tracking'] = qs.filter(status='tracking').count()
        status_counts['tracked'] = qs.filter(status='tracked').count()

        return Response({
            'total': qs.count(),
            'by_status': status_counts,
            'by_type': type_counts,
            'by_priority': priority_counts,
            'pending_high_priority': qs.filter(status='pending', priority=1).count(),
            'tracking_count': status_counts['tracking'],
        })

    # ==============================
    # 추적 관련 엔드포인트
    # ==============================

    @action(detail=True, methods=['post'])
    def start_tracking(self, request, pk=None):
        """
        제안 추적 시작

        적용된 제안의 효과를 지속적으로 모니터링 시작

        Returns:
        - baseline_metrics: 시작 시점 기준 메트릭
        - tracking_started_at: 추적 시작 시간
        """
        from ..services.suggestion_tracking import suggestion_tracking_service

        result = suggestion_tracking_service.start_tracking(int(pk))

        if result.get('success'):
            return Response(result)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def tracking_data(self, request, pk=None):
        """
        추적 데이터 조회

        차트용 시계열 데이터, 스냅샷 목록, 분석 이력 반환

        Returns:
        - suggestion: 제안 기본 정보
        - baseline: 기준 메트릭
        - current: 현재 메트릭
        - snapshots: 일별 스냅샷 배열
        - analysis_logs: 분석 이력
        - chart_data: 차트용 데이터
        - summary: 요약 통계
        """
        from ..services.suggestion_tracking import suggestion_tracking_service

        result = suggestion_tracking_service.get_tracking_data(int(pk))

        if result.get('success'):
            return Response(result)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def analyze_impact(self, request, pk=None):
        """
        효과 분석 실행

        AI를 통해 제안의 효과를 분석하고 인사이트 생성

        Body:
        - analysis_type: 'manual' (기본), 'weekly', 'milestone', 'final'

        Returns:
        - analysis: AI 분석 결과
        - changes: 메트릭 변화
        - effectiveness_score: 효과성 점수
        - trend_direction: 트렌드 방향
        """
        from ..services.suggestion_tracking import suggestion_tracking_service

        analysis_type = request.data.get('analysis_type', 'manual')

        result = suggestion_tracking_service.analyze_impact(int(pk), analysis_type)

        if result.get('success'):
            return Response(result)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def end_tracking(self, request, pk=None):
        """
        추적 종료

        제안 추적을 완료하고 최종 분석 실행

        Body:
        - run_final_analysis: 최종 분석 실행 여부 (기본 true)

        Returns:
        - final_metrics: 최종 메트릭
        - impact_analysis: AI 효과 분석 결과
        - effectiveness_score: 최종 효과성 점수
        """
        from ..services.suggestion_tracking import suggestion_tracking_service

        run_final_analysis = request.data.get('run_final_analysis', True)

        result = suggestion_tracking_service.end_tracking(int(pk), run_final_analysis)

        if result.get('success'):
            return Response(result)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def tracking_list(self, request):
        """
        추적중인 제안 목록

        Query params:
        - domain_id: 도메인 필터 (선택)

        Returns:
        - tracking_count: 추적 중인 제안 수
        - suggestions: 추적 중인 제안 목록
        """
        from ..services.suggestion_tracking import suggestion_tracking_service

        domain_id = request.query_params.get('domain_id')

        result = suggestion_tracking_service.get_tracking_list(
            domain_id=int(domain_id) if domain_id else None
        )

        return Response(result)

    @action(detail=True, methods=['post'])
    def capture_snapshot(self, request, pk=None):
        """
        스냅샷 수동 캡처

        현재 시점의 스냅샷을 즉시 캡처

        Returns:
        - snapshot: 캡처된 스냅샷 데이터
        - day_number: 추적 일차
        """
        from ..services.suggestion_tracking import suggestion_tracking_service

        result = suggestion_tracking_service.capture_daily_snapshot(int(pk))

        if result.get('success'):
            return Response(result)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
