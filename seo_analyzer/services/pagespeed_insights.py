"""
PageSpeed Insights API Service
"""
import logging
import requests
import time
from typing import Dict, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class PageSpeedInsightsService:
    """
    Service for fetching Lighthouse scores and Core Web Vitals from PageSpeed Insights API
    Uses API Key authentication (Service Account not supported by this API)
    """

    API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize PageSpeed Insights service with API Key

        Args:
            api_key: Google API key (optional, uses settings if not provided)
        """
        self.api_key = api_key or getattr(settings, 'GOOGLE_API_KEY', '')

    def analyze_url(
        self,
        url: str,
        strategy: str = 'mobile',
        categories: Optional[list] = None,
        max_retries: int = 3
    ) -> Dict:
        """
        Analyze a URL using PageSpeed Insights API with retry logic

        Args:
            url: The URL to analyze
            strategy: 'mobile' or 'desktop'
            categories: List of categories to analyze
            max_retries: Maximum number of retry attempts

        Returns:
            Dictionary with analysis results or error information
        """
        if categories is None:
            categories = ['performance', 'accessibility', 'seo', 'pwa', 'best-practices']

        params = {
            'url': url,
            'strategy': strategy,
            'category': categories,
        }

        # Add API key if available
        if self.api_key:
            params['key'] = self.api_key
            logger.debug(f"Using API key for {url}")
        else:
            logger.debug(f"Using free quota (no API key) for {url}")

        # Retry logic with exponential backoff
        retry_delay = 2  # Initial retry delay in seconds
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Analyzing {url} ({strategy}) - "
                    f"Attempt {attempt + 1}/{max_retries}"
                )

                response = requests.get(
                    self.API_URL,
                    params=params,
                    timeout=60
                )
                response.raise_for_status()

                data = response.json()
                return self._extract_metrics(data, strategy)

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code
                last_error = e

                if status_code == 429:  # Rate limit exceeded
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"Rate limit hit for {url}. "
                            f"Waiting {wait_time}s before retry {attempt + 2}/{max_retries}"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Rate limit exceeded for {url} after {max_retries} attempts")
                        return self._error_response(
                            url, strategy,
                            'Rate limit exceeded. Please try again later.',
                            status_code
                        )

                elif status_code in [400, 404]:  # Bad request or not found
                    logger.error(f"Invalid URL or page not found: {url} ({status_code})")
                    return self._error_response(
                        url, strategy,
                        f'Invalid URL or page not found (HTTP {status_code})',
                        status_code
                    )

                elif status_code >= 500:  # Server error - retry
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        logger.warning(
                            f"Server error ({status_code}) for {url}. "
                            f"Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Server error persists for {url} after {max_retries} attempts")
                        return self._error_response(
                            url, strategy,
                            f'PageSpeed Insights server error (HTTP {status_code})',
                            status_code
                        )

                else:  # Other HTTP errors
                    logger.error(f"HTTP error {status_code} for {url}: {e}")
                    return self._error_response(
                        url, strategy,
                        f'HTTP error {status_code}: {str(e)}',
                        status_code
                    )

            except requests.exceptions.Timeout:
                last_error = 'Timeout'
                if attempt < max_retries - 1:
                    logger.warning(f"Timeout for {url}. Retrying...")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"Timeout for {url} after {max_retries} attempts")
                    return self._error_response(url, strategy, 'Request timeout')

            except requests.exceptions.ConnectionError as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"Connection error for {url}. Retrying...")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"Connection error for {url} after {max_retries} attempts")
                    return self._error_response(url, strategy, 'Connection error')

            except Exception as e:
                logger.error(f"Unexpected error analyzing {url}: {e}", exc_info=True)
                return self._error_response(url, strategy, f'Unexpected error: {str(e)}')

        # If we get here, all retries failed
        return self._error_response(
            url, strategy,
            f'All {max_retries} attempts failed. Last error: {last_error}'
        )

    def _error_response(
        self,
        url: str,
        strategy: str,
        message: str,
        status_code: Optional[int] = None
    ) -> Dict:
        """Create standardized error response"""
        response = {
            'error': True,
            'url': url,
            'strategy': strategy,
            'message': message,
        }
        if status_code:
            response['status_code'] = status_code
        return response

    def _extract_metrics(self, data: Dict, strategy: str) -> Dict:
        """
        Extract relevant metrics from PageSpeed Insights response

        Args:
            data: Raw API response
            strategy: 'mobile' or 'desktop'

        Returns:
            Dictionary with extracted metrics
        """
        try:
            lighthouse = data.get('lighthouseResult', {})
            categories = lighthouse.get('categories', {})
            audits = lighthouse.get('audits', {})

            # Extract Lighthouse scores (0-100)
            scores = {
                'performance_score': self._get_score(categories.get('performance')),
                'accessibility_score': self._get_score(categories.get('accessibility')),
                'seo_score': self._get_score(categories.get('seo')),
                'pwa_score': self._get_score(categories.get('pwa')),
                'best_practices_score': self._get_score(categories.get('best-practices')),
            }

            # Extract Core Web Vitals
            core_web_vitals = {
                'lcp': self._get_metric_value(audits.get('largest-contentful-paint')),  # Largest Contentful Paint (seconds)
                'fid': self._get_metric_value(audits.get('max-potential-fid')),  # First Input Delay (ms)
                'cls': self._get_metric_value(audits.get('cumulative-layout-shift')),  # Cumulative Layout Shift
                'fcp': self._get_metric_value(audits.get('first-contentful-paint')),  # First Contentful Paint (seconds)
                'tti': self._get_metric_value(audits.get('interactive')),  # Time to Interactive (seconds)
                'tbt': self._get_metric_value(audits.get('total-blocking-time')),  # Total Blocking Time (ms)
            }

            # Mobile/Desktop specific score
            if strategy == 'mobile':
                scores['mobile_score'] = scores['performance_score']
            else:
                scores['desktop_score'] = scores['performance_score']

            result = {
                'error': False,
                'url': lighthouse.get('finalUrl', ''),
                'strategy': strategy,
                **scores,
                **core_web_vitals,
                'fetch_time': lighthouse.get('fetchTime', ''),
            }

            logger.info(f"Successfully extracted metrics for {result['url']}")
            return result

        except Exception as e:
            logger.error(f"Error extracting PageSpeed metrics: {e}")
            return {
                'error': True,
                'message': f"Failed to extract metrics: {str(e)}"
            }

    @staticmethod
    def _get_score(category: Optional[Dict]) -> Optional[int]:
        """
        Extract score from category object

        Args:
            category: Category object from Lighthouse results

        Returns:
            Score as integer (0-100) or None
        """
        if not category:
            return None

        score = category.get('score')
        if score is None:
            return None

        # Lighthouse scores are 0-1, convert to 0-100
        return round(score * 100)

    @staticmethod
    def _get_metric_value(audit: Optional[Dict]) -> Optional[float]:
        """
        Extract numeric value from audit object

        Args:
            audit: Audit object from Lighthouse results

        Returns:
            Metric value or None
        """
        if not audit:
            return None

        # Try numericValue first (preferred)
        numeric_value = audit.get('numericValue')
        if numeric_value is not None:
            return numeric_value

        # Fallback to displayValue parsing
        display_value = audit.get('displayValue', '')
        try:
            # Remove units and parse
            value_str = display_value.split()[0].replace(',', '').replace('s', '').replace('ms', '')
            return float(value_str)
        except (ValueError, IndexError):
            return None

    def analyze_both_strategies(self, url: str, mobile_only: bool = False) -> Dict:
        """
        Analyze URL for both mobile and desktop (or mobile only for speed)

        Args:
            url: The URL to analyze
            mobile_only: If True, only analyze mobile (2x faster)

        Returns:
            Dictionary with combined results
        """
        # For faster scans, mobile-only is recommended (Google uses mobile-first indexing)
        if mobile_only:
            mobile_result = self.analyze_url(url, strategy='mobile')

            if mobile_result.get('error'):
                return {
                    'url': url,
                    'error': True,
                    'message': mobile_result.get('message'),
                    'mobile': mobile_result,
                    'primary_scores': {}
                }

            return {
                'url': url,
                'error': False,
                'mobile': mobile_result,
                'desktop': None,
                'primary_scores': {
                    'performance_score': mobile_result.get('performance_score'),
                    'accessibility_score': mobile_result.get('accessibility_score'),
                    'seo_score': mobile_result.get('seo_score'),
                    'pwa_score': mobile_result.get('pwa_score'),
                    'best_practices_score': mobile_result.get('best_practices_score'),
                    'mobile_score': mobile_result.get('mobile_score'),
                    'desktop_score': None,
                }
            }

        # Full analysis (mobile + desktop) - slower but comprehensive
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as executor:
            mobile_future = executor.submit(self.analyze_url, url, 'mobile')
            desktop_future = executor.submit(self.analyze_url, url, 'desktop')

            mobile_result = mobile_future.result()
            desktop_result = desktop_future.result()

        # Combine results
        combined = {
            'url': url,
            'mobile': mobile_result,
            'desktop': desktop_result,
        }

        # If either has errors, mark as error
        if mobile_result.get('error') or desktop_result.get('error'):
            combined['error'] = True
        else:
            combined['error'] = False
            # Take mobile scores as primary (mobile-first indexing)
            combined['primary_scores'] = {
                'performance_score': mobile_result.get('performance_score'),
                'accessibility_score': mobile_result.get('accessibility_score'),
                'seo_score': mobile_result.get('seo_score'),
                'pwa_score': mobile_result.get('pwa_score'),
                'best_practices_score': mobile_result.get('best_practices_score'),
                'mobile_score': mobile_result.get('mobile_score'),
                'desktop_score': desktop_result.get('desktop_score'),
            }

        return combined
