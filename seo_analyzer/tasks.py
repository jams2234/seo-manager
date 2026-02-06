"""
Celery Tasks for SEO Analyzer
"""
import logging
from datetime import datetime, timezone
from celery import shared_task
from django.db import transaction
from .models import Domain, Page, SEOMetrics, HistoricalMetrics
from .services import DomainRefreshService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    soft_time_limit=600,  # 10 minutes soft limit
    time_limit=660,       # 11 minutes hard limit
    acks_late=True,       # Acknowledge after completion (allows retry on crash)
    max_retries=1,        # Retry once on failure
)
def refresh_domain_cache(self, domain_id):
    """
    Background task to refresh all data for a domain

    Args:
        domain_id: ID of the domain to refresh

    Returns:
        dict: Refresh result with pages_discovered, pages_processed, etc.

    Notes:
        - Uses 4 parallel workers (safe for Celery fork)
        - 10 minute soft limit, 11 minute hard limit
        - Will retry once on crash/timeout
    """
    try:
        domain = Domain.objects.get(id=domain_id)
        logger.info(f"Starting background scan for domain: {domain.domain_name}")

        # Update sync status to running
        domain.full_scan_status = 'running'
        domain.save(update_fields=['full_scan_status'])

        # Progress callback for Celery state updates
        def progress_callback(current, total, message):
            """Update Celery task state with progress info"""
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': current,
                    'total': total,
                    'status': message,
                    'percent': int((current / total) * 100) if total > 0 else 0
                }
            )

        # Use DomainRefreshService (max 1000 pages, includes desktop)
        # mobile_only=False: Comprehensive analysis with both mobile and desktop scores
        service = DomainRefreshService(max_pages=1000, max_metrics=100, mobile_only=False)
        result = service.refresh_domain(domain, progress_callback=progress_callback)

        logger.info(
            f"Completed background scan for {domain.domain_name}: "
            f"{result['metrics_fetched']}/{result['pages_discovered']} pages processed"
        )

        # Update sync status to success
        domain.full_scan_status = 'success'
        domain.last_full_scan_at = timezone.now()
        domain.save(update_fields=['full_scan_status', 'last_full_scan_at'])

        return {
            'domain_id': domain_id,
            'domain_name': domain.domain_name,
            'pages_discovered': result['pages_discovered'],
            'pages_processed': result['pages_processed'],
            'metrics_fetched': result['metrics_fetched'],
            'status': 'completed'
        }

    except Domain.DoesNotExist:
        logger.error(f"Domain {domain_id} not found")
        return {
            'error': True,
            'message': f'Domain {domain_id} not found'
        }
    except Exception as e:
        logger.error(f"Error in refresh_domain_cache for domain {domain_id}: {e}")
        # Update sync status to failed
        try:
            domain = Domain.objects.get(id=domain_id)
            domain.full_scan_status = 'failed'
            domain.save(update_fields=['full_scan_status'])
        except Exception:
            pass
        return {
            'error': True,
            'message': str(e)
        }


@shared_task
def nightly_cache_update():
    """
    Nightly task to update all active domains
    """
    logger.info("Starting nightly cache update")

    active_domains = Domain.objects.filter(status='active')
    logger.info(f"Found {active_domains.count()} active domains")

    for domain in active_domains:
        try:
            # Trigger individual domain refresh
            refresh_domain_cache.delay(domain.id)
            logger.info(f"Queued refresh for {domain.domain_name}")
        except Exception as e:
            logger.error(f"Failed to queue refresh for {domain.domain_name}: {e}")

    return {
        'status': 'completed',
        'domains_queued': active_domains.count()
    }


@shared_task(
    bind=True,
    soft_time_limit=300,  # 5분 soft limit
    time_limit=360,       # 6분 hard limit
    acks_late=True,
    max_retries=1,
)
def gsc_sync_domain(self, domain_id: int):
    """
    GSC 경량 동기화 - Search Console 데이터만 업데이트

    PageSpeed API 호출 없이 GSC 데이터만 업데이트:
    - 색인 상태 (URL Inspection API)
    - 노출수/클릭수 (Search Analytics API)

    장점:
    - 빠름 (17페이지 기준 ~10초)
    - PageSpeed API 쿼터 절약
    - GSC 데이터는 2-3일 지연되므로 하루 2회면 충분
    """
    try:
        domain = Domain.objects.get(id=domain_id)
        logger.info(f"Starting GSC sync for: {domain.domain_name}")

        # Update sync status to running
        domain.gsc_sync_status = 'running'
        domain.save(update_fields=['gsc_sync_status'])

        def progress_callback(current, total, message):
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': current,
                    'total': total,
                    'status': message,
                    'percent': int((current / total) * 100) if total > 0 else 0
                }
            )

        service = DomainRefreshService()
        result = service.refresh_search_console_only(domain, progress_callback=progress_callback)

        logger.info(
            f"GSC sync completed for {domain.domain_name}: "
            f"{result.get('pages_updated', 0)} pages updated"
        )

        # Update sync status to success
        domain.gsc_sync_status = 'success'
        domain.last_gsc_sync_at = timezone.now()
        domain.save(update_fields=['gsc_sync_status', 'last_gsc_sync_at'])

        return {
            'domain_id': domain_id,
            'domain_name': domain.domain_name,
            'pages_updated': result.get('pages_updated', 0),
            'pages_failed': result.get('pages_failed', 0),
            'elapsed_time': result.get('elapsed_time', 0),
            'status': 'completed'
        }

    except Domain.DoesNotExist:
        logger.error(f"Domain {domain_id} not found")
        return {'error': True, 'message': f'Domain {domain_id} not found'}
    except Exception as e:
        logger.error(f"Error in gsc_sync_domain for domain {domain_id}: {e}", exc_info=True)
        # Update sync status to failed
        try:
            domain = Domain.objects.get(id=domain_id)
            domain.gsc_sync_status = 'failed'
            domain.save(update_fields=['gsc_sync_status'])
        except Exception:
            pass
        return {'error': True, 'message': str(e)}


@shared_task
def gsc_sync_all_domains():
    """
    모든 활성 도메인의 GSC 데이터 동기화

    하루 2회 실행 권장 (08:00, 20:00)
    - GSC 데이터는 2-3일 지연되므로 자주 호출할 필요 없음
    - URL Inspection API 쿼터: 2,000/일/사이트
    """
    logger.info("Starting GSC sync for all active domains")

    active_domains = Domain.objects.filter(status='active')
    logger.info(f"Found {active_domains.count()} active domains")

    queued = 0
    for domain in active_domains:
        try:
            gsc_sync_domain.delay(domain.id)
            logger.info(f"Queued GSC sync for {domain.domain_name}")
            queued += 1
        except Exception as e:
            logger.error(f"Failed to queue GSC sync for {domain.domain_name}: {e}")

    return {
        'status': 'completed',
        'domains_queued': queued
    }


@shared_task
def generate_daily_snapshot():
    """
    Generate daily snapshots for historical tracking
    """
    logger.info("Generating daily snapshots")

    snapshot_date = datetime.now(timezone.utc).date()
    created_count = 0

    # Get all active pages with metrics
    pages = Page.objects.filter(status='active').prefetch_related('seo_metrics')

    for page in pages:
        latest_metrics = page.seo_metrics.first()
        if latest_metrics:
            # Check if snapshot already exists for today
            existing = HistoricalMetrics.objects.filter(
                page=page,
                date=snapshot_date
            ).exists()

            if not existing:
                HistoricalMetrics.objects.create(
                    page=page,
                    seo_score=latest_metrics.seo_score,
                    performance_score=latest_metrics.performance_score,
                    accessibility_score=latest_metrics.accessibility_score,
                    avg_position=latest_metrics.avg_position,
                    total_clicks=latest_metrics.clicks,
                    total_impressions=latest_metrics.impressions,
                    date=snapshot_date,
                )
                created_count += 1

    logger.info(f"Created {created_count} daily snapshots")

    return {
        'status': 'completed',
        'snapshots_created': created_count,
        'date': str(snapshot_date)
    }


# ============================================================================
# AI 지속 학습 태스크
# ============================================================================

@shared_task(
    bind=True,
    soft_time_limit=1800,  # 30분 soft limit
    time_limit=2100,       # 35분 hard limit
    acks_late=True,
    max_retries=1,
)
def ai_continuous_learning_sync(self, domain_id: int):
    """
    도메인별 AI 지속 학습 동기화

    Process:
    1. 새로운/변경된 데이터 감지
    2. 벡터 DB 임베딩 업데이트
    3. 학습 상태 기록
    """
    from .models import Domain, AILearningState
    from .services.vector_store import get_vector_store

    try:
        domain = Domain.objects.get(id=domain_id)
        logger.info(f"Starting AI learning sync for: {domain.domain_name}")

        # 학습 상태 가져오거나 생성
        learning_state, created = AILearningState.objects.get_or_create(
            domain=domain,
            defaults={'sync_status': 'syncing'}
        )

        if not created:
            learning_state.sync_status = 'syncing'
            learning_state.save(update_fields=['sync_status'])

        vector_store = get_vector_store()

        if not vector_store.is_available():
            learning_state.sync_status = 'failed'
            learning_state.last_error = 'Vector store not available'
            learning_state.save()
            return {'error': True, 'message': 'Vector store not available'}

        # 도메인 동기화
        result = vector_store.sync_domain(domain)

        # 학습 상태 업데이트
        learning_state.last_sync_at = datetime.now(timezone.utc)
        learning_state.pages_synced = result.get('pages_embedded', 0)
        learning_state.embeddings_updated = (
            result.get('pages_embedded', 0) +
            result.get('fixes_embedded', 0) +
            (1 if result.get('domain_embedded') else 0)
        )
        learning_state.sync_status = 'success' if not result.get('errors') else 'failed'
        learning_state.last_error = '; '.join(result.get('errors', [])) if result.get('errors') else None
        learning_state.save()

        logger.info(f"AI learning sync completed for {domain.domain_name}: {result}")
        return result

    except Domain.DoesNotExist:
        logger.error(f"Domain {domain_id} not found")
        return {'error': True, 'message': 'Domain not found'}
    except Exception as e:
        logger.error(f"AI learning sync failed: {e}", exc_info=True)
        # 실패 상태 저장
        try:
            AILearningState.objects.filter(domain_id=domain_id).update(
                sync_status='failed',
                last_error=str(e)
            )
        except Exception:
            pass
        raise


@shared_task(
    bind=True,
    soft_time_limit=3600,  # 1시간 soft limit
    time_limit=3900,       # 1시간 5분 hard limit
)
def ai_auto_analysis(self, domain_id: int, trigger_type: str = 'manual'):
    """
    AI 자동 분석 및 제안 생성

    Args:
        domain_id: 도메인 ID
        trigger_type: 'manual', 'scheduled', 'event'

    Process:
    1. 도메인 전체 컨텍스트 로드
    2. RAG로 관련 지식 검색
    3. Claude API로 종합 분석
    4. 제안 생성 및 저장
    """
    from .models import Domain, AIAnalysisRun, AISuggestion
    from .services.ai_analysis_engine import AIAnalysisEngine

    run = None

    try:
        domain = Domain.objects.get(id=domain_id)
        logger.info(f"Starting AI auto-analysis for: {domain.domain_name}")

        # 분석 실행 기록 생성
        run = AIAnalysisRun.objects.create(
            domain=domain,
            status='running',
            trigger_type=trigger_type,
            started_at=datetime.now(timezone.utc),
            celery_task_id=self.request.id,
        )

        def progress_callback(current, total, message):
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': current,
                    'total': total,
                    'status': message,
                    'percent': int((current / total) * 100) if total > 0 else 0
                }
            )

        engine = AIAnalysisEngine()
        result = engine.run_full_analysis(
            domain,
            progress_callback=progress_callback
        )

        if not result.get('success'):
            raise Exception(result.get('error', 'Analysis failed'))

        # 결과 저장
        run.status = 'completed'
        run.completed_at = datetime.now(timezone.utc)
        run.suggestions_count = len(result.get('suggestions', []))
        run.insights_count = len(result.get('insights', []))
        run.result_summary = result.get('summary', {})
        run.save()

        # 제안 생성
        with transaction.atomic():
            for suggestion in result.get('suggestions', []):
                AISuggestion.objects.create(
                    domain=domain,
                    analysis_run=run,
                    page_id=suggestion.get('page_id'),
                    suggestion_type=suggestion.get('type', 'general'),
                    priority=suggestion.get('priority', 2),
                    title=suggestion.get('title', ''),
                    description=suggestion.get('description', ''),
                    expected_impact=suggestion.get('expected_impact'),
                    action_data=suggestion.get('action_data', {}),
                    is_auto_applicable=suggestion.get('is_auto_applicable', False),
                )

        logger.info(f"AI auto-analysis completed for {domain.domain_name}")

        return {
            'domain_id': domain_id,
            'run_id': run.id,
            'suggestions_count': run.suggestions_count,
            'insights_count': run.insights_count,
            'status': 'completed',
        }

    except Domain.DoesNotExist:
        logger.error(f"Domain {domain_id} not found")
        return {'error': True, 'message': 'Domain not found'}
    except Exception as e:
        logger.error(f"AI auto-analysis failed: {e}", exc_info=True)
        if run:
            run.status = 'failed'
            run.error_message = str(e)
            run.completed_at = datetime.now(timezone.utc)
            run.save()
        raise


@shared_task
def schedule_all_domain_analysis():
    """
    모든 활성 도메인에 대해 AI 분석 스케줄링
    (Celery Beat에서 호출)
    """
    from .models import Domain

    domains = Domain.objects.filter(
        status='active',
        sitemap_ai_enabled=True,
    )

    queued = 0
    for domain in domains:
        try:
            ai_auto_analysis.delay(domain.id, trigger_type='scheduled')
            queued += 1
            logger.info(f"Queued AI analysis for {domain.domain_name}")
        except Exception as e:
            logger.error(f"Failed to queue AI analysis for {domain.domain_name}: {e}")

    logger.info(f"Scheduled AI analysis for {queued} domains")
    return {'domains_queued': queued}


@shared_task
def update_vector_embeddings():
    """
    변경된 데이터의 벡터 임베딩 업데이트 (증분)
    """
    from datetime import timedelta
    from .models import Domain, Page, AIFixHistory
    from .services.vector_store import get_vector_store

    vector_store = get_vector_store()

    if not vector_store.is_available():
        logger.warning("Vector store not available, skipping embedding update")
        return {'skipped': True, 'reason': 'Vector store not available'}

    # 최근 6시간 이내 업데이트된 데이터
    cutoff = datetime.now(timezone.utc) - timedelta(hours=6)

    stats = {
        'domains': 0,
        'pages': 0,
        'fixes': 0,
    }

    # 도메인 업데이트
    updated_domains = Domain.objects.filter(updated_at__gte=cutoff)
    for domain in updated_domains:
        if vector_store.embed_domain(domain):
            stats['domains'] += 1

    # 페이지 업데이트
    updated_pages = Page.objects.filter(updated_at__gte=cutoff)
    for page in updated_pages:
        if vector_store.embed_page(page):
            stats['pages'] += 1

    # 수정 이력 업데이트
    new_fixes = AIFixHistory.objects.filter(created_at__gte=cutoff)
    for fix in new_fixes:
        if vector_store.embed_fix_history(fix):
            stats['fixes'] += 1

    logger.info(f"Vector embeddings updated: {stats}")
    return stats


@shared_task
def evaluate_fix_effectiveness():
    """
    AI 수정의 효과성 평가 (SEO 점수 학습 기반)

    배포 후 일정 기간(7일) 경과한 수정에 대해:
    1. SEO 점수 변화 분석 (before vs after)
    2. 이슈 재발 여부 확인
    3. 종합 효과성 점수 업데이트
    4. post_fix_metrics에 현재 점수 저장 (학습용)
    """
    from datetime import timedelta
    from .models import AIFixHistory, SEOIssue

    # 7일 전 수정된(applied/deployed) 미평가 항목 조회
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    pending_fixes = AIFixHistory.objects.filter(
        fix_status__in=['applied', 'deployed'],
        effectiveness='unknown',
        created_at__lt=cutoff,
    ).select_related('page')

    evaluated = 0
    results = {'effective': 0, 'partial': 0, 'ineffective': 0, 'negative': 0}

    for fix in pending_fixes:
        try:
            page = fix.page
            if not page:
                continue

            # 1. SEO 점수 변화 분석
            pre_metrics = fix.pre_fix_metrics or {}
            pre_seo_score = pre_metrics.get('seo_score', 0) or 0

            # 현재 SEO 점수 가져오기
            latest_metrics = page.seo_metrics.first()
            current_seo_score = float(latest_metrics.seo_score) if latest_metrics and latest_metrics.seo_score else 0

            # 점수 변화 계산
            score_change = current_seo_score - pre_seo_score

            # post_fix_metrics에 현재 점수 저장 (학습용)
            fix.post_fix_metrics = {
                'seo_score': current_seo_score,
                'performance_score': float(latest_metrics.performance_score) if latest_metrics and latest_metrics.performance_score else None,
                'measured_at': datetime.now(timezone.utc).isoformat(),
                'score_change': score_change,
            }

            # 2. 이슈 재발 여부 확인
            recurred = SEOIssue.objects.filter(
                page=page,
                issue_type=fix.issue_type,
                detected_at__gt=fix.created_at,
            ).exists()

            if recurred:
                fix.issue_recurred = True
                fix.recurrence_count = SEOIssue.objects.filter(
                    page=page,
                    issue_type=fix.issue_type,
                    detected_at__gt=fix.created_at,
                ).count()
                fix.recurrence_detected_at = datetime.now(timezone.utc)
            else:
                fix.issue_recurred = False

            # 3. 종합 효과성 판단 (점수 변화 + 이슈 재발)
            if score_change < -5:
                # 점수가 5점 이상 하락 → 부정적
                fix.effectiveness = 'negative'
                results['negative'] += 1
            elif recurred or score_change < -2:
                # 이슈 재발 또는 점수 2점 이상 하락 → 비효과적
                fix.effectiveness = 'ineffective'
                results['ineffective'] += 1
            elif score_change >= 3:
                # 점수 3점 이상 상승 → 효과적
                fix.effectiveness = 'effective'
                results['effective'] += 1
            elif score_change >= 0:
                # 점수 유지 또는 소폭 상승 → 부분적
                fix.effectiveness = 'partial'
                results['partial'] += 1
            else:
                # 그 외 → 비효과적
                fix.effectiveness = 'ineffective'
                results['ineffective'] += 1

            fix.effectiveness_evaluated_at = datetime.now(timezone.utc)
            fix.save(update_fields=[
                'effectiveness', 'effectiveness_evaluated_at',
                'post_fix_metrics', 'issue_recurred', 'recurrence_count', 'recurrence_detected_at'
            ])
            evaluated += 1

            logger.info(
                f"Fix {fix.id} evaluated: {fix.effectiveness} "
                f"(score: {pre_seo_score:.1f} → {current_seo_score:.1f}, change: {score_change:+.1f})"
            )

        except Exception as e:
            logger.error(f"Failed to evaluate fix {fix.id}: {e}")

    logger.info(f"Evaluated {evaluated} fixes: {results}")
    return {'evaluated': evaluated, 'results': results}


# ==============================
# AI 제안 추적 태스크
# ==============================

@shared_task
def capture_tracking_snapshots():
    """
    추적중인 모든 제안의 일일 스냅샷 캡처

    스케줄: 매일 08:30 (GSC 동기화 완료 후)
    - GSC 데이터, SEO 점수 등 현재 메트릭 캡처
    - baseline 대비 변화량 계산
    - SuggestionTrackingSnapshot 레코드 생성
    """
    from .services.suggestion_tracking import suggestion_tracking_service

    logger.info("📊 Starting daily tracking snapshot capture...")

    try:
        result = suggestion_tracking_service.capture_all_tracking_snapshots()

        logger.info(
            f"📊 Daily snapshot capture completed: "
            f"{result.get('captured', 0)} captured, "
            f"{result.get('skipped', 0)} skipped, "
            f"{result.get('failed', 0)} failed"
        )

        return result

    except Exception as e:
        logger.error(f"Daily snapshot capture failed: {e}", exc_info=True)
        return {'error': True, 'message': str(e)}


@shared_task
def analyze_tracking_effectiveness():
    """
    추적중인 제안의 주간 효과 분석

    스케줄: 매주 월요일 09:00
    - 7일 이상 추적된 제안에 대해 AI 효과 분석 실행
    - SuggestionEffectivenessLog 생성
    """
    from .services.suggestion_tracking import suggestion_tracking_service
    from .models import AISuggestion

    logger.info("🔍 Starting weekly effectiveness analysis...")

    # 7일 이상 추적된 제안 조회
    tracking_suggestions = AISuggestion.objects.filter(
        status='tracking',
        tracking_days__gte=7
    )

    analyzed = 0
    failed = 0

    for suggestion in tracking_suggestions:
        try:
            # 최근 주간 분석이 없는 경우에만 실행
            recent_log = suggestion.effectiveness_logs.filter(
                analysis_type='weekly'
            ).order_by('-created_at').first()

            # 7일 이내에 주간 분석이 있으면 스킵
            if recent_log:
                from datetime import timedelta
                if (datetime.now(timezone.utc) - recent_log.created_at) < timedelta(days=7):
                    continue

            result = suggestion_tracking_service.analyze_impact(
                suggestion.id,
                analysis_type='weekly'
            )

            if result.get('success'):
                analyzed += 1
                logger.info(f"Weekly analysis for suggestion #{suggestion.id}: score={result.get('effectiveness_score')}")
            else:
                failed += 1

        except Exception as e:
            logger.error(f"Weekly analysis failed for suggestion #{suggestion.id}: {e}")
            failed += 1

    logger.info(f"🔍 Weekly analysis completed: {analyzed} analyzed, {failed} failed")
    return {'analyzed': analyzed, 'failed': failed}


@shared_task
def auto_complete_old_tracking():
    """
    오래된 추적 자동 완료

    스케줄: 매주 일요일 00:00
    - 90일 이상 추적된 제안 자동 완료
    - 최종 분석 실행 후 상태를 'tracked'로 변경
    """
    from .services.suggestion_tracking import suggestion_tracking_service

    logger.info("🏁 Starting auto-complete for old tracking...")

    try:
        result = suggestion_tracking_service.auto_complete_old_tracking(max_days=90)

        logger.info(f"🏁 Auto-complete finished: {result.get('completed', 0)} suggestions completed")

        return result

    except Exception as e:
        logger.error(f"Auto-complete failed: {e}", exc_info=True)
        return {'error': True, 'message': str(e)}
