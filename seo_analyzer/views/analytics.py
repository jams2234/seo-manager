"""
Analytics API Views
도메인 및 페이지별 SEO 성과 추적 대시보드 API
"""
import logging
from datetime import timedelta, datetime
from collections import defaultdict

from django.db.models import Avg, Sum, Count, F, Max, Min
from django.db.models.functions import TruncDate, TruncWeek
from django.utils import timezone
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from celery.schedules import crontab

from ..models import Domain, Page, SEOMetrics, SEOIssue, AIFixHistory, SEOAnalysisReport, DailyTrafficSnapshot
from ..services.search_console import SearchConsoleService

logger = logging.getLogger(__name__)


class AnalyticsViewSet(viewsets.ViewSet):
    """
    도메인 및 페이지별 SEO 성과 분석 API

    Endpoints:
    - GET /analytics/domain_overview/ - 도메인 전체 개요
    - GET /analytics/page_trends/ - 페이지별 SEO 트렌드
    - GET /analytics/keyword_trends/ - 키워드 노출 트렌드
    - GET /analytics/comparison/ - 시작 vs 현재 비교
    """

    @action(detail=False, methods=['get'])
    def domain_overview(self, request):
        """
        도메인 전체 개요 - 종합 스코어 및 트렌드

        Query params:
        - domain_id: 도메인 ID (필수)
        - days: 조회 기간 (기본 30일)
        """
        domain_id = request.query_params.get('domain_id')
        days = int(request.query_params.get('days', 30))

        if not domain_id:
            return Response({'error': 'domain_id is required'}, status=400)

        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            return Response({'error': 'Domain not found'}, status=404)

        # 기간 설정
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        # 페이지 목록
        pages = Page.objects.filter(domain=domain).prefetch_related('seo_metrics')

        # 도메인 전체 트렌드 (일별 평균)
        domain_trends = self._get_domain_trends(domain, start_date, end_date)

        # 현재 도메인 상태
        current_stats = self._get_current_domain_stats(domain)

        # 시작 시점 vs 현재 비교
        comparison = self._get_start_vs_current(domain, start_date)

        # 페이지 수
        page_count = pages.count()
        synced_pages = pages.filter(seo_metrics__isnull=False).distinct().count()

        return Response({
            'domain': {
                'id': domain.id,
                'name': domain.domain_name,
                'page_count': page_count,
                'synced_pages': synced_pages,
            },
            'current_stats': current_stats,
            'comparison': comparison,
            'trends': domain_trends,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days,
            }
        })

    @action(detail=False, methods=['get'])
    def page_trends(self, request):
        """
        페이지별 SEO 트렌드 리스트

        Query params:
        - domain_id: 도메인 ID (필수)
        - days: 조회 기간 (기본 30일)
        - limit: 페이지 수 제한 (기본 50)
        """
        domain_id = request.query_params.get('domain_id')
        days = int(request.query_params.get('days', 30))
        limit = int(request.query_params.get('limit', 50))

        if not domain_id:
            return Response({'error': 'domain_id is required'}, status=400)

        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            return Response({'error': 'Domain not found'}, status=404)

        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        # 모든 페이지 가져오기
        pages = Page.objects.filter(domain=domain)[:limit]

        page_data = []
        for page in pages:
            trends = self._get_page_trends(page, start_date, end_date)
            comparison = self._get_page_comparison(page, start_date)

            # 실제 이슈 기반 Health Score (SEOAnalysisReport에서)
            latest_report = page.seo_reports.order_by('-analyzed_at').first()
            actual_health_score = latest_report.overall_health_score if latest_report else None

            page_data.append({
                'page_id': page.id,
                'url': page.url,
                'path': page.path,
                'title': page.title,
                'depth_level': page.depth_level,
                'actual_health_score': actual_health_score,  # 이슈 기반 (SEOIssuesPanel과 동일)
                'trends': trends,
                'comparison': comparison,
            })

        return Response({
            'domain_id': domain.id,
            'domain_name': domain.domain_name,
            'pages': page_data,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days,
            }
        })

    @action(detail=False, methods=['get'])
    def keyword_trends(self, request):
        """
        키워드 노출 트렌드

        Query params:
        - domain_id: 도메인 ID (필수)
        - days: 조회 기간 (기본 30일)
        """
        domain_id = request.query_params.get('domain_id')
        days = int(request.query_params.get('days', 30))

        if not domain_id:
            return Response({'error': 'domain_id is required'}, status=400)

        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            return Response({'error': 'Domain not found'}, status=404)

        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        # 페이지별 top_queries 수집
        pages = Page.objects.filter(domain=domain)

        keyword_data = defaultdict(lambda: {
            'impressions': 0,
            'clicks': 0,
            'pages': [],
            'first_seen': None,
            'last_seen': None,
        })

        for page in pages:
            metrics = page.seo_metrics.filter(
                snapshot_date__gte=start_date
            ).order_by('-snapshot_date')

            for metric in metrics:
                if metric.top_queries:
                    for query_data in metric.top_queries[:10]:
                        # 'query' 또는 'keys[0]' 형식 모두 지원
                        keyword = query_data.get('query') or (query_data.get('keys', [''])[0] if query_data.get('keys') else '')
                        if not keyword:
                            continue

                        kw_data = keyword_data[keyword]
                        kw_data['impressions'] += query_data.get('impressions', 0)
                        kw_data['clicks'] += query_data.get('clicks', 0)

                        if page.url not in kw_data['pages']:
                            kw_data['pages'].append(page.url)

                        snapshot_date = metric.snapshot_date
                        if not kw_data['first_seen'] or snapshot_date < kw_data['first_seen']:
                            kw_data['first_seen'] = snapshot_date
                        if not kw_data['last_seen'] or snapshot_date > kw_data['last_seen']:
                            kw_data['last_seen'] = snapshot_date

        # 상위 키워드 정렬
        sorted_keywords = sorted(
            keyword_data.items(),
            key=lambda x: x[1]['impressions'],
            reverse=True
        )[:50]

        keywords = []
        for keyword, data in sorted_keywords:
            keywords.append({
                'keyword': keyword,
                'impressions': data['impressions'],
                'clicks': data['clicks'],
                'ctr': (data['clicks'] / data['impressions'] * 100) if data['impressions'] > 0 else 0,
                'page_count': len(data['pages']),
                'pages': data['pages'][:5],  # 상위 5개 페이지만
                'first_seen': data['first_seen'].isoformat() if data['first_seen'] else None,
                'last_seen': data['last_seen'].isoformat() if data['last_seen'] else None,
            })

        return Response({
            'domain_id': domain.id,
            'keywords': keywords,
            'total_keywords': len(keyword_data),
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days,
            }
        })

    @action(detail=False, methods=['get'])
    def comparison(self, request):
        """
        시작 시점 vs 현재 상세 비교

        Query params:
        - domain_id: 도메인 ID (필수)
        """
        domain_id = request.query_params.get('domain_id')

        if not domain_id:
            return Response({'error': 'domain_id is required'}, status=400)

        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            return Response({'error': 'Domain not found'}, status=404)

        pages = Page.objects.filter(domain=domain)

        comparison_data = []
        total_improvement = {
            'seo_score': 0,
            'impressions': 0,
            'clicks': 0,
            'keywords': 0,
            'pages_improved': 0,
            'pages_declined': 0,
        }

        for page in pages:
            metrics = page.seo_metrics.order_by('snapshot_date')

            if metrics.count() < 2:
                continue

            first = metrics.first()
            latest = metrics.last()

            # 변화량 계산
            seo_change = (latest.seo_score or 0) - (first.seo_score or 0)
            impressions_change = (latest.impressions or 0) - (first.impressions or 0)
            clicks_change = (latest.clicks or 0) - (first.clicks or 0)

            # 키워드 수 변화
            first_keywords = len(first.top_queries) if first.top_queries else 0
            latest_keywords = len(latest.top_queries) if latest.top_queries else 0
            keywords_change = latest_keywords - first_keywords

            comparison_data.append({
                'page_id': page.id,
                'url': page.url,
                'path': page.path,
                'title': page.title,
                'first_snapshot': {
                    'date': first.snapshot_date.isoformat(),
                    'seo_score': first.seo_score,
                    'impressions': first.impressions,
                    'clicks': first.clicks,
                    'keywords_count': first_keywords,
                },
                'latest_snapshot': {
                    'date': latest.snapshot_date.isoformat(),
                    'seo_score': latest.seo_score,
                    'impressions': latest.impressions,
                    'clicks': latest.clicks,
                    'keywords_count': latest_keywords,
                },
                'changes': {
                    'seo_score': seo_change,
                    'impressions': impressions_change,
                    'clicks': clicks_change,
                    'keywords': keywords_change,
                },
                'improved': seo_change > 0,
            })

            # 전체 집계
            total_improvement['seo_score'] += seo_change
            total_improvement['impressions'] += impressions_change
            total_improvement['clicks'] += clicks_change
            total_improvement['keywords'] += keywords_change

            if seo_change > 0:
                total_improvement['pages_improved'] += 1
            elif seo_change < 0:
                total_improvement['pages_declined'] += 1

        # 평균 계산
        page_count = len(comparison_data)
        if page_count > 0:
            total_improvement['avg_seo_change'] = total_improvement['seo_score'] / page_count
        else:
            total_improvement['avg_seo_change'] = 0

        return Response({
            'domain_id': domain.id,
            'domain_name': domain.domain_name,
            'summary': total_improvement,
            'pages': comparison_data,
        })

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_domain_trends(self, domain, start_date, end_date):
        """도메인 전체 일별 트렌드 (SEOMetrics + 저장된 트래픽 데이터 병합)"""

        # 1. SEOMetrics에서 SEO/Performance 점수 가져오기
        # MySQL TruncDate 이슈로 Python에서 날짜 그룹핑
        metrics_raw = SEOMetrics.objects.filter(
            page__domain=domain,
            snapshot_date__gte=start_date,
            snapshot_date__lte=end_date,
        ).values('snapshot_date', 'seo_score', 'performance_score', 'page_id')

        # Python에서 날짜별 그룹핑
        metrics_by_date = {}
        for m in metrics_raw:
            if m['snapshot_date']:
                # timezone aware datetime을 local date로 변환
                local_dt = timezone.localtime(m['snapshot_date'])
                date_str = local_dt.strftime('%Y-%m-%d')

                if date_str not in metrics_by_date:
                    metrics_by_date[date_str] = {
                        'seo_scores': [],
                        'perf_scores': [],
                        'pages': set(),
                    }

                if m['seo_score'] is not None:
                    metrics_by_date[date_str]['seo_scores'].append(m['seo_score'])
                if m['performance_score'] is not None:
                    metrics_by_date[date_str]['perf_scores'].append(m['performance_score'])
                if m['page_id']:
                    metrics_by_date[date_str]['pages'].add(m['page_id'])

        # 평균 계산
        for date_str, data in metrics_by_date.items():
            seo_scores = data['seo_scores']
            perf_scores = data['perf_scores']
            metrics_by_date[date_str] = {
                'seo_score': round(sum(seo_scores) / len(seo_scores), 1) if seo_scores else None,
                'performance_score': round(sum(perf_scores) / len(perf_scores), 1) if perf_scores else None,
                'page_count': len(data['pages']),
            }

        # 2. 저장된 DailyTrafficSnapshot에서 트래픽 데이터 가져오기
        gsc_by_date = {}
        stored_snapshots = DailyTrafficSnapshot.objects.filter(
            domain=domain,
            date__gte=start_date.date() if hasattr(start_date, 'date') else start_date,
            date__lte=end_date.date() if hasattr(end_date, 'date') else end_date,
        ).order_by('date')

        for snapshot in stored_snapshots:
            date_str = snapshot.date.strftime('%Y-%m-%d')
            gsc_by_date[date_str] = {
                'impressions': snapshot.impressions,
                'clicks': snapshot.clicks,
                'ctr': round(snapshot.ctr * 100, 2) if snapshot.ctr else 0,
                'avg_position': round(snapshot.avg_position, 1) if snapshot.avg_position else 0,
            }

        # 3. 저장된 데이터가 없거나 부족하면 GSC API로 가져오기
        if len(gsc_by_date) < 7 and domain.search_console_connected:
            try:
                gsc = SearchConsoleService()
                site_url = f'sc-domain:{domain.domain_name}'

                # GSC API에 date 차원으로 쿼리
                gsc_result = gsc.get_search_analytics(
                    site_url=site_url,
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d'),
                    dimensions=['date'],
                    row_limit=500
                )

                if not gsc_result.get('error'):
                    for row in gsc_result.get('rows', []):
                        date_str = row.get('keys', [''])[0]
                        if date_str and date_str not in gsc_by_date:
                            gsc_by_date[date_str] = {
                                'impressions': row.get('impressions', 0),
                                'clicks': row.get('clicks', 0),
                                'ctr': round(row.get('ctr', 0) * 100, 2),
                                'avg_position': round(row.get('position', 0), 1),
                            }
                    logger.info(f"GSC daily trends fetched from API: {len(gsc_by_date)} days for {domain.domain_name}")
            except Exception as e:
                logger.warning(f"Failed to fetch GSC daily trends: {e}")

        # 3. 모든 날짜 수집 (SEOMetrics + GSC)
        all_dates = set(metrics_by_date.keys()) | set(gsc_by_date.keys())

        # 4. 병합하여 트렌드 생성
        trends = []
        for date_str in sorted(all_dates):
            seo_data = metrics_by_date.get(date_str, {})
            gsc_data = gsc_by_date.get(date_str, {})

            seo_score = seo_data.get('seo_score')
            performance_score = seo_data.get('performance_score')

            # Health Score 계산 (SEO + Performance 평균)
            health_score = None
            if seo_score is not None and performance_score is not None:
                health_score = (seo_score + performance_score) / 2
            elif seo_score is not None:
                health_score = seo_score

            trends.append({
                'date': date_str,
                'seo_score': seo_score,
                'health_score': round(health_score, 1) if health_score else None,
                'performance_score': performance_score,
                'impressions': gsc_data.get('impressions', 0),
                'clicks': gsc_data.get('clicks', 0),
                'ctr': gsc_data.get('ctr'),
                'avg_position': gsc_data.get('avg_position'),
                'page_count': seo_data.get('page_count', 0),
            })

        return trends

    def _get_current_domain_stats(self, domain):
        """현재 도메인 통계"""
        # 각 페이지의 최신 메트릭
        pages = Page.objects.filter(domain=domain)

        total_lighthouse_seo = 0
        total_health = 0
        total_performance = 0
        total_impressions = 0
        total_clicks = 0
        total_keywords = set()
        indexed_count = 0
        page_count = 0
        health_count = 0  # 실제 health score가 있는 페이지 수

        for page in pages:
            latest = page.seo_metrics.order_by('-snapshot_date').first()
            if latest:
                page_count += 1
                total_lighthouse_seo += latest.seo_score or 0
                total_performance += latest.performance_score or 0
                total_impressions += latest.impressions or 0
                total_clicks += latest.clicks or 0

                if latest.is_indexed:
                    indexed_count += 1

                if latest.top_queries:
                    for q in latest.top_queries:
                        # 'query' 또는 'keys[0]' 형식 모두 지원
                        keyword = q.get('query') or (q.get('keys', [''])[0] if q.get('keys') else '')
                        if keyword:
                            total_keywords.add(keyword)

            # 실제 이슈 기반 Health Score (SEOAnalysisReport에서)
            latest_report = page.seo_reports.order_by('-analyzed_at').first()
            if latest_report and latest_report.overall_health_score:
                total_health += latest_report.overall_health_score
                health_count += 1

        avg_lighthouse_seo = total_lighthouse_seo / page_count if page_count > 0 else 0
        avg_performance = total_performance / page_count if page_count > 0 else 0
        avg_health = total_health / health_count if health_count > 0 else 0
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0

        # 도메인 대표 스코어 (가중 평균)
        # Health Score(이슈 기반) 50% + Performance 25% + 인덱싱률 15% + CTR 10%
        indexing_rate = (indexed_count / page_count * 100) if page_count > 0 else 0
        domain_score = (
            avg_health * 0.5 +
            avg_performance * 0.25 +
            indexing_rate * 0.15 +
            min(ctr * 10, 100) * 0.10  # CTR은 10% = 100점으로 스케일
        )

        return {
            'lighthouse_seo_score': round(avg_lighthouse_seo, 1),  # Lighthouse 기술 점수
            'health_score': round(avg_health, 1),  # 이슈 기반 점수 (SEOIssuesPanel과 동일)
            'performance_score': round(avg_performance, 1),
            'domain_score': round(domain_score, 1),
            'impressions': total_impressions,
            'clicks': total_clicks,
            'ctr': round(ctr, 2),
            'keyword_count': len(total_keywords),
            'indexed_pages': indexed_count,
            'total_pages': page_count,
            'indexing_rate': round(indexing_rate, 1),
        }

    def _get_start_vs_current(self, domain, start_date):
        """시작 시점 vs 현재 비교"""
        pages = Page.objects.filter(domain=domain)

        start_stats = {'seo': 0, 'impressions': 0, 'clicks': 0, 'count': 0}
        current_stats = {'seo': 0, 'impressions': 0, 'clicks': 0, 'count': 0}
        # unique 키워드 수집을 위한 set
        start_keywords = set()
        current_keywords = set()

        for page in pages:
            # 시작 시점 (start_date 이후 첫 메트릭)
            first = page.seo_metrics.filter(
                snapshot_date__gte=start_date
            ).order_by('snapshot_date').first()

            # 현재 (최신 메트릭)
            latest = page.seo_metrics.order_by('-snapshot_date').first()

            if first:
                start_stats['seo'] += first.seo_score or 0
                start_stats['impressions'] += first.impressions or 0
                start_stats['clicks'] += first.clicks or 0
                start_stats['count'] += 1
                # unique 키워드 수집
                if first.top_queries:
                    for q in first.top_queries:
                        kw = q.get('query') or (q.get('keys', [''])[0] if q.get('keys') else '')
                        if kw:
                            start_keywords.add(kw)

            if latest:
                current_stats['seo'] += latest.seo_score or 0
                current_stats['impressions'] += latest.impressions or 0
                current_stats['clicks'] += latest.clicks or 0
                current_stats['count'] += 1
                # unique 키워드 수집
                if latest.top_queries:
                    for q in latest.top_queries:
                        kw = q.get('query') or (q.get('keys', [''])[0] if q.get('keys') else '')
                        if kw:
                            current_keywords.add(kw)

        # 평균 계산
        start_avg_seo = start_stats['seo'] / start_stats['count'] if start_stats['count'] > 0 else 0
        current_avg_seo = current_stats['seo'] / current_stats['count'] if current_stats['count'] > 0 else 0

        return {
            'start': {
                'date': start_date.isoformat(),
                'avg_seo_score': round(start_avg_seo, 1),
                'total_impressions': start_stats['impressions'],
                'total_clicks': start_stats['clicks'],
                'total_keywords': len(start_keywords),
                'page_count': start_stats['count'],
            },
            'current': {
                'avg_seo_score': round(current_avg_seo, 1),
                'total_impressions': current_stats['impressions'],
                'total_clicks': current_stats['clicks'],
                'total_keywords': len(current_keywords),
                'page_count': current_stats['count'],
            },
            'changes': {
                'seo_score': round(current_avg_seo - start_avg_seo, 1),
                'impressions': current_stats['impressions'] - start_stats['impressions'],
                'clicks': current_stats['clicks'] - start_stats['clicks'],
                'keywords': len(current_keywords) - len(start_keywords),
                'seo_percent': round((current_avg_seo - start_avg_seo) / start_avg_seo * 100, 1) if start_avg_seo > 0 else 0,
            }
        }

    def _get_page_trends(self, page, start_date, end_date):
        """페이지별 트렌드 데이터"""
        metrics = page.seo_metrics.filter(
            snapshot_date__gte=start_date,
            snapshot_date__lte=end_date,
        ).order_by('snapshot_date')

        trends = []
        for m in metrics:
            # Health Score
            health_score = None
            if m.seo_score is not None and m.performance_score is not None:
                health_score = (m.seo_score + m.performance_score) / 2
            elif m.seo_score is not None:
                health_score = m.seo_score

            # 상위 5개 키워드 추출
            # GSC API는 키워드를 'keys' 배열에 저장함 (예: {"keys": ["코인그리"], ...})
            top_keywords = []
            if m.top_queries:
                for q in m.top_queries[:5]:
                    # 'query' 또는 'keys[0]' 형식 모두 지원
                    query_text = q.get('query') or (q.get('keys', [''])[0] if q.get('keys') else '')
                    if query_text:  # 빈 문자열 제외
                        top_keywords.append({
                            'query': query_text,
                            'impressions': q.get('impressions', 0),
                            'clicks': q.get('clicks', 0),
                            'position': q.get('position', 0),
                        })

            trends.append({
                'date': m.snapshot_date.isoformat(),
                'seo_score': m.seo_score,
                'health_score': round(health_score, 1) if health_score else None,
                'performance_score': m.performance_score,
                'impressions': m.impressions or 0,
                'clicks': m.clicks or 0,
                'ctr': round(m.ctr, 2) if m.ctr else None,
                'keywords_count': len(m.top_queries) if m.top_queries else 0,
                'top_keywords': top_keywords,  # 키워드 목록 추가
            })

        return trends

    def _get_page_comparison(self, page, start_date):
        """페이지 시작 vs 현재 비교"""
        first = page.seo_metrics.filter(
            snapshot_date__gte=start_date
        ).order_by('snapshot_date').first()

        latest = page.seo_metrics.order_by('-snapshot_date').first()

        if not first or not latest:
            return None

        return {
            'start': {
                'date': first.snapshot_date.isoformat(),
                'seo_score': first.seo_score,
                'impressions': first.impressions or 0,
                'clicks': first.clicks or 0,
            },
            'current': {
                'date': latest.snapshot_date.isoformat(),
                'seo_score': latest.seo_score,
                'impressions': latest.impressions or 0,
                'clicks': latest.clicks or 0,
            },
            'changes': {
                'seo_score': (latest.seo_score or 0) - (first.seo_score or 0),
                'impressions': (latest.impressions or 0) - (first.impressions or 0),
                'clicks': (latest.clicks or 0) - (first.clicks or 0),
            }
        }

    # =========================================================================
    # Schedule Status & Settings
    # =========================================================================

    @action(detail=False, methods=['get'])
    def schedule_status(self, request):
        """
        스케줄 상태 조회 - 현재 자동 동기화 스케줄 및 마지막 실행 정보

        Query params:
        - domain_id: 도메인 ID (필수)
        """
        domain_id = request.query_params.get('domain_id')

        if not domain_id:
            return Response({'error': 'domain_id is required'}, status=400)

        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            return Response({'error': 'Domain not found'}, status=404)

        # Celery Beat 스케줄 정보
        beat_schedule = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})

        # 스케줄 정보 파싱
        schedules = []

        schedule_info = {
            'gsc-sync-morning': {
                'name': 'GSC 아침 동기화',
                'description': 'Google Search Console 데이터 동기화',
                'icon': '🌅',
                'type': 'gsc',
            },
            'gsc-sync-evening': {
                'name': 'GSC 저녁 동기화',
                'description': 'Google Search Console 데이터 동기화',
                'icon': '🌆',
                'type': 'gsc',
            },
            'daily-full-scan': {
                'name': '일일 전체 스캔',
                'description': 'PageSpeed API를 사용한 전체 SEO 분석',
                'icon': '📊',
                'type': 'full_scan',
            },
            'daily-ai-analysis': {
                'name': 'AI 일일 분석',
                'description': 'AI 기반 SEO 개선 제안 생성',
                'icon': '🧠',
                'type': 'ai_analysis',
            },
            'vector-embedding-update': {
                'name': '벡터 임베딩 업데이트',
                'description': 'AI 학습을 위한 데이터 벡터화',
                'icon': '🔄',
                'type': 'embedding',
            },
            'evaluate-fix-effectiveness': {
                'name': '수정 효과성 평가',
                'description': '적용된 AI 수정의 효과 분석',
                'icon': '📈',
                'type': 'evaluation',
            },
            'daily-snapshot': {
                'name': '일일 스냅샷',
                'description': 'SEO 메트릭 일일 스냅샷 생성',
                'icon': '📸',
                'type': 'snapshot',
            },
        }

        # DB에서 사용자 정의 스케줄 조회 (오버라이드)
        from django_celery_beat.models import PeriodicTask
        db_overrides = {task.name: task for task in PeriodicTask.objects.all()}

        for key, schedule_config in beat_schedule.items():
            info = schedule_info.get(key, {
                'name': key,
                'description': '',
                'icon': '⏰',
                'type': 'other',
            })

            # DB에 오버라이드가 있으면 DB 값 사용
            if key in db_overrides:
                db_task = db_overrides[key]
                cron = db_task.crontab
                if cron:
                    hour = int(cron.hour) if cron.hour.isdigit() else cron.hour
                    minute = int(cron.minute) if cron.minute.isdigit() else 0
                    if isinstance(hour, int):
                        schedule_text = f'매일 {hour:02d}:{minute:02d}'
                        # DB 스케줄로 다음 실행 시간 계산
                        next_run = self._calculate_next_run_from_crontab(hour, minute)
                    else:
                        schedule_text = f'{hour}시간마다'
                        next_run = None
                else:
                    schedule_text = 'Unknown'
                    next_run = None
                enabled = db_task.enabled
            else:
                # settings.py에서 가져옴
                schedule = schedule_config.get('schedule')
                schedule_text = self._format_crontab(schedule) if schedule else 'Unknown'
                next_run = self._calculate_next_run(schedule) if schedule else None
                enabled = True

            schedules.append({
                'key': key,
                'name': info['name'],
                'description': info['description'],
                'icon': info['icon'],
                'type': info['type'],
                'task': schedule_config.get('task', ''),
                'schedule_text': schedule_text,
                'next_run': next_run.isoformat() if next_run else None,
                'enabled': enabled,
                'editable': key in ['daily-full-scan', 'daily-ai-analysis', 'gsc-sync-morning', 'gsc-sync-evening', 'daily-snapshot', 'evaluate-fix-effectiveness'],
            })

        # 도메인별 마지막 동기화 정보 (새 필드 사용)
        last_gsc_sync = domain.last_gsc_sync_at
        last_full_scan = domain.last_full_scan_at or domain.last_scanned_at
        gsc_sync_status = domain.gsc_sync_status or 'idle'
        full_scan_status = domain.full_scan_status or 'idle'

        # AILearningState에서 마지막 동기화 정보
        try:
            ai_state = domain.ai_learning_state
            last_ai_sync = ai_state.last_sync_at
            ai_sync_status = ai_state.sync_status
        except Exception:
            last_ai_sync = None
            ai_sync_status = 'idle'

        # 새 필드가 없으면 SEOMetrics에서 추정 (하위 호환성)
        if not last_gsc_sync:
            latest_metric = SEOMetrics.objects.filter(
                page__domain=domain
            ).order_by('-snapshot_date').first()
            if latest_metric:
                last_gsc_sync = latest_metric.snapshot_date

        return Response({
            'domain': {
                'id': domain.id,
                'name': domain.domain_name,
            },
            'schedules': schedules,
            'last_sync': {
                'gsc': last_gsc_sync.isoformat() if last_gsc_sync else None,
                'full_scan': last_full_scan.isoformat() if last_full_scan else None,
                'ai_sync': last_ai_sync.isoformat() if last_ai_sync else None,
            },
            'sync_status': {
                'gsc': gsc_sync_status,
                'full_scan': full_scan_status,
                'ai': ai_sync_status,
                'domain': domain.status,
            },
            'gsc_connected': domain.search_console_connected,
        })

    @action(detail=False, methods=['post'])
    def trigger_sync(self, request):
        """
        수동 동기화 트리거

        Request body:
        - domain_id: 도메인 ID (필수)
        - sync_type: 동기화 유형 ('gsc', 'full_scan', 'ai_analysis')
        """
        domain_id = request.data.get('domain_id')
        sync_type = request.data.get('sync_type', 'gsc')

        if not domain_id:
            return Response({'error': 'domain_id is required'}, status=400)

        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            return Response({'error': 'Domain not found'}, status=404)

        # Celery 태스크 임포트 및 실행
        from ..tasks import gsc_sync_domain, refresh_domain_cache, ai_auto_analysis

        task_result = None
        task_name = ''

        if sync_type == 'gsc':
            task_result = gsc_sync_domain.delay(domain.id)
            task_name = 'GSC 동기화'
        elif sync_type == 'full_scan':
            task_result = refresh_domain_cache.delay(domain.id)
            task_name = '전체 스캔'
        elif sync_type == 'ai_analysis':
            task_result = ai_auto_analysis.delay(domain.id)
            task_name = 'AI 분석'
        else:
            return Response({'error': f'Unknown sync_type: {sync_type}'}, status=400)

        return Response({
            'success': True,
            'message': f'{task_name} 작업이 시작되었습니다.',
            'task_id': task_result.id if task_result else None,
            'sync_type': sync_type,
            'domain_id': domain.id,
        })

    def _format_crontab(self, schedule):
        """crontab 스케줄을 읽기 쉬운 텍스트로 변환"""
        if not isinstance(schedule, crontab):
            return str(schedule)

        hour = schedule._orig_hour
        minute = schedule._orig_minute
        dow = schedule._orig_day_of_week

        # 시간 포맷
        if isinstance(hour, str) and '/' in hour:
            # */6 형식
            interval = hour.split('/')[1]
            return f'{interval}시간마다'

        # 요일 확인
        if dow != '*':
            day_names = ['일', '월', '화', '수', '목', '금', '토']
            if isinstance(dow, int):
                dow_text = day_names[dow]
            else:
                dow_text = str(dow)
            return f'매주 {dow_text}요일 {hour}:{minute:02d}'

        # 매일
        if hour != '*':
            return f'매일 {hour}:{minute:02d}'

        return f'{minute}분마다'

    def _calculate_next_run(self, schedule):
        """다음 실행 시간 계산 (KST 기준)"""
        if not isinstance(schedule, crontab):
            return None

        # KST로 변환하여 계산 (스케줄이 KST 기준이므로)
        now = timezone.localtime(timezone.now())

        hour = schedule._orig_hour
        minute = schedule._orig_minute
        dow = schedule._orig_day_of_week

        # 간단한 다음 실행 시간 계산
        if isinstance(hour, str) and '/' in hour:
            # */N 시간마다
            interval = int(hour.split('/')[1])
            next_hour = ((now.hour // interval) + 1) * interval
            if next_hour >= 24:
                next_run = now.replace(hour=0, minute=0, second=0) + timedelta(days=1)
            else:
                next_run = now.replace(hour=next_hour, minute=0, second=0)
            return next_run

        if hour != '*':
            hour = int(hour)
            minute = int(minute) if minute != '*' else 0

            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if next_run <= now:
                next_run += timedelta(days=1)

            # 요일 확인
            if dow != '*':
                target_dow = int(dow)
                current_dow = next_run.weekday()
                # Python: 0=월, 6=일, Celery: 0=일, 6=토
                celery_dow = (current_dow + 1) % 7
                days_until = (target_dow - celery_dow) % 7
                if days_until == 0 and next_run <= now:
                    days_until = 7
                next_run += timedelta(days=days_until)

            return next_run

        return None

    def _calculate_next_run_from_crontab(self, hour, minute):
        """DB crontab에서 다음 실행 시간 계산"""
        now = timezone.localtime(timezone.now())

        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if next_run <= now:
            next_run += timedelta(days=1)

        return next_run

    @action(detail=False, methods=['post'])
    def update_schedule(self, request):
        """
        스케줄 시간 업데이트

        Request body:
        - schedule_key: 스케줄 키 (예: 'daily-full-scan')
        - hour: 실행 시간 (0-23)
        - minute: 실행 분 (0-59), 기본값 0
        - enabled: 활성화 여부, 기본값 True
        """
        from django_celery_beat.models import PeriodicTask, CrontabSchedule
        import json

        schedule_key = request.data.get('schedule_key')
        hour = request.data.get('hour')
        minute = request.data.get('minute', 0)
        enabled = request.data.get('enabled', True)

        if not schedule_key:
            return Response({'error': 'schedule_key is required'}, status=400)

        if hour is None:
            return Response({'error': 'hour is required'}, status=400)

        # 유효한 스케줄 키 확인
        valid_keys = {
            'gsc-sync-morning': 'seo_analyzer.tasks.gsc_sync_all_domains',
            'gsc-sync-evening': 'seo_analyzer.tasks.gsc_sync_all_domains',
            'daily-full-scan': 'seo_analyzer.tasks.nightly_cache_update',
            'daily-ai-analysis': 'seo_analyzer.tasks.schedule_all_domain_analysis',
            'vector-embedding-update': 'seo_analyzer.tasks.update_vector_embeddings',
            'evaluate-fix-effectiveness': 'seo_analyzer.tasks.evaluate_fix_effectiveness',
            'daily-snapshot': 'seo_analyzer.tasks.generate_daily_snapshot',
        }

        if schedule_key not in valid_keys:
            return Response({
                'error': f'Invalid schedule_key: {schedule_key}',
                'valid_keys': list(valid_keys.keys())
            }, status=400)

        try:
            hour = int(hour)
            minute = int(minute)

            if not (0 <= hour <= 23):
                return Response({'error': 'hour must be between 0 and 23'}, status=400)
            if not (0 <= minute <= 59):
                return Response({'error': 'minute must be between 0 and 59'}, status=400)

            # Crontab 스케줄 생성 또는 조회
            crontab_schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=str(minute),
                hour=str(hour),
                day_of_week='*',
                day_of_month='*',
                month_of_year='*',
                timezone='Asia/Seoul'
            )

            # PeriodicTask 생성 또는 업데이트
            task_name = valid_keys[schedule_key]

            periodic_task, created = PeriodicTask.objects.update_or_create(
                name=schedule_key,
                defaults={
                    'task': task_name,
                    'crontab': crontab_schedule,
                    'enabled': enabled,
                    'kwargs': json.dumps({}),
                }
            )

            return Response({
                'success': True,
                'message': f'스케줄이 {"생성" if created else "업데이트"}되었습니다.',
                'schedule': {
                    'key': schedule_key,
                    'hour': hour,
                    'minute': minute,
                    'enabled': enabled,
                    'schedule_text': f'매일 {hour:02d}:{minute:02d}',
                }
            })

        except ValueError as e:
            return Response({'error': f'Invalid value: {str(e)}'}, status=400)
        except Exception as e:
            logger.exception(f'Failed to update schedule: {e}')
            return Response({'error': str(e)}, status=500)

    @action(detail=False, methods=['get'])
    def get_schedule_config(self, request):
        """
        스케줄 설정 조회 (DB에서 사용자 정의 스케줄 포함)

        Query params:
        - schedule_key: 특정 스케줄만 조회 (선택)
        """
        from django_celery_beat.models import PeriodicTask

        schedule_key = request.query_params.get('schedule_key')

        # settings.py의 기본 스케줄
        beat_schedule = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})

        # DB에서 사용자 정의 스케줄 조회
        db_schedules = PeriodicTask.objects.filter(enabled=True)

        schedule_configs = []

        schedule_info = {
            'gsc-sync-morning': {'name': 'GSC 아침 동기화', 'type': 'gsc', 'editable': True},
            'gsc-sync-evening': {'name': 'GSC 저녁 동기화', 'type': 'gsc', 'editable': True},
            'daily-full-scan': {'name': '일일 전체 스캔', 'type': 'full_scan', 'editable': True},
            'daily-ai-analysis': {'name': 'AI 일일 분석', 'type': 'ai_analysis', 'editable': True},
            'vector-embedding-update': {'name': '벡터 임베딩 업데이트', 'type': 'embedding', 'editable': False},
            'evaluate-fix-effectiveness': {'name': '수정 효과성 평가', 'type': 'evaluation', 'editable': True},
            'daily-snapshot': {'name': '일일 스냅샷', 'type': 'snapshot', 'editable': True},
        }

        # DB 스케줄로 오버라이드된 키 추적
        db_overrides = {task.name: task for task in db_schedules}

        for key, config in beat_schedule.items():
            if schedule_key and key != schedule_key:
                continue

            info = schedule_info.get(key, {'name': key, 'type': 'other', 'editable': False})

            # DB에 오버라이드가 있으면 DB 값 사용
            if key in db_overrides:
                db_task = db_overrides[key]
                cron = db_task.crontab
                if cron:
                    hour = int(cron.hour) if cron.hour.isdigit() else cron.hour
                    minute = int(cron.minute) if cron.minute.isdigit() else cron.minute
                    schedule_text = f'매일 {hour:02d}:{minute:02d}' if isinstance(hour, int) else cron.hour
                    enabled = db_task.enabled
                else:
                    hour = None
                    minute = None
                    schedule_text = 'Unknown'
                    enabled = db_task.enabled
                source = 'database'
            else:
                # settings.py에서 가져옴
                schedule = config.get('schedule')
                schedule_text = self._format_crontab(schedule) if schedule else 'Unknown'
                hour = schedule._orig_hour if isinstance(schedule, crontab) else None
                minute = schedule._orig_minute if isinstance(schedule, crontab) else None
                enabled = True
                source = 'settings'

            schedule_configs.append({
                'key': key,
                'name': info['name'],
                'type': info['type'],
                'editable': info['editable'],
                'hour': int(hour) if isinstance(hour, (int, str)) and str(hour).isdigit() else hour,
                'minute': int(minute) if isinstance(minute, (int, str)) and str(minute).isdigit() else minute,
                'schedule_text': schedule_text,
                'enabled': enabled,
                'source': source,
            })

        return Response({
            'schedules': schedule_configs
        })

    @action(detail=False, methods=['post'])
    def backfill_gsc_traffic(self, request):
        """
        GSC 과거 트래픽 데이터를 DB에 저장 (최초 1회 또는 수동 실행)

        Request body:
        - domain_id: 도메인 ID (필수)
        - days: 가져올 기간 (기본 90일, 최대 500일)
        """
        domain_id = request.data.get('domain_id')
        days = int(request.data.get('days', 90))

        if not domain_id:
            return Response({'error': 'domain_id is required'}, status=400)

        if days > 500:
            days = 500  # GSC API 제한

        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            return Response({'error': 'Domain not found'}, status=404)

        if not domain.search_console_connected:
            return Response({
                'error': 'GSC not connected',
                'message': 'Google Search Console이 연결되지 않은 도메인입니다.'
            }, status=400)

        # 기간 설정
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        try:
            gsc = SearchConsoleService()
            site_url = f'sc-domain:{domain.domain_name}'

            # GSC API에서 일별 데이터 가져오기
            gsc_result = gsc.get_search_analytics(
                site_url=site_url,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                dimensions=['date'],
                row_limit=500
            )

            if gsc_result.get('error'):
                return Response({
                    'error': 'GSC API error',
                    'message': gsc_result.get('error')
                }, status=500)

            rows = gsc_result.get('rows', [])
            created_count = 0
            updated_count = 0

            for row in rows:
                date_str = row.get('keys', [''])[0]
                if not date_str:
                    continue

                # date_str: 'YYYY-MM-DD'
                try:
                    snapshot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    continue

                # DailyTrafficSnapshot 생성 또는 업데이트
                snapshot, created = DailyTrafficSnapshot.objects.update_or_create(
                    domain=domain,
                    date=snapshot_date,
                    defaults={
                        'impressions': row.get('impressions', 0),
                        'clicks': row.get('clicks', 0),
                        'ctr': row.get('ctr', 0),
                        'avg_position': row.get('position', 0),
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            logger.info(f"Backfill completed for {domain.domain_name}: {created_count} created, {updated_count} updated")

            return Response({
                'success': True,
                'message': f'GSC 트래픽 데이터가 저장되었습니다.',
                'domain_id': domain.id,
                'domain_name': domain.domain_name,
                'period': {
                    'start': start_date.strftime('%Y-%m-%d'),
                    'end': end_date.strftime('%Y-%m-%d'),
                    'days': days,
                },
                'stats': {
                    'fetched_rows': len(rows),
                    'created': created_count,
                    'updated': updated_count,
                }
            })

        except Exception as e:
            logger.exception(f'Failed to backfill GSC traffic: {e}')
            return Response({
                'error': str(e),
                'message': 'GSC 데이터 가져오기에 실패했습니다.'
            }, status=500)

    @action(detail=False, methods=['get'])
    def traffic_history(self, request):
        """
        저장된 트래픽 히스토리 조회

        Query params:
        - domain_id: 도메인 ID (필수)
        - days: 조회 기간 (기본 30일)
        """
        domain_id = request.query_params.get('domain_id')
        days = int(request.query_params.get('days', 30))

        if not domain_id:
            return Response({'error': 'domain_id is required'}, status=400)

        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            return Response({'error': 'Domain not found'}, status=404)

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # 저장된 스냅샷 조회
        snapshots = DailyTrafficSnapshot.objects.filter(
            domain=domain,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')

        # 총계 계산
        total_impressions = sum(s.impressions for s in snapshots)
        total_clicks = sum(s.clicks for s in snapshots)
        avg_ctr = total_clicks / total_impressions * 100 if total_impressions > 0 else 0

        data = []
        for s in snapshots:
            data.append({
                'date': s.date.strftime('%Y-%m-%d'),
                'impressions': s.impressions,
                'clicks': s.clicks,
                'ctr': round(s.ctr * 100, 2) if s.ctr else 0,
                'avg_position': round(s.avg_position, 1) if s.avg_position else 0,
            })

        return Response({
            'domain_id': domain.id,
            'domain_name': domain.domain_name,
            'period': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d'),
                'days': days,
            },
            'stats': {
                'total_impressions': total_impressions,
                'total_clicks': total_clicks,
                'avg_ctr': round(avg_ctr, 2),
                'data_points': len(data),
            },
            'history': data,
        })
