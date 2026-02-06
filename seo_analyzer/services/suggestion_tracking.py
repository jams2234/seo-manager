"""
AI 제안 지속 추적 서비스
제안 적용 후 SEO 데이터 변화를 지속적으로 모니터링하고 효과를 분석
"""
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
from django.utils import timezone
from django.db import transaction
from django.db.models import Avg, Sum, Count

from ..models import (
    AISuggestion, SuggestionTrackingSnapshot, SuggestionEffectivenessLog,
    Page, SEOMetrics, SEOAnalysisReport, Domain
)
from .search_console import SearchConsoleService
from .ai.claude_client import ClaudeAPIClient

logger = logging.getLogger(__name__)


class SuggestionTrackingService:
    """
    AI 제안 추적 서비스

    주요 기능:
    - 추적 시작: baseline 메트릭 캡처
    - 일일 스냅샷: GSC + SEO 메트릭 수집
    - 효과 분석: Claude API로 AI 분석
    - 추적 종료: 최종 분석 및 학습
    """

    def __init__(self):
        self.gsc_service = None  # Lazy initialization
        self.claude_client = None

    def _get_gsc_service(self):
        """GSC 서비스 지연 초기화"""
        if self.gsc_service is None:
            self.gsc_service = SearchConsoleService()
        return self.gsc_service

    def _get_claude_client(self):
        """Claude 클라이언트 지연 초기화"""
        if self.claude_client is None:
            self.claude_client = ClaudeAPIClient()
        return self.claude_client

    # ==============================
    # 1. 추적 시작
    # ==============================

    def start_tracking(self, suggestion_id: int) -> Dict:
        """
        제안 추적 시작

        1. 상태를 'tracking'으로 변경
        2. 현재 baseline_metrics 캡처
        3. 추적 시작 시간 기록

        Args:
            suggestion_id: AISuggestion ID

        Returns:
            {
                'success': True/False,
                'message': '...',
                'baseline_metrics': {...},
                'tracking_started_at': '...'
            }
        """
        try:
            suggestion = AISuggestion.objects.select_related('domain', 'page').get(id=suggestion_id)

            # 이미 추적 중이면 에러
            if suggestion.status == 'tracking':
                return {
                    'success': False,
                    'message': '이미 추적 중인 제안입니다.',
                    'suggestion_id': suggestion_id
                }

            # applied 상태에서만 추적 시작 가능
            if suggestion.status != 'applied':
                return {
                    'success': False,
                    'message': f'적용 완료된 제안만 추적 가능합니다. (현재 상태: {suggestion.status})',
                    'suggestion_id': suggestion_id
                }

            # baseline 메트릭 캡처
            baseline = self._capture_current_metrics(suggestion)

            # 상태 업데이트
            now = timezone.now()
            suggestion.status = 'tracking'
            suggestion.tracking_started_at = now
            suggestion.baseline_metrics = baseline
            suggestion.save(update_fields=[
                'status', 'tracking_started_at', 'baseline_metrics', 'updated_at'
            ])

            logger.info(f"✅ Started tracking for suggestion #{suggestion_id}")

            return {
                'success': True,
                'message': '추적이 시작되었습니다.',
                'suggestion_id': suggestion_id,
                'baseline_metrics': baseline,
                'tracking_started_at': now.isoformat()
            }

        except AISuggestion.DoesNotExist:
            return {
                'success': False,
                'message': f'제안을 찾을 수 없습니다. (ID: {suggestion_id})'
            }
        except Exception as e:
            logger.error(f"Error starting tracking for suggestion #{suggestion_id}: {e}")
            return {
                'success': False,
                'message': f'추적 시작 실패: {str(e)}'
            }

    def _capture_current_metrics(self, suggestion: AISuggestion) -> Dict:
        """
        현재 시점의 메트릭 캡처

        Args:
            suggestion: AISuggestion 인스턴스

        Returns:
            {
                'impressions': 100,
                'clicks': 10,
                'ctr': 10.0,
                'position': 5.2,
                'seo_score': 85,
                'health_score': 78,
                'keywords_count': 5,
                'captured_at': '2026-02-06T12:00:00Z'
            }
        """
        metrics = {
            'impressions': 0,
            'clicks': 0,
            'ctr': 0,
            'position': 0,
            'seo_score': None,
            'performance_score': None,
            'health_score': None,
            'keywords_count': 0,
            'captured_at': timezone.now().isoformat()
        }

        domain = suggestion.domain
        page = suggestion.page

        # 1. GSC 데이터 가져오기 (30일 범위로 bulk 조회 후 페이지 매칭)
        try:
            gsc = self._get_gsc_service()
            site_url = f"sc-domain:{domain.domain_name}"

            if page:
                # get_all_page_analytics로 30일 데이터 조회 (더 정확함)
                all_pages_result = gsc.get_all_page_analytics(site_url)

                if not all_pages_result.get('error'):
                    pages_data = all_pages_result.get('pages', {})
                    page_url = page.url

                    # URL 매칭 (trailing slash 처리)
                    page_metrics = pages_data.get(page_url)
                    if not page_metrics and page_url.endswith('/'):
                        page_metrics = pages_data.get(page_url.rstrip('/'))
                    if not page_metrics and not page_url.endswith('/'):
                        page_metrics = pages_data.get(page_url + '/')

                    if page_metrics:
                        metrics['impressions'] = page_metrics.get('impressions', 0)
                        metrics['clicks'] = page_metrics.get('clicks', 0)
                        metrics['ctr'] = page_metrics.get('ctr', 0)
                        metrics['position'] = page_metrics.get('position', 0)

                        # 키워드 수는 별도 조회
                        try:
                            page_detail = gsc.get_page_analytics(site_url, page_url)
                            if not page_detail.get('error'):
                                metrics['keywords_count'] = page_detail.get('query_count', 0)
                        except Exception:
                            pass
            else:
                # 도메인 레벨 데이터 (페이지가 없는 경우)
                all_pages_result = gsc.get_all_page_analytics(site_url)

                if not all_pages_result.get('error'):
                    pages_data = all_pages_result.get('pages', {})
                    if pages_data:
                        metrics['impressions'] = sum(p.get('impressions', 0) for p in pages_data.values())
                        metrics['clicks'] = sum(p.get('clicks', 0) for p in pages_data.values())
                        total_impressions = metrics['impressions']
                        if total_impressions > 0:
                            metrics['ctr'] = round((metrics['clicks'] / total_impressions) * 100, 2)
                        positions = [p.get('position', 0) for p in pages_data.values() if p.get('position')]
                        if positions:
                            metrics['position'] = round(sum(positions) / len(positions), 1)

        except Exception as e:
            logger.warning(f"GSC data fetch failed: {e}")

        # 2. SEO 스코어 가져오기
        if page:
            try:
                latest_metrics = page.seo_metrics.order_by('-snapshot_date').first()
                if latest_metrics:
                    metrics['seo_score'] = latest_metrics.seo_score
                    metrics['performance_score'] = latest_metrics.performance_score

                latest_report = page.seo_reports.order_by('-analyzed_at').first()
                if latest_report:
                    metrics['health_score'] = latest_report.overall_health_score

            except Exception as e:
                logger.warning(f"SEO metrics fetch failed: {e}")

        return metrics

    # ==============================
    # 2. 일일 스냅샷 캡처
    # ==============================

    def capture_daily_snapshot(self, suggestion_id: int) -> Dict:
        """
        추적중인 제안의 일일 스냅샷 캡처

        Args:
            suggestion_id: AISuggestion ID

        Returns:
            {
                'success': True/False,
                'snapshot': {...},
                'day_number': N
            }
        """
        try:
            suggestion = AISuggestion.objects.select_related('domain', 'page').get(id=suggestion_id)

            if suggestion.status != 'tracking':
                return {
                    'success': False,
                    'message': f'추적 중인 제안이 아닙니다. (상태: {suggestion.status})'
                }

            today = date.today()

            # 이미 오늘 스냅샷이 있는지 확인
            existing = SuggestionTrackingSnapshot.objects.filter(
                suggestion=suggestion,
                date=today
            ).first()

            if existing:
                return {
                    'success': True,
                    'message': '오늘 스냅샷이 이미 존재합니다.',
                    'snapshot': self._snapshot_to_dict(existing),
                    'day_number': existing.day_number
                }

            # 현재 메트릭 캡처
            current_metrics = self._capture_current_metrics(suggestion)
            baseline = suggestion.baseline_metrics or {}

            # day_number 계산
            if suggestion.tracking_started_at:
                delta = today - suggestion.tracking_started_at.date()
                day_number = delta.days + 1
            else:
                day_number = suggestion.tracking_days + 1

            # 변화량 계산
            changes = self._calculate_changes(baseline, current_metrics)

            # 스냅샷 생성
            snapshot = SuggestionTrackingSnapshot.objects.create(
                suggestion=suggestion,
                date=today,
                day_number=day_number,
                impressions=current_metrics.get('impressions', 0),
                clicks=current_metrics.get('clicks', 0),
                ctr=current_metrics.get('ctr'),
                avg_position=current_metrics.get('position'),
                seo_score=current_metrics.get('seo_score'),
                performance_score=current_metrics.get('performance_score'),
                health_score=current_metrics.get('health_score'),
                keywords_count=current_metrics.get('keywords_count', 0),
                impressions_change=changes.get('impressions_change', 0),
                clicks_change=changes.get('clicks_change', 0),
                ctr_change=changes.get('ctr_change'),
                position_change=changes.get('position_change'),
                seo_score_change=changes.get('seo_score_change'),
                impressions_change_percent=changes.get('impressions_change_percent'),
                clicks_change_percent=changes.get('clicks_change_percent'),
            )

            # tracking_days 업데이트
            suggestion.tracking_days = day_number
            suggestion.save(update_fields=['tracking_days', 'updated_at'])

            logger.info(f"📊 Captured snapshot day {day_number} for suggestion #{suggestion_id}")

            return {
                'success': True,
                'message': f'Day {day_number} 스냅샷이 저장되었습니다.',
                'snapshot': self._snapshot_to_dict(snapshot),
                'day_number': day_number
            }

        except AISuggestion.DoesNotExist:
            return {
                'success': False,
                'message': f'제안을 찾을 수 없습니다. (ID: {suggestion_id})'
            }
        except Exception as e:
            logger.error(f"Error capturing snapshot for suggestion #{suggestion_id}: {e}")
            return {
                'success': False,
                'message': f'스냅샷 캡처 실패: {str(e)}'
            }

    def _calculate_changes(self, baseline: Dict, current: Dict) -> Dict:
        """baseline 대비 변화량 계산"""
        changes = {}

        # 노출수 변화
        base_imp = baseline.get('impressions', 0)
        curr_imp = current.get('impressions', 0)
        changes['impressions_change'] = curr_imp - base_imp
        if base_imp > 0:
            changes['impressions_change_percent'] = round(((curr_imp - base_imp) / base_imp) * 100, 1)
        else:
            changes['impressions_change_percent'] = 100.0 if curr_imp > 0 else 0

        # 클릭수 변화
        base_clicks = baseline.get('clicks', 0)
        curr_clicks = current.get('clicks', 0)
        changes['clicks_change'] = curr_clicks - base_clicks
        if base_clicks > 0:
            changes['clicks_change_percent'] = round(((curr_clicks - base_clicks) / base_clicks) * 100, 1)
        else:
            changes['clicks_change_percent'] = 100.0 if curr_clicks > 0 else 0

        # CTR 변화 (퍼센트 포인트)
        base_ctr = baseline.get('ctr', 0) or 0
        curr_ctr = current.get('ctr', 0) or 0
        changes['ctr_change'] = round(curr_ctr - base_ctr, 2)

        # 순위 변화 (음수 = 순위 상승)
        base_pos = baseline.get('position', 0) or 0
        curr_pos = current.get('position', 0) or 0
        if base_pos > 0 and curr_pos > 0:
            changes['position_change'] = round(curr_pos - base_pos, 1)
        else:
            changes['position_change'] = None

        # SEO 점수 변화
        base_seo = baseline.get('seo_score')
        curr_seo = current.get('seo_score')
        if base_seo is not None and curr_seo is not None:
            changes['seo_score_change'] = round(curr_seo - base_seo, 1)
        else:
            changes['seo_score_change'] = None

        return changes

    def _snapshot_to_dict(self, snapshot: SuggestionTrackingSnapshot) -> Dict:
        """스냅샷을 딕셔너리로 변환"""
        return {
            'id': snapshot.id,
            'date': snapshot.date.isoformat(),
            'day_number': snapshot.day_number,
            'impressions': snapshot.impressions,
            'clicks': snapshot.clicks,
            'ctr': snapshot.ctr,
            'avg_position': snapshot.avg_position,
            'seo_score': snapshot.seo_score,
            'performance_score': snapshot.performance_score,
            'health_score': snapshot.health_score,
            'keywords_count': snapshot.keywords_count,
            'impressions_change': snapshot.impressions_change,
            'clicks_change': snapshot.clicks_change,
            'ctr_change': snapshot.ctr_change,
            'position_change': snapshot.position_change,
            'seo_score_change': snapshot.seo_score_change,
            'impressions_change_percent': snapshot.impressions_change_percent,
            'clicks_change_percent': snapshot.clicks_change_percent,
        }

    # ==============================
    # 3. 추적중인 모든 제안 스냅샷 캡처
    # ==============================

    def capture_all_tracking_snapshots(self) -> Dict:
        """
        추적중인 모든 제안에 대해 일일 스냅샷 캡처
        Celery 태스크에서 호출됨

        Returns:
            {
                'success': True,
                'captured': N,
                'failed': N,
                'skipped': N
            }
        """
        tracking_suggestions = AISuggestion.objects.filter(status='tracking')

        results = {
            'captured': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }

        for suggestion in tracking_suggestions:
            result = self.capture_daily_snapshot(suggestion.id)

            if result.get('success'):
                if '이미 존재' in result.get('message', ''):
                    results['skipped'] += 1
                else:
                    results['captured'] += 1
            else:
                results['failed'] += 1

            results['details'].append({
                'suggestion_id': suggestion.id,
                'success': result.get('success'),
                'message': result.get('message')
            })

        logger.info(f"📊 Daily snapshot batch: {results['captured']} captured, {results['skipped']} skipped, {results['failed']} failed")

        return {
            'success': True,
            **results
        }

    # ==============================
    # 4. 효과 분석
    # ==============================

    def analyze_impact(self, suggestion_id: int, analysis_type: str = 'manual') -> Dict:
        """
        제안의 효과 분석 실행

        Args:
            suggestion_id: AISuggestion ID
            analysis_type: 'weekly', 'milestone', 'final', 'manual'

        Returns:
            {
                'success': True/False,
                'analysis': {...},
                'effectiveness_score': 75.5
            }
        """
        try:
            suggestion = AISuggestion.objects.select_related('domain', 'page').get(id=suggestion_id)

            if suggestion.status not in ['tracking', 'tracked']:
                return {
                    'success': False,
                    'message': '추적 중이거나 추적 완료된 제안만 분석 가능합니다.'
                }

            # 스냅샷 데이터 수집
            snapshots = SuggestionTrackingSnapshot.objects.filter(
                suggestion=suggestion
            ).order_by('day_number')

            if not snapshots.exists():
                return {
                    'success': False,
                    'message': '분석할 스냅샷 데이터가 없습니다.'
                }

            # 메트릭 비교 데이터 준비
            baseline = suggestion.baseline_metrics or {}
            latest_snapshot = snapshots.last()

            current_metrics = {
                'impressions': latest_snapshot.impressions,
                'clicks': latest_snapshot.clicks,
                'ctr': latest_snapshot.ctr,
                'position': latest_snapshot.avg_position,
                'seo_score': latest_snapshot.seo_score,
                'health_score': latest_snapshot.health_score,
            }

            changes = self._calculate_metric_changes(baseline, current_metrics)

            # AI 분석 실행
            ai_analysis = self._run_ai_analysis(suggestion, snapshots, changes)

            # 효과성 점수 계산
            effectiveness_score = self._calculate_effectiveness_score(changes, ai_analysis)

            # 트렌드 방향 결정
            trend_direction = self._determine_trend(snapshots)

            # 경과 일수
            days_since_applied = latest_snapshot.day_number if latest_snapshot else 0

            # 효과성 로그 저장
            log = SuggestionEffectivenessLog.objects.create(
                suggestion=suggestion,
                analysis_type=analysis_type,
                days_since_applied=days_since_applied,
                baseline_metrics=baseline,
                current_metrics=current_metrics,
                changes=changes,
                ai_analysis=ai_analysis,
                effectiveness_score=effectiveness_score,
                trend_direction=trend_direction
            )

            # 제안에 최신 분석 결과 저장
            suggestion.impact_analysis = ai_analysis
            suggestion.effectiveness_score = effectiveness_score
            suggestion.save(update_fields=['impact_analysis', 'effectiveness_score', 'updated_at'])

            logger.info(f"🔍 Impact analysis completed for suggestion #{suggestion_id}: score={effectiveness_score}")

            return {
                'success': True,
                'message': '효과 분석이 완료되었습니다.',
                'analysis': ai_analysis,
                'changes': changes,
                'effectiveness_score': effectiveness_score,
                'trend_direction': trend_direction,
                'days_since_applied': days_since_applied,
                'log_id': log.id
            }

        except AISuggestion.DoesNotExist:
            return {
                'success': False,
                'message': f'제안을 찾을 수 없습니다. (ID: {suggestion_id})'
            }
        except Exception as e:
            logger.error(f"Error analyzing impact for suggestion #{suggestion_id}: {e}")
            return {
                'success': False,
                'message': f'효과 분석 실패: {str(e)}'
            }

    def _calculate_metric_changes(self, baseline: Dict, current: Dict) -> Dict:
        """메트릭 변화량 상세 계산"""
        changes = {}

        metrics = ['impressions', 'clicks', 'ctr', 'position', 'seo_score', 'health_score']

        for metric in metrics:
            base_val = baseline.get(metric)
            curr_val = current.get(metric)

            if base_val is None or curr_val is None:
                changes[metric] = {'value': None, 'percent': None, 'direction': 'unknown'}
                continue

            diff = curr_val - base_val

            # 퍼센트 계산
            if base_val != 0:
                percent = round((diff / abs(base_val)) * 100, 1)
            else:
                percent = 100.0 if diff > 0 else (0 if diff == 0 else -100.0)

            # 방향 결정 (position은 반대)
            if metric == 'position':
                # 순위는 낮을수록 좋음
                direction = 'up' if diff < 0 else ('down' if diff > 0 else 'stable')
            else:
                direction = 'up' if diff > 0 else ('down' if diff < 0 else 'stable')

            changes[metric] = {
                'value': round(diff, 2),
                'percent': percent,
                'direction': direction
            }

        return changes

    def _run_ai_analysis(
        self,
        suggestion: AISuggestion,
        snapshots,
        changes: Dict
    ) -> Dict:
        """Claude API로 효과 분석"""
        try:
            claude = self._get_claude_client()

            # 분석 컨텍스트 구성
            snapshot_data = [
                {
                    'day': s.day_number,
                    'date': s.date.isoformat(),
                    'impressions': s.impressions,
                    'clicks': s.clicks,
                    'ctr': s.ctr,
                    'position': s.avg_position,
                    'seo_score': s.seo_score,
                }
                for s in snapshots[:30]  # 최대 30일
            ]

            prompt = f"""
다음 SEO 제안의 적용 효과를 분석해주세요.

## 제안 정보
- 유형: {suggestion.get_suggestion_type_display()}
- 제목: {suggestion.title}
- 설명: {suggestion.description}
- 대상 페이지: {suggestion.page.url if suggestion.page else '도메인 전체'}

## 기준 메트릭 (적용 전)
{suggestion.baseline_metrics}

## 메트릭 변화
{changes}

## 일별 스냅샷 데이터
{snapshot_data}

## 분석 요청
1. 전체 효과 판정 (positive, negative, neutral, inconclusive)
2. 신뢰도 (0.0 ~ 1.0)
3. 효과 요약 (한 문장)
4. 상승/하락 요인 분석
5. 향후 권장사항

JSON 형식으로 응답해주세요:
{{
    "overall_effect": "positive|negative|neutral|inconclusive",
    "confidence": 0.0~1.0,
    "summary": "효과 요약 (한 문장)",
    "factors": [
        {{"factor": "요인명", "effect": "positive|negative|neutral", "confidence": 0.0~1.0, "description": "설명"}}
    ],
    "recommendations": ["권장사항1", "권장사항2"],
    "insights": ["인사이트1", "인사이트2"]
}}
"""

            response = claude.analyze_json(
                prompt=prompt,
                system="SEO 분석 전문가로서 데이터 기반 분석을 수행합니다. JSON 형식으로만 응답하세요."
            )

            if response.get('success') and response.get('parsed'):
                analysis = response['parsed']
                analysis['analyzed_at'] = timezone.now().isoformat()
                return analysis
            else:
                # Claude 분석 실패 시 기본 분석
                return self._basic_analysis(changes)

        except Exception as e:
            logger.warning(f"AI analysis failed: {e}")
            return self._basic_analysis(changes)

    def _basic_analysis(self, changes: Dict) -> Dict:
        """기본 분석 (AI 실패 시 fallback)"""
        positive_count = sum(
            1 for m, c in changes.items()
            if c.get('direction') == 'up'
        )
        negative_count = sum(
            1 for m, c in changes.items()
            if c.get('direction') == 'down'
        )

        if positive_count > negative_count:
            overall = 'positive'
        elif negative_count > positive_count:
            overall = 'negative'
        else:
            overall = 'neutral'

        return {
            'overall_effect': overall,
            'confidence': 0.5,
            'summary': f'메트릭 {positive_count}개 상승, {negative_count}개 하락',
            'factors': [],
            'recommendations': [],
            'insights': [],
            'analyzed_at': timezone.now().isoformat(),
            'is_basic_analysis': True
        }

    def _calculate_effectiveness_score(self, changes: Dict, ai_analysis: Dict) -> float:
        """효과성 점수 계산 (0-100)"""
        score = 50.0  # 기준점

        # 메트릭 변화에 따른 점수 조정
        weights = {
            'impressions': 25,
            'clicks': 25,
            'ctr': 20,
            'position': 15,
            'seo_score': 10,
            'health_score': 5,
        }

        for metric, weight in weights.items():
            change = changes.get(metric, {})
            direction = change.get('direction')
            percent = change.get('percent', 0) or 0

            if direction == 'up':
                # 상승 시 가점 (최대 weight * 0.5)
                bonus = min(weight * 0.5, weight * abs(percent) / 100)
                score += bonus
            elif direction == 'down':
                # 하락 시 감점 (최대 weight * 0.5)
                penalty = min(weight * 0.5, weight * abs(percent) / 100)
                score -= penalty

        # AI 분석 결과 반영
        if ai_analysis.get('overall_effect') == 'positive':
            score += 5 * ai_analysis.get('confidence', 0.5)
        elif ai_analysis.get('overall_effect') == 'negative':
            score -= 5 * ai_analysis.get('confidence', 0.5)

        # 범위 제한
        return max(0, min(100, round(score, 1)))

    def _determine_trend(self, snapshots) -> str:
        """스냅샷 데이터에서 트렌드 방향 결정"""
        if snapshots.count() < 3:
            return 'stable'

        # 최근 7일 vs 이전 7일 비교
        all_snapshots = list(snapshots)
        if len(all_snapshots) < 7:
            recent = all_snapshots[-3:]
            earlier = all_snapshots[:3]
        else:
            recent = all_snapshots[-7:]
            earlier = all_snapshots[:7]

        recent_avg = sum(s.impressions for s in recent) / len(recent)
        earlier_avg = sum(s.impressions for s in earlier) / len(earlier)

        if recent_avg > earlier_avg * 1.1:
            return 'improving'
        elif recent_avg < earlier_avg * 0.9:
            return 'declining'
        else:
            # 변동성 체크
            impressions = [s.impressions for s in all_snapshots]
            avg = sum(impressions) / len(impressions)
            variance = sum((x - avg) ** 2 for x in impressions) / len(impressions)
            std_dev = variance ** 0.5

            if std_dev > avg * 0.3:
                return 'volatile'
            return 'stable'

    # ==============================
    # 5. 추적 종료
    # ==============================

    def end_tracking(self, suggestion_id: int, run_final_analysis: bool = True) -> Dict:
        """
        추적 종료

        Args:
            suggestion_id: AISuggestion ID
            run_final_analysis: 최종 분석 실행 여부

        Returns:
            {
                'success': True/False,
                'final_metrics': {...},
                'impact_analysis': {...}
            }
        """
        try:
            suggestion = AISuggestion.objects.select_related('domain', 'page').get(id=suggestion_id)

            if suggestion.status != 'tracking':
                return {
                    'success': False,
                    'message': f'추적 중인 제안이 아닙니다. (상태: {suggestion.status})'
                }

            now = timezone.now()

            # 최종 메트릭 캡처
            final_metrics = self._capture_current_metrics(suggestion)

            # 최종 분석 실행
            if run_final_analysis:
                analysis_result = self.analyze_impact(suggestion_id, analysis_type='final')
            else:
                analysis_result = {}

            # 상태 업데이트
            suggestion.status = 'tracked'
            suggestion.tracking_ended_at = now
            suggestion.final_metrics = final_metrics

            if analysis_result.get('success'):
                suggestion.impact_analysis = analysis_result.get('analysis', {})
                suggestion.effectiveness_score = analysis_result.get('effectiveness_score')

            suggestion.save()

            logger.info(f"✅ Ended tracking for suggestion #{suggestion_id} after {suggestion.tracking_days} days")

            return {
                'success': True,
                'message': f'추적이 종료되었습니다. (총 {suggestion.tracking_days}일)',
                'suggestion_id': suggestion_id,
                'tracking_days': suggestion.tracking_days,
                'final_metrics': final_metrics,
                'impact_analysis': suggestion.impact_analysis,
                'effectiveness_score': suggestion.effectiveness_score
            }

        except AISuggestion.DoesNotExist:
            return {
                'success': False,
                'message': f'제안을 찾을 수 없습니다. (ID: {suggestion_id})'
            }
        except Exception as e:
            logger.error(f"Error ending tracking for suggestion #{suggestion_id}: {e}")
            return {
                'success': False,
                'message': f'추적 종료 실패: {str(e)}'
            }

    # ==============================
    # 6. 추적 데이터 조회
    # ==============================

    def get_tracking_data(self, suggestion_id: int) -> Dict:
        """
        추적 데이터 조회 (프론트엔드용)

        Args:
            suggestion_id: AISuggestion ID

        Returns:
            {
                'success': True,
                'suggestion': {...},
                'baseline': {...},
                'current': {...},
                'snapshots': [...],
                'analysis_logs': [...],
                'chart_data': {...}
            }
        """
        try:
            suggestion = AISuggestion.objects.select_related('domain', 'page').get(id=suggestion_id)

            # 스냅샷 데이터
            snapshots = SuggestionTrackingSnapshot.objects.filter(
                suggestion=suggestion
            ).order_by('day_number')

            # 분석 로그
            analysis_logs = SuggestionEffectivenessLog.objects.filter(
                suggestion=suggestion
            ).order_by('-created_at')[:10]

            # 차트 데이터 구성
            chart_data = self._build_chart_data(snapshots)

            # 요약 통계
            summary_stats = self._calculate_summary_stats(suggestion, snapshots)

            return {
                'success': True,
                'suggestion': {
                    'id': suggestion.id,
                    'title': suggestion.title,
                    'type': suggestion.suggestion_type,
                    'status': suggestion.status,
                    'page_url': suggestion.page.url if suggestion.page else None,
                    'tracking_days': suggestion.tracking_days,
                    'tracking_started_at': suggestion.tracking_started_at.isoformat() if suggestion.tracking_started_at else None,
                    'effectiveness_score': suggestion.effectiveness_score,
                },
                'baseline': suggestion.baseline_metrics,
                'current': self._capture_current_metrics(suggestion) if suggestion.status == 'tracking' else suggestion.final_metrics,
                'snapshots': [self._snapshot_to_dict(s) for s in snapshots],
                'analysis_logs': [
                    {
                        'id': log.id,
                        'type': log.analysis_type,
                        'days_since_applied': log.days_since_applied,
                        'effectiveness_score': log.effectiveness_score,
                        'trend_direction': log.trend_direction,
                        'summary': log.ai_analysis.get('summary') if log.ai_analysis else None,
                        'created_at': log.created_at.isoformat()
                    }
                    for log in analysis_logs
                ],
                'chart_data': chart_data,
                'summary': summary_stats
            }

        except AISuggestion.DoesNotExist:
            return {
                'success': False,
                'message': f'제안을 찾을 수 없습니다. (ID: {suggestion_id})'
            }
        except Exception as e:
            logger.error(f"Error getting tracking data for suggestion #{suggestion_id}: {e}")
            return {
                'success': False,
                'message': f'추적 데이터 조회 실패: {str(e)}'
            }

    def _build_chart_data(self, snapshots) -> Dict:
        """차트용 데이터 구성"""
        return {
            'labels': [s.date.isoformat() for s in snapshots],
            'impressions': [s.impressions for s in snapshots],
            'clicks': [s.clicks for s in snapshots],
            'ctr': [s.ctr for s in snapshots],
            'position': [s.avg_position for s in snapshots],
            'seo_score': [s.seo_score for s in snapshots],
            'health_score': [s.health_score for s in snapshots],
        }

    def _calculate_summary_stats(self, suggestion: AISuggestion, snapshots) -> Dict:
        """요약 통계 계산"""
        if not snapshots.exists():
            return {}

        baseline = suggestion.baseline_metrics or {}

        # 평균 계산
        avg_impressions = snapshots.aggregate(avg=Avg('impressions'))['avg'] or 0
        avg_clicks = snapshots.aggregate(avg=Avg('clicks'))['avg'] or 0

        # 최신 vs 기준 비교
        latest = snapshots.last()

        return {
            'tracking_days': suggestion.tracking_days,
            'total_snapshots': snapshots.count(),
            'avg_impressions': round(avg_impressions, 1),
            'avg_clicks': round(avg_clicks, 1),
            'baseline_impressions': baseline.get('impressions', 0),
            'current_impressions': latest.impressions if latest else 0,
            'impressions_change_percent': latest.impressions_change_percent if latest else 0,
            'overall_trend': suggestion.impact_analysis.get('overall_effect') if suggestion.impact_analysis else None,
        }

    # ==============================
    # 7. 추적중인 제안 목록
    # ==============================

    def get_tracking_list(self, domain_id: int = None) -> Dict:
        """
        추적중인 제안 목록 조회

        Args:
            domain_id: 도메인 ID (선택)

        Returns:
            {
                'success': True,
                'tracking_count': N,
                'suggestions': [...]
            }
        """
        queryset = AISuggestion.objects.filter(
            status='tracking'
        ).select_related('domain', 'page')

        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)

        suggestions = []
        for s in queryset:
            latest_snapshot = s.tracking_snapshots.order_by('-day_number').first()

            suggestions.append({
                'id': s.id,
                'title': s.title,
                'type': s.suggestion_type,
                'domain_name': s.domain.domain_name,
                'page_url': s.page.url if s.page else None,
                'tracking_days': s.tracking_days,
                'tracking_started_at': s.tracking_started_at.isoformat() if s.tracking_started_at else None,
                'latest_snapshot': self._snapshot_to_dict(latest_snapshot) if latest_snapshot else None,
                'effectiveness_score': s.effectiveness_score,
            })

        return {
            'success': True,
            'tracking_count': len(suggestions),
            'suggestions': suggestions
        }

    # ==============================
    # 8. 자동 완료 (90일 초과)
    # ==============================

    def auto_complete_old_tracking(self, max_days: int = 90) -> Dict:
        """
        오래된 추적 자동 완료

        Args:
            max_days: 최대 추적 일수 (기본 90일)

        Returns:
            {
                'success': True,
                'completed': N
            }
        """
        cutoff_date = timezone.now() - timedelta(days=max_days)

        old_suggestions = AISuggestion.objects.filter(
            status='tracking',
            tracking_started_at__lt=cutoff_date
        )

        completed = 0
        for suggestion in old_suggestions:
            result = self.end_tracking(suggestion.id, run_final_analysis=True)
            if result.get('success'):
                completed += 1

        logger.info(f"🏁 Auto-completed {completed} old tracking suggestions")

        return {
            'success': True,
            'completed': completed
        }


# 싱글톤 인스턴스
suggestion_tracking_service = SuggestionTrackingService()
