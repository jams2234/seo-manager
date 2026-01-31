"""
Google Search Console API Service
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from googleapiclient.errors import HttpError
from .google_api_client import GoogleAPIClient

logger = logging.getLogger(__name__)

# Retry configuration for transient failures
# Reduced retries to prevent SSL error accumulation and worker crashes
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 3


class SearchConsoleService:
    """
    Service for fetching data from Google Search Console API
    """

    def __init__(self):
        """Initialize Search Console service with authentication"""
        # URL Inspection requires webmasters scope (not just readonly)
        scopes = ['https://www.googleapis.com/auth/webmasters']
        self.client = GoogleAPIClient(scopes=scopes)
        self.service = self.client.build_service('searchconsole', 'v1')

    def get_site_info(self, site_url: str) -> Dict:
        """
        Get basic information about a site in Search Console

        Args:
            site_url: Site URL (e.g., 'https://example.com/' or 'sc-domain:example.com')

        Returns:
            Dictionary with site information
        """
        try:
            site_info = self.service.sites().get(siteUrl=site_url).execute()
            logger.info(f"Retrieved site info for {site_url}")
            return {
                'error': False,
                'site_url': site_info.get('siteUrl'),
                'permission_level': site_info.get('permissionLevel'),
            }

        except HttpError as e:
            return self.client.handle_api_error(e, f"get_site_info for {site_url}")

    def get_sitemaps(self, site_url: str) -> List[Dict]:
        """
        Get list of sitemaps for a site

        Args:
            site_url: Site URL

        Returns:
            List of sitemap information
        """
        try:
            response = self.service.sitemaps().list(siteUrl=site_url).execute()
            sitemaps = response.get('sitemap', [])

            logger.info(f"Retrieved {len(sitemaps)} sitemaps for {site_url}")

            return [{
                'error': False,
                'path': sitemap.get('path'),
                'last_submitted': sitemap.get('lastSubmitted'),
                'is_pending': sitemap.get('isPending'),
                'is_sitemaps_index': sitemap.get('isSitemapsIndex'),
            } for sitemap in sitemaps]

        except HttpError as e:
            error_info = self.client.handle_api_error(e, f"get_sitemaps for {site_url}")
            return [error_info]

    def get_search_analytics(
        self,
        site_url: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        dimensions: Optional[List[str]] = None,
        filters: Optional[List[Dict]] = None,
        row_limit: int = 1000
    ) -> Dict:
        """
        Get search analytics data (impressions, clicks, CTR, position)

        Args:
            site_url: Site URL
            start_date: Start date in YYYY-MM-DD format (default: 30 days ago)
            end_date: End date in YYYY-MM-DD format (default: today)
            dimensions: List of dimensions (page, query, country, device, searchAppearance)
            filters: List of filter objects
            row_limit: Maximum number of rows to return

        Returns:
            Dictionary with search analytics data
        """
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        # Default dimension is page
        if not dimensions:
            dimensions = ['page']

        request_body = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': dimensions,
            'rowLimit': row_limit,
        }

        if filters:
            request_body['dimensionFilterGroups'] = [{
                'filters': filters
            }]

        try:
            response = self.service.searchanalytics().query(
                siteUrl=site_url,
                body=request_body
            ).execute()

            rows = response.get('rows', [])
            logger.info(f"Retrieved {len(rows)} search analytics rows for {site_url}")

            return {
                'error': False,
                'site_url': site_url,
                'start_date': start_date,
                'end_date': end_date,
                'dimensions': dimensions,
                'row_count': len(rows),
                'rows': rows,
            }

        except HttpError as e:
            return self.client.handle_api_error(e, f"get_search_analytics for {site_url}")

    def get_page_analytics(
        self,
        site_url: str,
        page_url: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        Get search analytics for a specific page with retry logic

        Args:
            site_url: Site URL
            page_url: Specific page URL to filter
            start_date: Start date
            end_date: End date

        Returns:
            Dictionary with page analytics
        """
        filters = [{
            'dimension': 'page',
            'operator': 'equals',
            'expression': page_url
        }]

        # Retry loop for transient failures
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            result = self.get_search_analytics(
                site_url=site_url,
                start_date=start_date,
                end_date=end_date,
                dimensions=['query'],  # Group by query
                filters=filters,
                row_limit=100
            )

            if result.get('error'):
                # Check if error is transient (timeout, SSL, connection)
                error_msg = str(result.get('message', '')).lower()
                is_transient = any(keyword in error_msg for keyword in ['timeout', 'ssl', 'connection', 'socket', 'server error'])

                if is_transient and attempt < MAX_RETRIES:
                    last_error = result
                    logger.warning(f"⚠️ Transient error in Search Analytics on attempt {attempt}/{MAX_RETRIES} for {page_url}: {error_msg}")
                    time.sleep(RETRY_DELAY_SECONDS * attempt)
                    continue

                # Non-transient error or max retries reached
                return result

            # Calculate aggregated metrics
            rows = result.get('rows', [])
            total_clicks = sum(row.get('clicks', 0) for row in rows)
            total_impressions = sum(row.get('impressions', 0) for row in rows)
            avg_ctr = total_clicks / total_impressions if total_impressions > 0 else 0
            avg_position = sum(row.get('position', 0) for row in rows) / len(rows) if rows else 0

            logger.info(f"✅ Search Analytics for {page_url} (attempt {attempt}): {len(rows)} queries")

            return {
                'error': False,
                'page_url': page_url,
                'start_date': result['start_date'],
                'end_date': result['end_date'],
                'clicks': total_clicks,
                'impressions': total_impressions,
                'ctr': round(avg_ctr * 100, 2),  # Convert to percentage
                'avg_position': round(avg_position, 1),
                'query_count': len(rows),
                'top_queries': rows[:10],  # Top 10 queries
            }

        # All retries exhausted
        logger.error(f"❌ All {MAX_RETRIES} attempts failed for Search Analytics: {page_url}")
        return last_error if last_error else {'error': True, 'message': 'Unknown error'}

    def get_index_status(self, site_url: str, page_url: str) -> Dict:
        """
        Get indexing status for a specific URL using URL Inspection API

        This method provides accurate, real-time indexing status from Google Search Console.
        It replaces the old approach of using impressions > 0 to determine indexing.

        Responsibility:
        - Query URL Inspection API for actual Google index status
        - Parse and normalize response data
        - Handle API errors gracefully
        - Retry on transient failures (timeout, SSL errors)

        Args:
            site_url: Site URL in sc-domain format (e.g., 'sc-domain:example.com')
            page_url: Full URL to check (e.g., 'https://example.com/page')

        Returns:
            Dictionary with index status:
            {
                'error': False,
                'is_indexed': True,           # True if verdict == 'PASS'
                'verdict': 'PASS',            # PASS, PARTIAL, FAIL, NEUTRAL, UNKNOWN
                'coverage_state': 'Submitted and indexed',
                'indexing_state': 'INDEXING_ALLOWED',
                'crawled_as': 'MOBILE',
                'page_fetch_state': 'SUCCESSFUL',
                'last_crawl_time': '2026-01-27T05:35:39Z'
            }

            On error:
            {
                'error': True,
                'message': 'Error description',
                'page_url': 'https://...'
            }

        Notes:
        - This is a real-time API call, can take 30-60+ seconds
        - HTTP timeout set to 90 seconds to prevent premature timeouts
        - Retries up to 3 times on transient failures (timeout, SSL errors)
        - Failures are logged but non-fatal (caller should handle gracefully)
        """
        last_error = None

        # Retry loop for transient failures
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # Use URL Inspection API for accurate index status
                request_body = {
                    'inspectionUrl': page_url,
                    'siteUrl': site_url,
                }

                response = self.service.urlInspection().index().inspect(
                    body=request_body
                ).execute()

                # Extract index status from response
                inspection_result = response.get('inspectionResult', {})
                index_status_result = inspection_result.get('indexStatusResult', {})

                # Get coverage state and verdict
                coverage_state = index_status_result.get('coverageState', 'Unknown')
                verdict = index_status_result.get('verdict', 'UNKNOWN')

                # Determine if indexed based on verdict
                # Possible verdicts: PASS, PARTIAL, FAIL, NEUTRAL, UNKNOWN
                # Only PASS means fully indexed
                is_indexed = verdict == 'PASS'

                # Get additional details
                crawled_as = index_status_result.get('crawledAs', 'Unknown')
                indexing_state = index_status_result.get('indexingState', 'Unknown')
                page_fetch_state = index_status_result.get('pageFetchState', 'Unknown')

                logger.info(f"✅ Index status for {page_url} (attempt {attempt}): verdict={verdict}, coverage={coverage_state}")

                return {
                    'error': False,
                    'page_url': page_url,
                    'is_indexed': is_indexed,
                    'verdict': verdict,
                    'coverage_state': coverage_state,
                    'indexing_state': indexing_state,
                    'crawled_as': crawled_as,
                    'page_fetch_state': page_fetch_state,
                    'last_crawl_time': index_status_result.get('lastCrawlTime'),
                }

            except HttpError as e:
                # Handle API errors (404, permission errors, quota exceeded, etc.)
                # Don't retry on 4xx errors (client errors)
                if e.resp.status < 500:
                    error_result = self.client.handle_api_error(e, f"get_index_status for {page_url}")
                    error_result['page_url'] = page_url
                    return error_result

                # Retry on 5xx errors (server errors)
                last_error = e
                logger.warning(f"⚠️ HTTP {e.resp.status} error on attempt {attempt}/{MAX_RETRIES} for {page_url}: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_SECONDS * attempt)  # Exponential backoff
                    continue

            except Exception as e:
                # Handle unexpected errors (SSL, network, timeout, parsing errors, etc.)
                error_str = str(e).lower()

                # Retry on transient errors (timeout, SSL, connection)
                is_transient = any(keyword in error_str for keyword in ['timeout', 'ssl', 'connection', 'socket'])

                if is_transient and attempt < MAX_RETRIES:
                    last_error = e
                    logger.warning(f"⚠️ Transient error on attempt {attempt}/{MAX_RETRIES} for {page_url}: {e}")
                    time.sleep(RETRY_DELAY_SECONDS * attempt)  # Exponential backoff
                    continue

                # Don't retry on non-transient errors
                logger.error(f"❌ Non-retryable error checking index status for {page_url}: {e}", exc_info=True)
                return {
                    'error': True,
                    'message': f"Unexpected error: {str(e)}",
                    'page_url': page_url,
                    'error_type': type(e).__name__,
                }

        # All retries exhausted
        logger.error(f"❌ All {MAX_RETRIES} attempts failed for {page_url}: {last_error}")
        return {
            'error': True,
            'message': f"Failed after {MAX_RETRIES} attempts: {str(last_error)}",
            'page_url': page_url,
            'error_type': type(last_error).__name__ if last_error else 'Unknown',
        }

    def list_sites(self) -> List[Dict]:
        """
        List all sites the service account has access to

        Returns:
            List of site URLs
        """
        try:
            response = self.service.sites().list().execute()
            sites = response.get('siteEntry', [])

            logger.info(f"Retrieved {len(sites)} sites from Search Console")

            return [{
                'site_url': site.get('siteUrl'),
                'permission_level': site.get('permissionLevel'),
            } for site in sites]

        except HttpError as e:
            error_info = self.client.handle_api_error(e, "list_sites")
            return [error_info]

    def batch_get_index_status(self, site_url: str, page_urls: List[str]) -> List[Dict]:
        """
        Get index status for multiple URLs using batch request

        Batch requests dramatically improve performance by combining multiple
        API calls into a single HTTP request, reducing network overhead.

        Performance:
        - Sequential: 17 pages × 15s = 255s (4min 15s)
        - Batch: 1 request = 20-30s
        - Improvement: 8-12x faster

        Args:
            site_url: Site URL in sc-domain format
            page_urls: List of page URLs to check (max 100 per batch)

        Returns:
            List of index status dictionaries (one per URL)

        Notes:
            - Combines up to 100 requests into single HTTP request
            - Quota still counts per URL (10 URLs = 10 quota)
            - Much faster than sequential requests
            - Reduces SSL error surface area
        """
        if not page_urls:
            return []

        # Google API supports max 100 requests per batch
        if len(page_urls) > 100:
            logger.warning(f"Batch size {len(page_urls)} exceeds limit 100, will process in chunks")
            results = []
            for i in range(0, len(page_urls), 100):
                chunk = page_urls[i:i+100]
                results.extend(self.batch_get_index_status(site_url, chunk))
            return results

        results = {}
        errors = {}

        def create_callback(page_url):
            """Create callback for batch request response"""
            def callback(request_id, response, exception):
                if exception:
                    logger.warning(f"⚠️ Batch error for {page_url}: {exception}")
                    errors[page_url] = {
                        'error': True,
                        'message': str(exception),
                        'page_url': page_url,
                        'error_type': type(exception).__name__,
                    }
                else:
                    # Parse successful response
                    try:
                        inspection_result = response.get('inspectionResult', {})
                        index_status_result = inspection_result.get('indexStatusResult', {})

                        coverage_state = index_status_result.get('coverageState', 'Unknown')
                        verdict = index_status_result.get('verdict', 'UNKNOWN')
                        is_indexed = verdict == 'PASS'

                        results[page_url] = {
                            'error': False,
                            'page_url': page_url,
                            'is_indexed': is_indexed,
                            'verdict': verdict,
                            'coverage_state': coverage_state,
                            'indexing_state': index_status_result.get('indexingState', 'Unknown'),
                            'crawled_as': index_status_result.get('crawledAs', 'Unknown'),
                            'page_fetch_state': index_status_result.get('pageFetchState', 'Unknown'),
                            'last_crawl_time': index_status_result.get('lastCrawlTime'),
                        }
                        logger.debug(f"✅ Batch index status for {page_url}: verdict={verdict}")
                    except Exception as e:
                        logger.error(f"❌ Failed to parse batch response for {page_url}: {e}")
                        errors[page_url] = {
                            'error': True,
                            'message': f"Parse error: {str(e)}",
                            'page_url': page_url,
                            'error_type': 'ParseError',
                        }
            return callback

        try:
            # Create batch request
            batch = self.service.new_batch_http_request()

            # Add each URL inspection to batch
            for page_url in page_urls:
                request_body = {
                    'inspectionUrl': page_url,
                    'siteUrl': site_url,
                }
                request = self.service.urlInspection().index().inspect(body=request_body)
                batch.add(request, callback=create_callback(page_url))

            # Execute batch (single HTTP request for all URLs)
            logger.info(f"🚀 Executing batch URL inspection for {len(page_urls)} pages")
            batch.execute()

            # Combine results and errors
            all_results = []
            for page_url in page_urls:
                if page_url in results:
                    all_results.append(results[page_url])
                elif page_url in errors:
                    all_results.append(errors[page_url])
                else:
                    # Should not happen, but handle gracefully
                    all_results.append({
                        'error': True,
                        'message': 'No response received',
                        'page_url': page_url,
                        'error_type': 'MissingResponse',
                    })

            success_count = len([r for r in all_results if not r.get('error')])
            logger.info(f"✅ Batch complete: {success_count}/{len(page_urls)} successful")

            return all_results

        except Exception as e:
            logger.error(f"❌ Batch request failed: {e}", exc_info=True)
            # Return error for all URLs
            return [{
                'error': True,
                'message': f"Batch request failed: {str(e)}",
                'page_url': page_url,
                'error_type': type(e).__name__,
            } for page_url in page_urls]
