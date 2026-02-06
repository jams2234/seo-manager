"""
SEO Issues ViewSet
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone

from ..models import SEOIssue
from ..serializers import SEOIssueSerializer, SEOIssueListSerializer
from ..services.auto_fix_service import AutoFixService
from ..services.git_deployer import GitDeployer

logger = logging.getLogger(__name__)


class SEOIssueViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SEO Issues
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

        page_id = self.request.query_params.get('page_id')
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

    @action(detail=True, methods=['get'], url_path='preview-fix')
    def preview_fix(self, request, pk=None):
        """
        Preview the code changes that will be made when auto-fixing
        GET /api/v1/seo-issues/{id}/preview-fix/
        """
        from ..services.code_preview_service import CodePreviewService

        issue = self.get_object()

        if not issue.auto_fix_available:
            return Response(
                {'error': 'This issue is not auto-fixable'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            preview_service = CodePreviewService()
            preview = preview_service.get_preview(issue)

            return Response({
                'issue_id': issue.id,
                'issue_type': issue.issue_type,
                'page_url': issue.page.url,
                'file_path': preview.get('file_path'),
                'project_type': preview.get('project_type'),
                'before_code': preview.get('before_code'),
                'after_code': preview.get('after_code'),
                'old_value': preview.get('old_value'),
                'new_value': preview.get('new_value'),
            })

        except Exception as e:
            logger.error(f"Preview failed for issue {issue.id}: {e}", exc_info=True)
            return Response(
                {'error': f'Preview failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='auto-fix')
    @transaction.atomic
    def auto_fix(self, request, pk=None):
        """
        Auto-fix a specific issue, create AI suggestion, and optionally deploy to Git
        POST /api/v1/seo-issues/{id}/auto-fix/
        Body: {
            "deploy_to_git": true,  (기본값: true - Git 설정 시 자동 배포)
            "start_tracking": true  (기본값: true - 적용 후 바로 추적 시작)
        }
        """
        from ..services.git_deployer import GitDeployer
        from ..models import AISuggestion
        from ..services.suggestion_tracking import suggestion_tracking_service
        from ..services.vector_store import SEOVectorStore
        from django.utils import timezone

        issue = self.get_object()
        deploy_to_git = request.data.get('deploy_to_git', True)
        start_tracking = request.data.get('start_tracking', True)

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
            logger.info(f"Auto-fixing issue {issue.id}: {issue.title}")

            auto_fix_service = AutoFixService()
            result = auto_fix_service.fix_issue(issue)

            if not result.get('success'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            domain = issue.page.domain
            suggestion_type = 'title' if 'title' in issue.issue_type else 'description'

            # === AI 제안 자동 생성 (SEO 오토픽스와 연결) ===
            ai_suggestion = AISuggestion.objects.create(
                domain=domain,
                page=issue.page,
                suggestion_type=suggestion_type,
                priority=2,
                title=f"[오토픽스] {issue.title}",
                description=result.get('message', ''),
                expected_impact=f"SEO 이슈 해결: {issue.issue_type}",
                action_data={
                    'source': 'seo_autofix',
                    'issue_id': issue.id,
                    'issue_type': issue.issue_type,
                    f'old_{suggestion_type}': result.get('old_value'),
                    f'new_{suggestion_type}': result.get('new_value'),
                    'fix_method': result.get('method'),
                },
                is_auto_applicable=True,
                status='applied',
                applied_at=timezone.now(),
            )
            logger.info(f"Created AISuggestion {ai_suggestion.id} from SEO autofix")

            response_data = {
                'message': result.get('message'),
                'issue_id': issue.id,
                'method': result.get('method'),
                'old_value': result.get('old_value'),
                'new_value': result.get('new_value'),
                'deployed_to_git': False,
                'suggestion_id': ai_suggestion.id,
            }

            # === 추적 시작 (옵션) ===
            if start_tracking:
                tracking_result = suggestion_tracking_service.start_tracking(ai_suggestion.id)
                if tracking_result.get('success'):
                    response_data['tracking_started'] = True
                    response_data['message'] += ' 추적 시작됨.'
                    logger.info(f"Started tracking for suggestion {ai_suggestion.id}")

            # === Git 배포 (설정되어 있고 요청된 경우) ===
            if deploy_to_git and domain.git_enabled:
                try:
                    fixes = [{
                        'page_url': issue.page.url,
                        'field': suggestion_type,
                        'old_value': result.get('old_value'),
                        'new_value': result.get('new_value'),
                    }]

                    git_deployer = GitDeployer(domain)
                    git_result = git_deployer.deploy_fixes(fixes)

                    if git_result.get('success'):
                        response_data['deployed_to_git'] = True
                        response_data['message'] += ' Git 배포 완료.'
                        response_data['git_result'] = git_result
                    else:
                        response_data['git_error'] = git_result.get('error')
                except Exception as git_e:
                    logger.error(f"Git deploy failed: {git_e}")
                    response_data['git_error'] = str(git_e)

            # === 벡터 저장소에 임베딩 ===
            try:
                vector_store = SEOVectorStore()
                if vector_store.is_available():
                    vector_store.embed_fix_history_from_suggestion(ai_suggestion)
                    logger.info(f"Embedded fix history to vector store for suggestion {ai_suggestion.id}")
            except Exception as vec_e:
                logger.warning(f"Vector embedding failed (non-critical): {vec_e}")

            return Response(response_data)

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
        Auto-fix multiple issues at once, create AI suggestions, and optionally deploy to Git
        POST /api/v1/seo-issues/bulk-fix/
        Body: {
            "issue_ids": [...],
            "deploy_to_git": true,  (기본값: true - Git 설정 시 자동 배포)
            "start_tracking": true  (기본값: true - 적용 후 바로 추적 시작)
        }
        """
        from ..services.git_deployer import GitDeployer
        from ..models import AISuggestion
        from ..services.suggestion_tracking import suggestion_tracking_service
        from ..services.vector_store import SEOVectorStore

        issue_ids = request.data.get('issue_ids', [])
        deploy_to_git = request.data.get('deploy_to_git', True)
        start_tracking = request.data.get('start_tracking', True)

        if not issue_ids:
            return Response(
                {'error': 'No issue IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

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

        auto_fix_service = AutoFixService()
        results = []
        all_changes = []  # Git 배포용 변경사항 수집
        created_suggestions = []  # 생성된 AI 제안 목록
        fixed_count = 0
        failed_count = 0

        for issue in issues:
            try:
                result = auto_fix_service.fix_issue(issue)

                if result.get('success'):
                    fixed_count += 1
                    domain = issue.page.domain
                    suggestion_type = 'title' if 'title' in issue.issue_type else 'description'

                    # === AI 제안 자동 생성 ===
                    ai_suggestion = AISuggestion.objects.create(
                        domain=domain,
                        page=issue.page,
                        suggestion_type=suggestion_type,
                        priority=2,
                        title=f"[오토픽스] {issue.title}",
                        description=result.get('message', ''),
                        expected_impact=f"SEO 이슈 해결: {issue.issue_type}",
                        action_data={
                            'source': 'seo_autofix_bulk',
                            'issue_id': issue.id,
                            'issue_type': issue.issue_type,
                            f'old_{suggestion_type}': result.get('old_value'),
                            f'new_{suggestion_type}': result.get('new_value'),
                            'fix_method': result.get('method'),
                        },
                        is_auto_applicable=True,
                        status='applied',
                        applied_at=timezone.now(),
                    )
                    created_suggestions.append(ai_suggestion)
                    logger.info(f"Created AISuggestion {ai_suggestion.id} from bulk SEO autofix")

                    # Git 배포용 변경사항 수집
                    all_changes.append({
                        'page_url': issue.page.url,
                        'field': suggestion_type,
                        'old_value': result.get('old_value'),
                        'new_value': result.get('new_value'),
                    })

                    results.append({
                        'issue_id': issue.id,
                        'issue_type': issue.issue_type,
                        'success': True,
                        'message': result.get('message'),
                        'suggestion_id': ai_suggestion.id,
                    })
                else:
                    failed_count += 1
                    results.append({
                        'issue_id': issue.id,
                        'issue_type': issue.issue_type,
                        'success': False,
                        'message': result.get('message'),
                    })

            except Exception as e:
                logger.error(f"Bulk auto-fix failed for issue {issue.id}: {e}", exc_info=True)
                results.append({
                    'issue_id': issue.id,
                    'issue_type': issue.issue_type,
                    'success': False,
                    'message': f'Error: {str(e)}',
                })
                failed_count += 1

        response_data = {
            'message': f'{fixed_count}개 이슈 수정 완료',
            'fixed_count': fixed_count,
            'failed_count': failed_count,
            'total_requested': len(issue_ids),
            'results': results,
            'deployed_to_git': False,
            'suggestions_created': len(created_suggestions),
            'tracking_started': 0,
        }

        # === 추적 시작 (옵션) ===
        if start_tracking and created_suggestions:
            tracking_count = 0
            for suggestion in created_suggestions:
                try:
                    tracking_result = suggestion_tracking_service.start_tracking(suggestion.id)
                    if tracking_result.get('success'):
                        tracking_count += 1
                except Exception as track_e:
                    logger.warning(f"Failed to start tracking for suggestion {suggestion.id}: {track_e}")
            response_data['tracking_started'] = tracking_count
            if tracking_count > 0:
                response_data['message'] += f' {tracking_count}개 추적 시작.'
                logger.info(f"Started tracking for {tracking_count} bulk autofix suggestions")

        # Git 배포 (설정되어 있고 변경사항이 있는 경우)
        if deploy_to_git and all_changes:
            # 첫 번째 이슈의 도메인에서 Git 설정 확인
            first_issue = issues.first()
            if first_issue and first_issue.page.domain.git_enabled:
                try:
                    git_deployer = GitDeployer(first_issue.page.domain)
                    git_result = git_deployer.deploy_fixes(all_changes)

                    if git_result.get('success'):
                        response_data['deployed_to_git'] = True
                        response_data['message'] += ' Git 배포 완료.'
                        response_data['git_result'] = git_result
                    else:
                        response_data['git_error'] = git_result.get('error')
                except Exception as git_e:
                    logger.error(f"Bulk Git deploy failed: {git_e}")
                    response_data['git_error'] = str(git_e)

        # === 벡터 저장소에 임베딩 ===
        if created_suggestions:
            try:
                vector_store = SEOVectorStore()
                if vector_store.is_available():
                    embedded_count = 0
                    for suggestion in created_suggestions:
                        result = vector_store.embed_fix_history_from_suggestion(suggestion)
                        if result:
                            embedded_count += 1
                    response_data['embeddings_created'] = embedded_count
                    logger.info(f"Embedded {embedded_count} fix histories to vector store")
            except Exception as vec_e:
                logger.warning(f"Vector embedding failed (non-critical): {vec_e}")

        return Response(response_data)

    @action(detail=True, methods=['patch'], url_path='update-fix')
    @transaction.atomic
    def update_fix_value(self, request, pk=None):
        """
        Update the suggested fix value manually
        PATCH /api/v1/seo-issues/{id}/update-fix/
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

            if was_deployed:
                issue.deployed_to_git = False
                issue.deployment_commit_hash = None
                issue.deployed_at = None
                issue.save(update_fields=['suggested_value', 'deployed_to_git', 'deployment_commit_hash', 'deployed_at'])
                logger.info(f"Updated fix value for deployed issue {issue.id}: {old_value} -> {suggested_value}. Marked for redeployment.")
            else:
                issue.save(update_fields=['suggested_value'])
                logger.info(f"Updated fix value for issue {issue.id}: {old_value} -> {suggested_value}")

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
        Deploy all pending fixes to Git
        POST /api/v1/seo-issues/deploy-pending/
        """
        page_id = request.data.get('page_id')

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
                    commit_hash = deployment_result.get('commit_hash')
                    deployed_at = timezone.now()

                    issue_ids = [issue.id for issue in issues]
                    SEOIssue.objects.filter(id__in=issue_ids).update(
                        deployed_to_git=True,
                        deployed_at=deployed_at,
                        deployment_commit_hash=commit_hash,
                        verification_status='pending'
                    )

                    # === AISuggestion 생성 및 추적 시작 ===
                    from ..models import AISuggestion
                    from ..services.suggestion_tracking import suggestion_tracking_service

                    created_suggestions = 0
                    tracking_started = 0
                    for issue in issues:
                        # 이미 연결된 AISuggestion이 있는지 확인
                        existing = AISuggestion.objects.filter(
                            page=issue.page,
                            action_data__issue_id=issue.id
                        ).first()

                        if not existing:
                            suggestion_type = 'description' if 'description' in issue.issue_type else 'title'
                            ai_suggestion = AISuggestion.objects.create(
                                domain=domain,
                                page=issue.page,
                                suggestion_type=suggestion_type,
                                priority=2,
                                title=f'[오토픽스] {issue.title}',
                                description=issue.message or '',
                                expected_impact=f'SEO 이슈 해결: {issue.issue_type}',
                                action_data={
                                    'source': 'seo_deploy_pending',
                                    'issue_id': issue.id,
                                    'issue_type': issue.issue_type,
                                    f'old_{suggestion_type}': issue.current_value,
                                    f'new_{suggestion_type}': issue.suggested_value,
                                },
                                is_auto_applicable=True,
                                status='applied',
                                applied_at=deployed_at,
                            )
                            created_suggestions += 1

                            # 추적 시작
                            try:
                                result = suggestion_tracking_service.start_tracking(ai_suggestion.id)
                                if result.get('success'):
                                    tracking_started += 1
                            except Exception as track_e:
                                logger.warning(f"Failed to start tracking for suggestion {ai_suggestion.id}: {track_e}")

                    total_deployed += len(issue_ids)
                    deployment_results.append({
                        'domain': domain.domain_name,
                        'success': True,
                        'commit_hash': commit_hash,
                        'issues_count': len(issues),
                        'suggestions_created': created_suggestions,
                        'tracking_started': tracking_started,
                        'message': f'Successfully deployed {len(issues)} fixes'
                    })
                    logger.info(f"Successfully deployed {len(issues)} fixes for domain {domain.domain_name}, created {created_suggestions} suggestions")
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
        """
        issue = self.get_object()

        if issue.status not in ['auto_fixed', 'fixed']:
            return Response(
                {'error': f'Cannot revert issue with status: {issue.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            logger.info(f"Reverting issue {issue.id}: {issue.title}")

            old_suggested_value = issue.suggested_value
            old_current_value = issue.current_value

            issue.status = 'open'
            issue.fixed_at = None

            if issue.suggested_value:
                issue.suggested_value = None

            issue.save(update_fields=['status', 'fixed_at', 'suggested_value'])

            response_data = {
                'message': f'Issue reverted to open state',
                'issue_id': issue.id,
                'old_status': 'auto_fixed' if issue.status == 'open' else 'fixed',
                'new_status': 'open',
            }

            deploy_to_git = request.data.get('deploy_to_git', False)
            domain = issue.page.domain

            if deploy_to_git and domain.git_enabled and issue.deployed_to_git:
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
                            'old_value': old_suggested_value,
                            'new_value': old_current_value,
                        }]
                        deployment_result = deployer.deploy_fixes(git_fixes)

                        if deployment_result.get('success'):
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

    @action(detail=False, methods=['get'], url_path='effectiveness_stats')
    def effectiveness_stats(self, request):
        """
        AI 수정 효과성 통계
        GET /api/v1/seo-issues/effectiveness_stats/
        """
        from datetime import timedelta
        from ..models import AIFixHistory

        domain_id = request.query_params.get('domain_id')
        time_range = request.query_params.get('time_range', '30d')

        # 기간 계산
        days = 30
        if time_range == '7d':
            days = 7
        elif time_range == '90d':
            days = 90
        elif time_range == 'all':
            days = None

        queryset = AIFixHistory.objects.all()
        if domain_id:
            queryset = queryset.filter(page__domain_id=domain_id)
        if days:
            cutoff = timezone.now() - timedelta(days=days)
            queryset = queryset.filter(created_at__gte=cutoff)

        total = queryset.count()
        effective = queryset.filter(effectiveness='effective').count()
        ineffective = queryset.filter(effectiveness='ineffective').count()
        unknown = queryset.filter(effectiveness='unknown').count()

        # 재발률 계산
        recurred = queryset.filter(issue_recurred=True).count()
        recurrence_rate = recurred / total if total > 0 else 0

        # 평균 해결 시간
        avg_resolution_time = None
        fixed_with_time = queryset.exclude(deployed_at__isnull=True).exclude(created_at__isnull=True)
        if fixed_with_time.exists():
            total_time = sum(
                [(f.deployed_at - f.created_at).total_seconds() for f in fixed_with_time if f.deployed_at and f.created_at],
                0
            )
            avg_seconds = total_time / fixed_with_time.count() if fixed_with_time.count() > 0 else 0
            if avg_seconds > 0:
                hours = int(avg_seconds // 3600)
                minutes = int((avg_seconds % 3600) // 60)
                avg_resolution_time = f"{hours}시간 {minutes}분" if hours > 0 else f"{minutes}분"

        return Response({
            'total_fixes': total,
            'effective': effective,
            'ineffective': ineffective,
            'unknown': unknown,
            'effectiveness_rate': (effective / total * 100) if total > 0 else 0,
            'recurrence_rate': recurrence_rate,
            'avg_resolution_time': avg_resolution_time,
        })

    @action(detail=False, methods=['get'], url_path='recent_fixes')
    def recent_fixes(self, request):
        """
        최근 수정 이력
        GET /api/v1/seo-issues/recent_fixes/
        """
        from ..models import AIFixHistory

        domain_id = request.query_params.get('domain_id')
        limit = int(request.query_params.get('limit', 10))

        queryset = AIFixHistory.objects.all().select_related('page')
        if domain_id:
            queryset = queryset.filter(page__domain_id=domain_id)

        fixes = queryset.order_by('-created_at')[:limit]

        result = []
        for fix in fixes:
            result.append({
                'id': fix.id,
                'issue_type': fix.issue_type,
                'fix_status': fix.fix_status,
                'effectiveness': fix.effectiveness,
                'page_url': fix.page.url if fix.page else None,
                'issue_recurred': fix.issue_recurred,
                'recurrence_count': fix.recurrence_count,
                'created_at': fix.created_at,
                'deployed_at': fix.deployed_at,
            })

        return Response(result)
