"""
Domain Refresh Service
도메인 갱신 로직을 캡슐화한 서비스 클래스
"""
import logging
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db import transaction
from ..models import Domain, Page, SEOMetrics
from .domain_scanner import DomainScanner
from .pagespeed_insights import PageSpeedInsightsService
from .search_console import SearchConsoleService
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class DomainRefreshService:
    """
    도메인 데이터 갱신 서비스

    이 서비스는 views.py의 refresh()와 tasks.py의 refresh_domain_cache()에서
    사용되는 공통 로직을 캡슐화합니다.

    Usage:
        # 동기 방식 (views.py)
        service = DomainRefreshService(max_pages=100, max_metrics=5)
        result = service.refresh_domain(domain)

        # 비동기 방식 (tasks.py)
        service = DomainRefreshService(max_pages=1000, max_metrics=1000)
        result = service.refresh_domain(domain, progress_callback=callback)
    """

    def __init__(self, max_pages=100, max_metrics=None, mobile_only=True):
        """
        Initialize service

        Args:
            max_pages: 최대 페이지 발견 수
            max_metrics: 메트릭을 가져올 최대 페이지 수 (None = 모든 페이지)
            mobile_only: True면 mobile만 분석 (2배 빠름), False면 mobile+desktop
        """
        self.max_pages = max_pages
        self.max_metrics = max_metrics or max_pages
        self.mobile_only = mobile_only

        # 서비스 초기화
        self.scanner = DomainScanner(max_pages=max_pages)
        self.pagespeed = PageSpeedInsightsService()
        self.search_console = None
        self.search_console_available = False

        # Rate limiting for PageSpeed API
        # PageSpeed Insights API limits:
        # - 400 requests per 100 seconds = 4 requests per second
        # - 25,000 requests per day
        #
        # Strategy: Use thread-safe rate limiter
        # - Max 4 concurrent requests (Semaphore)
        # - Min 250ms interval between requests (Token bucket)
        self.rate_limiter = RateLimiter(
            max_requests_per_second=4.0,
            max_concurrent=4
        )

        # Search Console 초기화 시도
        try:
            self.search_console = SearchConsoleService()
            self.search_console_available = True
            logger.info("Search Console service initialized successfully")
        except Exception as e:
            logger.warning(f"Search Console not available: {e}")

    def refresh_domain(self, domain, progress_callback=None):
        """
        도메인 데이터 갱신 메인 로직

        Process:
        1. Discover pages from sitemap/crawling (0-10%)
        2. Create/update pages in database (10-70%)
        3. Build page hierarchy (70%)
        4. Fetch SEO metrics in parallel (70-90%)
        5. Update domain aggregates (90-100%)

        Args:
            domain: Domain 인스턴스
            progress_callback: 진행률 콜백 함수 (optional)
                              callback(current, total, status_message)

        Returns:
            dict: {
                'pages_discovered': int,
                'pages_processed': int,
                'metrics_fetched': int,
                'domain': Domain
            }
        """
        start_time = time.time()
        analysis_mode = "mobile-only" if self.mobile_only else "mobile+desktop"

        logger.info(
            f"=== Starting domain refresh ===\n"
            f"  Domain: {domain.domain_name}\n"
            f"  Max pages: {self.max_pages}\n"
            f"  Max metrics: {self.max_metrics}\n"
            f"  Analysis mode: {analysis_mode}"
        )

        # Step 1: 페이지 발견 (0-10%)
        self._update_progress(progress_callback, 5, 100, "Discovering pages from sitemap")
        discovery_result = self.scanner.discover_from_domain(
            domain.domain_name,
            domain.protocol
        )

        discovered_pages = discovery_result['pages']
        total_pages = len(discovered_pages)
        logger.info(
            f"Discovery completed: {total_pages} pages found "
            f"({discovery_result.get('subdomains', [])!r} subdomains)"
        )

        # Step 2: 페이지 처리 (10-70%)
        processed_pages = []
        metrics_fetched = 0

        self._update_progress(progress_callback, 10, 100, "Saving pages to database")

        # Step 2a: Create/update pages in single transaction (10-60%)
        with transaction.atomic():
            for idx, page_data in enumerate(discovered_pages):
                progress = 10 + int((idx + 1) / total_pages * 50)
                self._update_progress(
                    progress_callback,
                    progress,
                    100,
                    f"Saving page {idx + 1}/{total_pages}"
                )

                page = self._create_or_update_page(domain, page_data)
                processed_pages.append(page)

        logger.info(f"Saved {len(processed_pages)} pages to database")

        # Step 2b: Establish parent-child relationships in single transaction (60-70%)
        self._update_progress(progress_callback, 65, 100, "Building page hierarchy")
        with transaction.atomic():
            self._establish_parent_relationships(domain)
        logger.info("Page hierarchy established")

        # Step 2c: Fetch metrics (70-90%) - OUTSIDE transaction for parallel processing
        self._update_progress(progress_callback, 70, 100, f"Fetching SEO metrics ({analysis_mode})")
        metrics_to_fetch = processed_pages[:self.max_metrics]
        logger.info(f"Will fetch metrics for {len(metrics_to_fetch)} pages (limit: {self.max_metrics})")

        metrics_fetched = self._fetch_metrics_parallel(
            metrics_to_fetch,
            progress_callback
        )

        # Step 3: Update domain aggregates in single transaction (90-100%)
        self._update_progress(progress_callback, 92, 100, "Updating domain statistics")
        with transaction.atomic():
            domain.update_aggregate_scores()
            domain.last_scanned_at = datetime.now(timezone.utc)
            domain.save()
        logger.info("Domain aggregate scores updated")

        self._update_progress(progress_callback, 100, 100, "Scan completed successfully")

        # Summary
        elapsed = time.time() - start_time
        result = {
            'pages_discovered': total_pages,
            'pages_processed': len(processed_pages),
            'metrics_fetched': metrics_fetched,
            'domain': domain,
            'elapsed_time': elapsed
        }

        logger.info(
            f"=== Domain refresh completed ===\n"
            f"  Pages discovered: {total_pages}\n"
            f"  Pages processed: {len(processed_pages)}\n"
            f"  Metrics fetched: {metrics_fetched}\n"
            f"  Time elapsed: {elapsed:.1f}s\n"
            f"  Average: {metrics_fetched/elapsed:.2f} pages/sec"
        )

        return result

    def refresh_search_console_only(self, domain, progress_callback=None):
        """
        Search Console 데이터만 갱신 (PageSpeed 스캔 없이)

        설계 의도:
        - Full Scan은 느리고 비용이 높음 (PageSpeed API 쿼터 소모)
        - 색인 상태는 자주 확인해야 하지만 PageSpeed는 주기적으로만 필요
        - 이 메서드는 기존 페이지의 Search Console 데이터만 업데이트

        Process:
        1. 기존 페이지 목록 가져오기 (새로운 페이지 발견 안 함)
        2. 각 페이지의 Search Console 데이터 업데이트
           - URL Inspection API → 색인 상태
           - Search Analytics API → 노출수/클릭수
        3. 도메인 통계 업데이트

        Advantages:
        - 빠름 (PageSpeed API 호출 없음)
        - API 쿼터 절약
        - 색인 상태 일일 체크에 적합

        Args:
            domain: Domain 인스턴스
            progress_callback: 진행률 콜백 함수 (optional)

        Returns:
            dict: {
                'pages_updated': int,
                'pages_failed': int,
                'domain': Domain
            }
        """
        if not self.search_console_available:
            logger.error("Search Console service not available")
            return {
                'error': True,
                'message': 'Search Console service not initialized',
                'pages_updated': 0,
                'pages_failed': 0,
            }

        start_time = time.time()
        logger.info(
            f"=== Starting Search Console refresh (lightweight) ===\n"
            f"  Domain: {domain.domain_name}"
        )

        # Get existing pages with metrics
        pages = Page.objects.filter(domain=domain).prefetch_related('seo_metrics')
        total_pages = pages.count()

        if total_pages == 0:
            logger.warning(f"No pages found for domain {domain.domain_name}")
            return {
                'pages_updated': 0,
                'pages_failed': 0,
                'domain': domain,
            }

        logger.info(f"Found {total_pages} pages to update")

        # Update Search Console data using BATCH request (12x faster!)
        updated = 0
        failed = 0

        # Filter pages that have metrics
        valid_pages = [p for p in pages if p.seo_metrics.first() is not None]
        invalid_count = total_pages - len(valid_pages)
        if invalid_count > 0:
            logger.warning(f"{invalid_count} pages skipped (no metrics)")
            failed += invalid_count

        if valid_pages:
            # Progress: starting batch
            self._update_progress(
                progress_callback,
                10,
                100,
                f"Batch fetching index status for {len(valid_pages)} pages..."
            )

            # Prepare batch request
            site_url = f"sc-domain:{domain.domain_name}"
            page_urls = [p.url for p in valid_pages]

            # Execute batch URL Inspection (single HTTP request!)
            try:
                batch_results = self.search_console.batch_get_index_status(site_url, page_urls)

                # Progress: processing results
                self._update_progress(
                    progress_callback,
                    50,
                    100,
                    f"Processing {len(batch_results)} index status results..."
                )

                # Update each page with batch results
                for idx, (page, result) in enumerate(zip(valid_pages, batch_results)):
                    try:
                        latest_metrics = page.seo_metrics.first()
                        if not latest_metrics:
                            continue

                        if result.get('error'):
                            logger.warning(f"⚠️ Batch failed for {page.url}: {result.get('message')}")
                            failed += 1
                            continue

                        # Update index status from batch result
                        latest_metrics.is_indexed = result.get('is_indexed', False)
                        latest_metrics.index_status = result.get('verdict', 'UNKNOWN')
                        latest_metrics.coverage_state = result.get('coverage_state', 'Unknown')

                        # Fetch Search Analytics (not batchable in same way)
                        try:
                            analytics = self.search_console.get_page_analytics(
                                site_url,
                                page.url
                            )
                            if not analytics.get('error'):
                                latest_metrics.impressions = analytics.get('impressions', 0)
                                latest_metrics.clicks = analytics.get('clicks', 0)
                                latest_metrics.ctr = analytics.get('ctr', 0)
                                latest_metrics.avg_position = analytics.get('avg_position', 0)
                        except BaseException as analytics_error:
                            # Search Analytics failure is non-fatal
                            logger.warning(f"⚠️ Search Analytics failed for {page.url}: {analytics_error}")

                        latest_metrics.save()
                        updated += 1
                        logger.debug(f"✅ Updated {page.url}")

                        # Progress update
                        progress = 50 + int((idx / len(valid_pages)) * 40)
                        self._update_progress(
                            progress_callback,
                            progress,
                            100,
                            f"Updated {idx+1}/{len(valid_pages)} pages"
                        )

                    except BaseException as e:
                        logger.error(f"❌ Failed to update {page.url}: {e}", exc_info=True)
                        failed += 1

            except BaseException as batch_error:
                # Batch failed completely - fall back to sequential
                logger.error(f"❌ Batch request failed, falling back to sequential: {batch_error}", exc_info=True)

                for idx, page in enumerate(valid_pages, 1):
                    try:
                        self._fetch_search_console_data(page)
                        updated += 1

                        # Progress update
                        progress = 10 + int((idx / len(valid_pages)) * 80)
                        self._update_progress(
                            progress_callback,
                            progress,
                            100,
                            f"Updating {idx}/{len(valid_pages)} (fallback)"
                        )
                    except BaseException as e:
                        logger.error(f"❌ Failed to update {page.url}: {e}")
                        failed += 1

        # Update domain aggregates
        self._update_progress(progress_callback, 95, 100, "Updating domain statistics")
        with transaction.atomic():
            domain.update_aggregate_scores()
            domain.last_scanned_at = datetime.now(timezone.utc)
            domain.save()

        self._update_progress(progress_callback, 100, 100, "Search Console refresh completed")

        # Summary
        elapsed = time.time() - start_time
        result = {
            'pages_updated': updated,
            'pages_failed': failed,
            'domain': domain,
            'elapsed_time': elapsed,
        }

        logger.info(
            f"=== Search Console refresh completed ===\n"
            f"  Pages updated: {updated}\n"
            f"  Pages failed: {failed}\n"
            f"  Time elapsed: {elapsed:.1f}s"
        )

        return result

    def _create_or_update_page(self, domain, page_data):
        """
        페이지 생성 또는 업데이트 (수동 편집 보존)

        수동 편집 보존 규칙:
        1. use_manual_position=True면 depth_level 업데이트 안 함
        2. last_manually_edited_at이 있으면 parent_page 업데이트 안 함
        3. 메타데이터(title, description)는 항상 업데이트
        4. is_subdomain, subdomain은 자동 스캔 결과로 업데이트

        Args:
            domain: Domain 인스턴스
            page_data: 페이지 정보 dict

        Returns:
            Page 인스턴스
        """
        page, created = Page.objects.get_or_create(
            domain=domain,
            url=page_data['url'],
            defaults={
                'path': page_data['path'],
                'is_subdomain': page_data['is_subdomain'],
                'subdomain': page_data['subdomain'],
                'depth_level': page_data.get('depth_level', 0),
                'status': 'active',
            }
        )

        if not created:
            # 기존 페이지 - 수동 편집 보존
            update_fields = []

            # Path는 항상 업데이트 (URL 구조 변경 반영)
            if page.path != page_data['path']:
                page.path = page_data['path']
                update_fields.append('path')

            # is_subdomain, subdomain은 자동 스캔 결과로 업데이트
            if page.is_subdomain != page_data['is_subdomain']:
                page.is_subdomain = page_data['is_subdomain']
                update_fields.append('is_subdomain')

            if page.subdomain != page_data.get('subdomain'):
                page.subdomain = page_data.get('subdomain')
                update_fields.append('subdomain')

            # depth_level은 수동 위치가 설정되지 않은 경우만 업데이트
            if not page.use_manual_position:
                if page.depth_level != page_data.get('depth_level', 0):
                    page.depth_level = page_data.get('depth_level', 0)
                    update_fields.append('depth_level')

            # Status는 항상 active로 (페이지가 발견되었으므로)
            if page.status != 'active':
                page.status = 'active'
                update_fields.append('status')

            # 메타데이터는 항상 업데이트 (page_data에 있는 경우)
            if 'title' in page_data and page.title != page_data['title']:
                page.title = page_data['title']
                update_fields.append('title')

            if 'description' in page_data and page.description != page_data['description']:
                page.description = page_data['description']
                update_fields.append('description')

            # 변경사항이 있으면 저장
            if update_fields:
                page.save(update_fields=update_fields)
                logger.debug(f"Updated page {page.url}: {update_fields}")
            else:
                logger.debug(f"No changes for page: {page.url}")
        else:
            logger.debug(f"Created new page: {page.url}")

        return page

    def _establish_parent_relationships(self, domain):
        """
        페이지 간 부모-자식 관계 설정 및 depth_level 재계산

        수동 편집 보존 규칙:
        - last_manually_edited_at이 있는 페이지는 parent_page 업데이트 안 함
        - use_manual_position=True인 페이지는 depth_level 업데이트 안 함

        Args:
            domain: Domain 인스턴스
        """
        # Get all pages for this domain
        pages = list(Page.objects.filter(domain=domain).order_by('path'))

        # Separate manually edited and auto pages
        manually_edited_pages = [p for p in pages if p.last_manually_edited_at]
        auto_pages = [p for p in pages if not p.last_manually_edited_at]

        logger.info(
            f"Establishing parent relationships: "
            f"{len(auto_pages)} auto pages, {len(manually_edited_pages)} manually edited (skipped)"
        )

        # First, find the root page (shortest path, usually '/')
        root_page = None
        for page in pages:
            if page.path == '/' or page.path == '':
                root_page = page
                # Only update if not manually edited
                if not page.last_manually_edited_at:
                    page.depth_level = 0
                    page.parent_page = None
                    page.save(update_fields=['parent_page', 'depth_level'])
                    logger.debug(f"Set root page: {page.url} (depth 0)")
                else:
                    logger.debug(f"Skipped manually edited root page: {page.url}")
                break

        # If no explicit root found, use the page with the shortest path
        if not root_page and pages:
            root_page = min(pages, key=lambda p: len(p.path.strip('/')))
            # Only update if not manually edited
            if not root_page.last_manually_edited_at:
                root_page.depth_level = 0
                root_page.parent_page = None
                root_page.save(update_fields=['parent_page', 'depth_level'])
                logger.debug(f"Set root page (shortest path): {root_page.url} (depth 0)")
            else:
                logger.debug(f"Skipped manually edited root (shortest path): {root_page.url}")

        # Sort pages by path length (shallow to deep)
        pages_sorted = sorted(pages, key=lambda p: len(p.path.strip('/')))

        # Build parent-child relationships and calculate depth
        # Only for pages that are NOT manually edited
        for page in pages_sorted:
            # Skip manually edited pages
            if page.last_manually_edited_at:
                logger.debug(f"Skipping manually edited page: {page.url}")
                continue

            if page == root_page:
                continue

            page_path = page.path.strip('/')

            # Find the best parent (longest matching path prefix)
            best_parent = None
            longest_match = -1

            for potential_parent in pages_sorted:
                if potential_parent == page:
                    continue

                parent_path = potential_parent.path.strip('/')

                # Check if this page is under the potential parent's path
                if not parent_path and potential_parent == root_page:
                    # Root page can be a parent
                    if longest_match < 0:
                        best_parent = potential_parent
                        longest_match = 0
                elif parent_path and page_path.startswith(parent_path + '/'):
                    # This is a valid parent with matching path
                    if len(parent_path) > longest_match:
                        best_parent = potential_parent
                        longest_match = len(parent_path)

            # Set parent and calculate depth
            update_fields = []
            if best_parent:
                page.parent_page = best_parent
                update_fields.append('parent_page')
                # Only update depth if not using manual position
                if not page.use_manual_position:
                    page.depth_level = best_parent.depth_level + 1
                    update_fields.append('depth_level')
            else:
                # No parent found, make it a child of root
                page.parent_page = root_page
                update_fields.append('parent_page')
                # Only update depth if not using manual position
                if not page.use_manual_position:
                    page.depth_level = 1
                    update_fields.append('depth_level')

            if update_fields:
                page.save(update_fields=update_fields)
                logger.debug(
                    f"Set parent: {page.path} (depth {page.depth_level}) -> "
                    f"{page.parent_page.path if page.parent_page else 'None'}"
                )

    def _fetch_metrics_parallel(self, pages, progress_callback):
        """
        병렬로 페이지 메트릭 수집 (최적화된 Rate limiting)

        최적화 전략:
        1. Batch URL Inspection (8-12x faster) - 단일 HTTP 요청으로 모든 페이지 색인 상태 확인
        2. Thread pool (10 workers) - 높은 처리량
        3. Rate limiter (4 concurrent, 4 req/sec) - API 제한 준수
        4. As-completed pattern - 효율적인 결과 처리
        5. Mobile + Desktop 병렬 분석 - 포괄적인 데이터

        Args:
            pages: Page 인스턴스 리스트
            progress_callback: 진행률 콜백 함수

        Returns:
            int: 성공적으로 수집된 메트릭 개수
        """
        if not pages:
            return 0

        total_pages = len(pages)
        metrics_fetched = 0
        failed_pages = 0
        start_time = time.time()

        # Worker configuration
        # More workers than rate limit allows better CPU utilization
        # while rate limiter controls actual API calls
        max_workers = 10

        analysis_mode = "mobile-only" if self.mobile_only else "mobile+desktop"
        logger.info(
            f"Starting parallel metrics fetch:\n"
            f"  - Pages: {total_pages}\n"
            f"  - Workers: {max_workers}\n"
            f"  - Analysis mode: {analysis_mode}\n"
            f"  - Rate limit: 4 concurrent, 4 req/sec"
        )

        # OPTIMIZATION: Batch fetch index status for all pages at once (8-12x faster!)
        # This reduces sequential URL Inspection API calls from 17×15s=255s to 1×20s=20s
        self.index_status_cache = {}  # Cache for batch results
        if self.search_console_available and pages:
            try:
                site_url = f"sc-domain:{pages[0].domain.domain_name}"
                page_urls = [p.url for p in pages]

                logger.info(f"🚀 Batch fetching index status for {len(page_urls)} pages...")
                self._update_progress(
                    progress_callback,
                    70,
                    100,
                    f"Batch fetching index status for {len(page_urls)} pages..."
                )

                # Execute batch URL Inspection (single HTTP request!)
                batch_results = self.search_console.batch_get_index_status(site_url, page_urls)

                # Cache results by URL for quick lookup during parallel processing
                for result in batch_results:
                    page_url = result.get('page_url')
                    if page_url:
                        self.index_status_cache[page_url] = result

                success_count = len([r for r in batch_results if not r.get('error')])
                logger.info(f"✅ Batch index status complete: {success_count}/{len(page_urls)} successful")

            except BaseException as batch_error:
                # Batch failed - will fall back to sequential in _fetch_search_console_data
                logger.error(f"❌ Batch URL Inspection failed, will use sequential fallback: {batch_error}", exc_info=True)
                self.index_status_cache = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks immediately
            # Rate limiting happens inside _fetch_page_metrics
            future_to_page = {
                executor.submit(self._fetch_page_metrics, page): page
                for page in pages
            }

            logger.info(f"Submitted all {total_pages} tasks to thread pool")

            # Process completed tasks as they finish
            for future in as_completed(future_to_page):
                page = future_to_page[future]

                try:
                    success = future.result()
                    if success:
                        metrics_fetched += 1
                    else:
                        failed_pages += 1

                except Exception as e:
                    failed_pages += 1
                    logger.error(
                        f"Exception processing {page.url}: {e}",
                        exc_info=True
                    )

                # Update progress (70-90% of total progress)
                progress_percent = 70 + int((metrics_fetched + failed_pages) / total_pages * 20)
                self._update_progress(
                    progress_callback,
                    progress_percent,
                    100,
                    f"Metrics: {metrics_fetched} succeeded, {failed_pages} failed ({analysis_mode})"
                )

        # Summary
        elapsed = time.time() - start_time
        success_rate = (metrics_fetched / total_pages * 100) if total_pages > 0 else 0
        pages_per_sec = metrics_fetched / elapsed if elapsed > 0 else 0

        logger.info(
            f"Parallel metrics fetch completed:\n"
            f"  - Succeeded: {metrics_fetched}/{total_pages} ({success_rate:.1f}%)\n"
            f"  - Failed: {failed_pages}/{total_pages}\n"
            f"  - Time: {elapsed:.1f}s\n"
            f"  - Rate: {pages_per_sec:.2f} pages/sec"
        )

        return metrics_fetched

    def _fetch_page_metrics(self, page):
        """
        페이지 메트릭 수집 (Thread-safe rate limiting)

        Args:
            page: Page 인스턴스

        Returns:
            bool: 성공 여부
        """
        try:
            # Apply rate limiting using context manager
            with self.rate_limiter:
                logger.info(f"Fetching metrics for {page.url}")

                # PageSpeed Insights 분석 (mobile + desktop)
                metrics_result = self.pagespeed.analyze_both_strategies(
                    page.url,
                    mobile_only=self.mobile_only
                )

                if metrics_result.get('error'):
                    error_msg = metrics_result.get('message', 'Unknown error')
                    logger.error(f"PageSpeed error for {page.url}: {error_msg}")
                    return False

            # Save metrics in separate transaction (outside rate limiter)
            # This prevents lock timeouts from parallel processing
            try:
                with transaction.atomic():
                    self._save_pagespeed_metrics(page, metrics_result)

                    # Search Console 데이터 (사용 가능한 경우)
                    if self.search_console_available:
                        try:
                            self._fetch_search_console_data(page)
                        except BaseException as sc_error:
                            # Search Console 에러는 치명적이지 않음 (BaseException으로 모든 에러 잡음)
                            logger.warning(f"Search Console data fetch failed for {page.url}: {sc_error}", exc_info=True)

                logger.info(f"Successfully saved metrics for {page.url}")
                return True

            except Exception as db_error:
                logger.error(f"Database error saving metrics for {page.url}: {db_error}", exc_info=True)
                return False

        except Exception as e:
            logger.error(f"Failed to fetch metrics for {page.url}: {e}", exc_info=True)
            return False

    def _save_pagespeed_metrics(self, page, metrics_result):
        """
        PageSpeed Insights 메트릭 저장

        Args:
            page: Page 인스턴스
            metrics_result: PageSpeed 분석 결과
        """
        primary = metrics_result['primary_scores']
        mobile = metrics_result['mobile']

        SEOMetrics.objects.create(
            page=page,
            seo_score=primary.get('seo_score'),
            performance_score=primary.get('performance_score'),
            accessibility_score=primary.get('accessibility_score'),
            best_practices_score=primary.get('best_practices_score'),
            pwa_score=primary.get('pwa_score'),
            mobile_score=primary.get('mobile_score'),
            desktop_score=primary.get('desktop_score'),
            lcp=mobile.get('lcp'),
            fid=mobile.get('fid'),
            cls=mobile.get('cls'),
            fcp=mobile.get('fcp'),
            tti=mobile.get('tti'),
            tbt=mobile.get('tbt'),
            snapshot_date=datetime.now(timezone.utc),
        )

    def _fetch_search_console_data(self, page):
        """
        Search Console 데이터 수집 및 업데이트

        Responsibility:
        - Fetch accurate index status via URL Inspection API
        - Fetch search analytics (impressions, clicks) via Search Analytics API
        - Update existing SEOMetrics with Search Console data
        - Handle API failures gracefully (non-fatal)

        Process:
        1. Get latest SEOMetrics for page (must already exist from PageSpeed scan)
        2. Call URL Inspection API → Update is_indexed, index_status, coverage_state
        3. Call Search Analytics API → Update impressions, clicks, CTR, avg_position

        Error Handling:
        - API failures are logged but don't stop the scan
        - Individual page failures don't affect other pages
        - Missing data results in fields staying as default values

        Args:
            page: Page instance to fetch data for

        Notes:
        - Requires Search Console service to be initialized
        - Uses sc-domain: format for site URL
        - Called after PageSpeed metrics are collected
        - Non-fatal: failures are acceptable and logged
        """
        # Worker 크래시 방지: 모든 에러를 안전하게 잡음
        try:
            # Search Console 객체 유효성 검사
            if not self.search_console or not hasattr(self.search_console, 'get_index_status'):
                logger.warning(f"Search Console not properly initialized for {page.url}")
                return

            # Site URL 구성
            site_url = f"sc-domain:{page.domain.domain_name}"

            # 최신 메트릭 가져오기 (이미 생성된 상태여야 함)
            latest_metrics = page.seo_metrics.first()
            if not latest_metrics:
                logger.warning(f"No SEO metrics found for {page.url}, skipping Search Console data")
                return

            # 1. URL Inspection API로 실제 색인 상태 확인
            try:
                # Use cached batch result if available (8-12x faster!)
                index_status = None
                if hasattr(self, 'index_status_cache') and page.url in self.index_status_cache:
                    index_status = self.index_status_cache[page.url]
                    logger.debug(f"Using cached batch index status for {page.url}")
                else:
                    # Fallback to sequential API call if batch failed or not available
                    logger.debug(f"Fetching index status sequentially for {page.url}")
                    index_status = self.search_console.get_index_status(site_url, page.url)

                if index_status and not index_status.get('error'):
                    # SEOMetrics에 색인 상태 저장
                    latest_metrics.is_indexed = index_status.get('is_indexed', False)
                    latest_metrics.index_status = index_status.get('verdict', 'UNKNOWN')
                    latest_metrics.coverage_state = index_status.get('coverage_state', 'Unknown')
                    latest_metrics.save(update_fields=['is_indexed', 'index_status', 'coverage_state'])

                    logger.info(
                        f"Index status for {page.url}: "
                        f"is_indexed={latest_metrics.is_indexed}, verdict={latest_metrics.index_status}"
                    )
                else:
                    logger.warning(f"Failed to get index status for {page.url}: {index_status.get('message') if index_status else 'No result'}")

            except BaseException as index_error:
                # BaseException으로 모든 에러 잡음 (Google API 저레벨 에러 포함)
                logger.error(f"URL Inspection failed for {page.url}: {index_error}", exc_info=True)

            # 2. Search Analytics로 노출수/클릭수 가져오기 (sc-domain format)
            try:
                analytics = self.search_console.get_page_analytics(
                    site_url,  # Use sc-domain format
                    page.url
                )

                if not analytics.get('error'):
                    # SEOMetrics에 analytics 데이터 저장
                    latest_metrics.impressions = analytics.get('impressions', 0)
                    latest_metrics.clicks = analytics.get('clicks', 0)
                    latest_metrics.ctr = analytics.get('ctr', 0)
                    latest_metrics.avg_position = analytics.get('avg_position', 0)
                    latest_metrics.save(update_fields=['impressions', 'clicks', 'ctr', 'avg_position'])

                    logger.debug(f"Updated Search Console analytics for {page.url}")
                else:
                    logger.warning(f"Failed to get analytics for {page.url}: {analytics.get('message')}")

            except BaseException as analytics_error:
                # BaseException으로 모든 에러 잡음 (연결 끊김 등)
                logger.error(f"Search Analytics failed for {page.url}: {analytics_error}", exc_info=True)

        except BaseException as e:
            # 최상위 보호: Worker 크래시 방지
            logger.error(f"Critical error in Search Console data fetch for {page.url}: {e}", exc_info=True)

    @staticmethod
    def _update_progress(callback, current, total, message):
        """
        진행률 콜백 호출

        Args:
            callback: 콜백 함수
            current: 현재 진행
            total: 전체
            message: 상태 메시지
        """
        logger.info(f"Progress update: {current}/{total} - {message}")
        logger.info(f"Callback is: {callback}, Type: {type(callback)}")
        if callback:
            try:
                logger.info(f"Calling callback with: current={current}, total={total}, message={message}")
                callback(current, total, message)
                logger.info(f"Progress callback executed successfully")
            except Exception as e:
                logger.error(f"Progress callback error: {e}", exc_info=True)
        else:
            logger.warning(f"No callback provided for progress update")
