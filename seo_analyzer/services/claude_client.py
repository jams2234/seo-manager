"""
Claude API Client Service
Wrapper for Anthropic Claude API with rate limiting and caching.
"""
import logging
import hashlib
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from functools import wraps

from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)


class ClaudeRateLimiter:
    """Simple rate limiter for API calls"""

    def __init__(self, max_calls: int = 50, period: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed
            period: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self.cache_key = 'claude_rate_limiter'

    def acquire(self) -> bool:
        """
        Try to acquire a rate limit slot.

        Returns:
            True if acquired, False if rate limited
        """
        now = time.time()
        window_start = now - self.period

        # Get current window data
        calls = cache.get(self.cache_key, [])

        # Remove old calls outside the window
        calls = [t for t in calls if t > window_start]

        # Check if we can make a new call
        if len(calls) >= self.max_calls:
            return False

        # Add current call
        calls.append(now)
        cache.set(self.cache_key, calls, self.period * 2)

        return True

    def wait_if_needed(self):
        """Wait until a rate limit slot is available"""
        while not self.acquire():
            logger.info("Rate limited, waiting 1 second...")
            time.sleep(1)


class ClaudeAPIClient:
    """
    Client for Anthropic Claude API.
    Provides rate limiting, caching, and error handling.
    """

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        max_tokens: int = None,
    ):
        """
        Initialize Claude API client.

        Args:
            api_key: Anthropic API key (defaults to settings)
            model: Model to use (defaults to settings)
            max_tokens: Max tokens for response (defaults to settings)
        """
        self.api_key = api_key or getattr(settings, 'ANTHROPIC_API_KEY', '')
        self.model = model or getattr(settings, 'CLAUDE_MODEL', 'claude-sonnet-4-20250514')
        self.max_tokens = max_tokens or getattr(settings, 'CLAUDE_MAX_TOKENS', 4096)
        self.cache_ttl = getattr(settings, 'CLAUDE_CACHE_TTL', 86400)

        # Rate limiter
        rate_limit = getattr(settings, 'CLAUDE_RATE_LIMIT_PER_MINUTE', 50)
        self.rate_limiter = ClaudeRateLimiter(max_calls=rate_limit, period=60)

        # Lazy import anthropic client
        self._client = None

    @property
    def client(self):
        """Lazy load Anthropic client"""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        return self._client

    def _get_cache_key(self, prompt: str, system: str = None) -> str:
        """Generate cache key for request"""
        content = f"{self.model}:{system or ''}:{prompt}"
        return f"claude_response_{hashlib.sha256(content.encode()).hexdigest()}"

    def _get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """Get cached response if available"""
        return cache.get(cache_key)

    def _cache_response(self, cache_key: str, response: Dict):
        """Cache response"""
        cache.set(cache_key, response, self.cache_ttl)

    def chat(
        self,
        prompt: str = None,
        messages: List[Dict] = None,
        system: str = None,
        use_cache: bool = True,
        temperature: float = 0.7,
    ) -> Dict:
        """
        Send a chat message to Claude.

        Args:
            prompt: User message/prompt (single message)
            messages: List of message dicts with 'role' and 'content' (conversation history)
            system: System message (optional)
            use_cache: Whether to use caching
            temperature: Response temperature (0-1)

        Returns:
            {
                'success': True/False,
                'content': 'Response text',
                'response': 'Response text (alias)',
                'model': 'claude-...',
                'usage': {'input_tokens': X, 'output_tokens': Y},
                'cached': True/False,
                'error': 'Error message if failed'
            }
        """
        if not self.api_key:
            return {
                'success': False,
                'error': 'Anthropic API key not configured',
                'content': None,
                'response': None,
            }

        # Build messages from prompt or use provided messages
        if messages:
            api_messages = messages
            cache_content = str(messages)
        elif prompt:
            api_messages = [{"role": "user", "content": prompt}]
            cache_content = prompt
        else:
            return {
                'success': False,
                'error': 'Either prompt or messages is required',
                'content': None,
                'response': None,
            }

        # Check cache
        cache_key = self._get_cache_key(cache_content, system)
        if use_cache:
            cached = self._get_cached_response(cache_key)
            if cached:
                logger.info("Returning cached Claude response")
                cached['cached'] = True
                return cached

        # Wait for rate limit
        self.rate_limiter.wait_if_needed()

        try:
            # Create request kwargs
            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": api_messages,
                "temperature": temperature,
            }

            if system:
                kwargs["system"] = system

            # Make API call
            logger.info(f"Calling Claude API with model: {self.model}")
            response = self.client.messages.create(**kwargs)

            # Extract response
            content = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, 'text'):
                        content += block.text

            result = {
                'success': True,
                'content': content,
                'response': content,  # Alias for backwards compatibility
                'model': response.model,
                'usage': {
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens,
                },
                'cached': False,
                'stop_reason': response.stop_reason,
            }

            # Cache successful response
            if use_cache:
                self._cache_response(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"Claude API error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'content': None,
                'response': None,
            }

    def analyze_json(
        self,
        prompt: str,
        system: str = None,
        use_cache: bool = True,
    ) -> Dict:
        """
        Send a prompt expecting JSON response.

        Args:
            prompt: User message/prompt
            system: System message (optional)
            use_cache: Whether to use caching

        Returns:
            Parsed JSON response or error dict
        """
        # Add JSON instruction to system prompt
        json_system = (system or "") + """

IMPORTANT: Your response must be valid JSON only. Do not include any text before or after the JSON.
Do not wrap the JSON in markdown code blocks.
"""

        result = self.chat(prompt, system=json_system.strip(), use_cache=use_cache, temperature=0.3)

        if not result.get('success'):
            return result

        # Try to parse JSON from response
        content = result.get('content', '')

        # Clean up potential markdown code blocks
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()

        try:
            parsed = json.loads(content)
            result['parsed'] = parsed
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            result['parse_error'] = str(e)
            return result

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        Uses approximation: ~4 characters per token.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        # Simple approximation
        return len(text) // 4


class ClaudeAnalyzer:
    """
    High-level analyzer using Claude for SEO analysis.
    """

    def __init__(self):
        self.client = ClaudeAPIClient()

    def analyze_sitemap(
        self,
        entries: List[Dict],
        domain_info: Dict = None,
    ) -> Dict:
        """
        Analyze sitemap entries for SEO issues.

        Args:
            entries: List of sitemap entry dicts with loc, lastmod, changefreq, priority
            domain_info: Optional domain context

        Returns:
            Analysis result with issues and suggestions
        """
        # Limit entries for context window
        sample_size = min(50, len(entries))
        sample_entries = entries[:sample_size]

        # Build prompt
        entries_text = "\n".join([
            f"- {e.get('loc')} (priority: {e.get('priority')}, changefreq: {e.get('changefreq')}, lastmod: {e.get('lastmod')})"
            for e in sample_entries
        ])

        system = """당신은 SEO 전문가입니다. 사용자가 선택한 특정 URL들만 분석하세요.
중요: 전체 사이트맵이 아니라, 사용자가 분석 대상으로 "선택한 URL들만" 분석합니다.

분석 중점:
1. 각 URL의 구조 및 내용 추정
2. 우선순위(priority) 값 적절성
3. 변경 빈도(changefreq) 적절성
4. lastmod 날짜 상태
5. 각 URL별 개선 제안

모든 응답은 한국어로 작성하세요."""

        prompt = f"""다음은 사용자가 AI 분석 대상으로 선택한 URL 목록입니다 (도메인: {domain_info.get('domain_name', '웹사이트') if domain_info else '웹사이트'}):

{entries_text}

**중요: 위 {len(entries)}개의 URL만 분석 대상입니다. 전체 사이트맵이 아닙니다.**
분석 대상 URL 수: {len(entries)}개

선택된 {len(entries)}개의 URL에 대해서만 다음 JSON 형식으로 분석 결과를 제공하세요 (한국어로):
{{
    "overall_health_score": 0-100,
    "analyzed_url_count": {len(entries)},
    "issues": [
        {{
            "type": "이슈_유형",
            "severity": "critical|warning|info",
            "description": "문제 설명",
            "affected_urls": ["분석대상 URL 중에서만"],
            "suggestion": "해결 방법"
        }}
    ],
    "suggestions": [
        {{
            "type": "제안_유형",
            "description": "제안 설명",
            "affected_urls": ["분석대상 URL"],
            "recommended_value": "권장 값",
            "current_value": "현재 값"
        }}
    ],
    "summary": "선택된 {len(entries)}개 URL에 대한 분석 요약 (한국어)"
}}"""

        return self.client.analyze_json(prompt, system=system)

    def suggest_entry_improvements(
        self,
        entry: Dict,
        page_metrics: Dict = None,
    ) -> Dict:
        """
        Get AI suggestions for a single sitemap entry.

        Args:
            entry: Sitemap entry dict
            page_metrics: Optional SEO metrics for the page

        Returns:
            Suggestions for the entry
        """
        system = """당신은 SEO 전문가입니다. 사이트맵 항목을 분석하고 페이지 지표와 URL 패턴을 기반으로 최적의 값을 제안하세요. 모든 응답은 한국어로 작성하세요."""

        metrics_text = ""
        if page_metrics:
            metrics_text = f"""
페이지 지표:
- SEO 점수: {page_metrics.get('seo_score')}
- 트래픽 (클릭): {page_metrics.get('clicks')}
- 노출: {page_metrics.get('impressions')}
- 평균 순위: {page_metrics.get('avg_position')}
- 색인 여부: {page_metrics.get('is_indexed')}"""

        prompt = f"""이 사이트맵 항목을 분석하고 개선 사항을 제안해주세요:

URL: {entry.get('loc')}
현재 우선순위: {entry.get('priority')}
현재 변경빈도: {entry.get('changefreq')}
현재 최종수정일: {entry.get('lastmod')}
{metrics_text}

다음 JSON 형식으로 제안을 제공하세요 (한국어로):
{{
    "recommended_priority": 0.0-1.0 또는 null,
    "recommended_changefreq": "always|hourly|daily|weekly|monthly|yearly|never" 또는 null,
    "priority_reason": "이 우선순위를 권장하는 이유",
    "changefreq_reason": "이 변경빈도를 권장하는 이유",
    "other_suggestions": ["제안1", "제안2"]
}}"""

        return self.client.analyze_json(prompt, system=system)

    def analyze_seo_issues(
        self,
        issues: List[Dict],
        domain_info: Dict = None,
    ) -> Dict:
        """
        Analyze SEO issues and provide prioritized action plan.

        Args:
            issues: List of SEO issue dicts
            domain_info: Optional domain context

        Returns:
            Analysis with prioritized action plan
        """
        # Limit issues for context
        sample_size = min(30, len(issues))
        sample_issues = issues[:sample_size]

        issues_text = "\n".join([
            f"- [{i.get('severity')}] {i.get('title')}: {i.get('message')} (Page: {i.get('page_url', 'unknown')})"
            for i in sample_issues
        ])

        system = """당신은 웹사이트 문제를 분석하는 SEO 전문가입니다. 영향도에 따라 문제의 우선순위를 정하고 실행 가능한 권장사항을 제공하세요. 모든 응답은 한국어로 작성하세요."""

        prompt = f"""다음 SEO 이슈를 분석해주세요 ({domain_info.get('domain_name', '웹사이트') if domain_info else '웹사이트'}):

{issues_text}

전체 이슈 수: {len(issues)}
표시된 샘플: {sample_size}

다음 JSON 형식으로 분석 결과를 제공하세요 (한국어로):
{{
    "priority_actions": [
        {{
            "priority": 1,
            "action": "수행할 작업",
            "impact": "예상 효과",
            "affected_issues": ["이슈_유형1", "이슈_유형2"],
            "estimated_effort": "low|medium|high"
        }}
    ],
    "quick_wins": ["빠른 개선 1", "빠른 개선 2"],
    "long_term_recommendations": ["장기 권장사항 1"],
    "summary": "전체 요약"
}}"""

        return self.client.analyze_json(prompt, system=system)
