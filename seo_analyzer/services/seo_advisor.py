"""
AI SEO Advisor Service
페이지 분석, 이슈 감지, 자동 수정 제안
"""
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from urllib.parse import urlparse, urljoin
from datetime import datetime
import re

from .base import AnalyzerService

logger = logging.getLogger(__name__)


class SEOAdvisor(AnalyzerService):
    """
    AI-based SEO Advisor
    Analyzes pages, detects issues, and suggests improvements
    """

    # Severity levels
    SEVERITY_CRITICAL = 'critical'
    SEVERITY_WARNING = 'warning'
    SEVERITY_INFO = 'info'

    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; SEOAnalyzerBot/1.0)'
        })
        self._last_fetch_error = None

    def analyze(self, page_url: str, pagespeed_data: Optional[Dict] = None, **kwargs) -> Dict:
        """
        Comprehensive SEO analysis of a page

        Args:
            page_url: URL to analyze
            pagespeed_data: PageSpeed Insights data (optional)
            **kwargs: Additional options

        Returns:
            {
                'url': 'https://...',
                'overall_health': 75,
                'issues': [...],
                'action_plan': {...},
                'auto_fix': {...},
                'estimated_time': '약 2시간',
                'potential_score_gain': 15,
            }
        """
        self.log_info(f"🔍 Starting SEO analysis: {page_url}")
        self._last_fetch_error = None

        # 1. Fetch HTML
        html_content = self._fetch_html(page_url)
        if not html_content:
            error_msg = self._last_fetch_error or 'Failed to fetch page'
            return {'error': True, 'message': f'Failed to fetch page: {error_msg}'}

        soup = BeautifulSoup(html_content, 'html.parser')

        # 2. Analyze each category
        issues = []

        # Meta tags analysis
        issues.extend(self._analyze_meta_tags(soup, page_url))

        # Title tag analysis
        issues.extend(self._analyze_title_tag(soup))

        # Heading tags analysis
        issues.extend(self._analyze_headings(soup))

        # Image analysis
        issues.extend(self._analyze_images(soup, page_url))

        # Link analysis
        issues.extend(self._analyze_links(soup, page_url))

        # Content analysis
        issues.extend(self._analyze_content(soup))

        # PageSpeed data integration (if provided)
        if pagespeed_data:
            issues.extend(self._analyze_performance(pagespeed_data))

        # 3. Calculate health score
        overall_health = self._calculate_health_score(issues)

        # 4. Generate action plan
        action_plan = self._generate_action_plan(issues)

        # 5. Extract auto-fixable items
        auto_fix = self._extract_auto_fixable(issues)

        # 6. Calculate potential improvement
        potential_gain = self._calculate_potential_gain(issues)
        estimated_time = self._estimate_fix_time(issues)

        self.log_info(f"✅ Analysis complete: {page_url} (health: {overall_health})")

        return {
            'url': page_url,
            'overall_health': overall_health,
            'issues': issues,
            'action_plan': action_plan,
            'auto_fix': auto_fix,
            'auto_fix_count': auto_fix.get('count', 0),
            'estimated_time': estimated_time['formatted'],
            'estimated_time_minutes': estimated_time['minutes'],
            'potential_score_gain': potential_gain,
            'timestamp': datetime.now().isoformat(),
            'error': False,
        }

    def _fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML from URL"""
        import requests
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.exceptions.HTTPError as e:
            # HTTP error (404, 500, etc.)
            status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            if status_code:
                if status_code == 404:
                    self._last_fetch_error = "페이지를 찾을 수 없습니다 (HTTP 404)"
                else:
                    self._last_fetch_error = f"HTTP {status_code} 에러"
                self.log_error(f"HTTP {status_code} error fetching {url}: {e}")
            else:
                self._last_fetch_error = "페이지에 접근할 수 없습니다"
                self.log_error(f"HTTP error fetching {url}: {e}")
            return None
        except requests.exceptions.Timeout:
            self.log_error(f"Timeout fetching {url}")
            self._last_fetch_error = "요청 시간 초과 (15초)"
            return None
        except Exception as e:
            self.log_error(f"Failed to fetch {url}: {e}")
            self._last_fetch_error = f"페이지 가져오기 실패: {str(e)}"
            return None

    # ========== Analysis Methods ==========

    def _analyze_meta_tags(self, soup: BeautifulSoup, url: str) -> List[Dict]:
        """Analyze meta tags"""
        issues = []

        # Meta Description check
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc or not meta_desc.get('content'):
            issues.append({
                'type': 'meta_description_missing',
                'severity': self.SEVERITY_CRITICAL,
                'category': 'meta_tags',
                'title': '메타 설명 누락',
                'message': '메타 설명이 없습니다. 검색 결과에 표시될 설명을 추가하세요.',
                'fix': '120-160자 길이의 매력적인 설명을 작성하세요',
                'example': self._generate_meta_description_suggestion(soup, url),
                'auto_fix_available': True,
                'auto_fix_method': 'generate_meta_description',
                'impact': 'high',
            })
        elif meta_desc:
            content = meta_desc.get('content', '')
            if len(content) < 120:
                issues.append({
                    'type': 'meta_description_too_short',
                    'severity': self.SEVERITY_WARNING,
                    'category': 'meta_tags',
                    'title': '메타 설명이 너무 짧음',
                    'message': f'현재 {len(content)}자입니다. 120-160자가 권장됩니다.',
                    'current_value': content,
                    'fix': '더 자세한 설명으로 확장하세요',
                    'auto_fix_available': True,
                    'auto_fix_method': 'expand_meta_description',
                    'impact': 'medium',
                })
            elif len(content) > 160:
                issues.append({
                    'type': 'meta_description_too_long',
                    'severity': self.SEVERITY_WARNING,
                    'category': 'meta_tags',
                    'title': '메타 설명이 너무 김',
                    'message': f'현재 {len(content)}자입니다. 검색 결과에서 잘릴 수 있습니다.',
                    'current_value': content,
                    'fix': '160자 이내로 줄이세요',
                    'suggested_value': content[:157] + '...',
                    'auto_fix_available': True,
                    'auto_fix_method': 'shorten_meta_description',
                    'impact': 'medium',
                })

        # Open Graph tags check
        og_title = soup.find('meta', property='og:title')
        og_desc = soup.find('meta', property='og:description')
        og_image = soup.find('meta', property='og:image')

        missing_og = []
        if not og_title:
            missing_og.append('og:title')
        if not og_desc:
            missing_og.append('og:description')
        if not og_image:
            missing_og.append('og:image')

        if missing_og:
            issues.append({
                'type': 'open_graph_incomplete',
                'severity': self.SEVERITY_WARNING,
                'category': 'meta_tags',
                'title': 'Open Graph 태그 불완전',
                'message': '소셜 미디어 공유 최적화를 위해 Open Graph 태그를 추가하세요.',
                'missing': missing_og,
                'fix': '누락된 Open Graph 태그 추가',
                'auto_fix_available': True,
                'auto_fix_method': 'generate_open_graph_tags',
                'impact': 'medium',
            })

        return issues

    def _analyze_title_tag(self, soup: BeautifulSoup) -> List[Dict]:
        """Analyze title tag"""
        issues = []

        title_tag = soup.find('title')
        if not title_tag or not title_tag.text.strip():
            issues.append({
                'type': 'title_missing',
                'severity': self.SEVERITY_CRITICAL,
                'category': 'title',
                'title': '제목 태그 누락',
                'message': '페이지 제목이 없습니다. SEO에 치명적입니다.',
                'fix': '50-60자 길이의 명확한 제목을 작성하세요',
                'auto_fix_available': True,
                'auto_fix_method': 'generate_title',
                'impact': 'critical',
            })
        else:
            title_text = title_tag.text.strip()
            if len(title_text) < 30:
                issues.append({
                    'type': 'title_too_short',
                    'severity': self.SEVERITY_WARNING,
                    'category': 'title',
                    'title': '제목이 너무 짧음',
                    'message': f'현재 {len(title_text)}자입니다. 50-60자가 권장됩니다.',
                    'current_value': title_text,
                    'fix': '더 자세하고 설명적인 제목으로 확장하세요',
                    'auto_fix_available': True,
                    'auto_fix_method': 'expand_title',
                    'impact': 'medium',
                })
            elif len(title_text) > 60:
                issues.append({
                    'type': 'title_too_long',
                    'severity': self.SEVERITY_WARNING,
                    'category': 'title',
                    'title': '제목이 너무 김',
                    'message': f'현재 {len(title_text)}자입니다. 검색 결과에서 잘릴 수 있습니다.',
                    'current_value': title_text,
                    'fix': '60자 이내로 줄이세요',
                    'suggested_value': title_text[:57] + '...',
                    'auto_fix_available': True,
                    'auto_fix_method': 'shorten_title',
                    'impact': 'medium',
                })

        return issues

    def _analyze_headings(self, soup: BeautifulSoup) -> List[Dict]:
        """Analyze heading tags (H1-H6)"""
        issues = []

        # H1 tag check
        h1_tags = soup.find_all('h1')
        if not h1_tags:
            issues.append({
                'type': 'h1_missing',
                'severity': self.SEVERITY_CRITICAL,
                'category': 'headings',
                'title': 'H1 태그 없음',
                'message': 'H1 태그는 페이지의 주요 제목으로 필수입니다.',
                'fix': '페이지 주제를 나타내는 H1 태그를 추가하세요',
                'auto_fix_available': False,
                'impact': 'high',
            })
        elif len(h1_tags) > 1:
            issues.append({
                'type': 'multiple_h1',
                'severity': self.SEVERITY_WARNING,
                'category': 'headings',
                'title': '여러 개의 H1 태그',
                'message': f'{len(h1_tags)}개의 H1 태그가 발견되었습니다. 하나만 사용하세요.',
                'current_values': [h1.text.strip() for h1 in h1_tags],
                'fix': '가장 중요한 제목 하나만 H1으로 남기고, 나머지는 H2로 변경하세요',
                'auto_fix_available': False,
                'impact': 'medium',
            })

        return issues

    def _analyze_images(self, soup: BeautifulSoup, page_url: str) -> List[Dict]:
        """Analyze images"""
        issues = []

        images = soup.find_all('img')
        images_without_alt = []

        for img in images:
            # Alt text check
            if not img.get('alt'):
                images_without_alt.append(img.get('src', 'unknown'))

        # Alt text missing issue
        if images_without_alt:
            issues.append({
                'type': 'images_without_alt',
                'severity': self.SEVERITY_WARNING,
                'category': 'images',
                'title': 'Alt 텍스트 누락',
                'message': f'{len(images_without_alt)}개 이미지에 alt 속성이 없습니다.',
                'images': images_without_alt[:10],
                'fix': '모든 이미지에 설명적인 alt 텍스트를 추가하세요',
                'auto_fix_available': True,
                'auto_fix_method': 'generate_alt_texts',
                'impact': 'medium',
            })

        return issues

    def _analyze_links(self, soup: BeautifulSoup, page_url: str) -> List[Dict]:
        """Analyze links"""
        issues = []

        all_links = soup.find_all('a', href=True)
        internal_links = []

        parsed_url = urlparse(page_url)
        base_domain = parsed_url.netloc

        for link in all_links:
            href = link['href']

            # Classify internal/external links
            if href.startswith('http'):
                link_domain = urlparse(href).netloc
                if base_domain in link_domain:
                    internal_links.append(href)
            elif href.startswith('/'):
                internal_links.append(href)

        # Internal link shortage warning
        if len(internal_links) < 3:
            issues.append({
                'type': 'low_internal_links',
                'severity': self.SEVERITY_INFO,
                'category': 'links',
                'title': '내부 링크 부족',
                'message': f'내부 링크가 {len(internal_links)}개뿐입니다. 3-5개 권장.',
                'fix': '관련 페이지로 링크를 추가하여 사이트 구조를 강화하세요',
                'auto_fix_available': False,
                'impact': 'medium',
            })

        return issues

    def _analyze_content(self, soup: BeautifulSoup) -> List[Dict]:
        """Analyze content"""
        issues = []

        # Extract body text
        body_text = soup.get_text(separator=' ', strip=True)
        word_count = len(body_text.split())

        # Content length check
        if word_count < 300:
            issues.append({
                'type': 'thin_content',
                'severity': self.SEVERITY_WARNING,
                'category': 'content',
                'title': '콘텐츠 부족',
                'message': f'현재 {word_count}단어입니다. 최소 300단어 권장.',
                'fix': '더 자세하고 유용한 콘텐츠를 추가하세요',
                'auto_fix_available': False,
                'impact': 'high',
            })

        return issues

    def _analyze_performance(self, pagespeed_data: Dict) -> List[Dict]:
        """Analyze PageSpeed Insights data"""
        issues = []

        # LCP (Largest Contentful Paint) check
        lcp = pagespeed_data.get('lcp')
        if lcp and lcp > 2500:
            issues.append({
                'type': 'slow_lcp',
                'severity': self.SEVERITY_WARNING if lcp < 4000 else self.SEVERITY_CRITICAL,
                'category': 'performance',
                'title': 'LCP (최대 콘텐츠 렌더링 시간) 느림',
                'message': f'현재 {lcp}ms입니다. 2500ms 이하가 권장됩니다.',
                'current_value': lcp,
                'threshold': 2500,
                'fix': '이미지 최적화, 서버 응답 시간 개선, 렌더링 차단 리소스 제거',
                'auto_fix_available': False,
                'impact': 'critical',
            })

        # CLS (Cumulative Layout Shift) check
        cls = pagespeed_data.get('cls')
        if cls and cls > 0.1:
            issues.append({
                'type': 'high_cls',
                'severity': self.SEVERITY_WARNING if cls < 0.25 else self.SEVERITY_CRITICAL,
                'category': 'performance',
                'title': 'CLS (누적 레이아웃 이동) 높음',
                'message': f'현재 {cls}입니다. 0.1 이하가 권장됩니다.',
                'current_value': cls,
                'threshold': 0.1,
                'fix': '이미지/동영상에 크기 지정, 동적 콘텐츠 위치 고정',
                'auto_fix_available': False,
                'impact': 'high',
            })

        return issues

    # ========== Helper Methods ==========

    def _calculate_health_score(self, issues: List[Dict]) -> int:
        """Calculate health score (0-100)"""
        if not issues:
            return 100

        # Weight-based score calculation
        penalty = 0
        for issue in issues:
            if issue['severity'] == self.SEVERITY_CRITICAL:
                penalty += 15
            elif issue['severity'] == self.SEVERITY_WARNING:
                penalty += 7
            elif issue['severity'] == self.SEVERITY_INFO:
                penalty += 3

        score = max(0, 100 - penalty)
        return score

    def _generate_action_plan(self, issues: List[Dict]) -> Dict:
        """Generate action plan by priority"""
        critical = [i for i in issues if i['severity'] == self.SEVERITY_CRITICAL]
        warnings = [i for i in issues if i['severity'] == self.SEVERITY_WARNING]
        info = [i for i in issues if i['severity'] == self.SEVERITY_INFO]

        return {
            'immediate': critical,
            'this_week': warnings,
            'nice_to_have': info,
        }

    def _extract_auto_fixable(self, issues: List[Dict]) -> Dict:
        """Extract auto-fixable items"""
        auto_fixable = [i for i in issues if i.get('auto_fix_available')]

        return {
            'count': len(auto_fixable),
            'issues': auto_fixable,
            'methods': [i.get('auto_fix_method') for i in auto_fixable],
        }

    def _calculate_potential_gain(self, issues: List[Dict]) -> int:
        """Calculate expected score improvement"""
        gain = 0
        for issue in issues:
            if issue.get('auto_fix_available'):
                if issue['severity'] == self.SEVERITY_CRITICAL:
                    gain += 15
                elif issue['severity'] == self.SEVERITY_WARNING:
                    gain += 7
                elif issue['severity'] == self.SEVERITY_INFO:
                    gain += 3

        return min(gain, 35)

    def _estimate_fix_time(self, issues: List[Dict]) -> Dict:
        """Estimate fix time"""
        total_minutes = 0
        for issue in issues:
            if issue['severity'] == self.SEVERITY_CRITICAL:
                total_minutes += 20
            elif issue['severity'] == self.SEVERITY_WARNING:
                total_minutes += 10
            else:
                total_minutes += 5

        hours = total_minutes // 60
        minutes = total_minutes % 60

        if hours > 0:
            formatted = f"약 {hours}시간 {minutes}분"
        else:
            formatted = f"약 {minutes}분"

        return {
            'formatted': formatted,
            'minutes': total_minutes
        }

    def _generate_meta_description_suggestion(self, soup: BeautifulSoup, url: str) -> str:
        """Generate AI-based meta description (simple version)"""
        # Combine title and first sentence to generate meta description
        title = soup.find('title')
        title_text = title.text.strip() if title else ""

        # Extract first sentence from body
        paragraphs = soup.find_all('p')
        first_sentence = ""
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 50:
                first_sentence = text[:120]
                break

        if title_text and first_sentence:
            return f"{title_text}. {first_sentence}..."
        elif title_text:
            return f"{title_text}에 대한 완벽한 가이드. 초보자도 쉽게 따라할 수 있습니다."
        else:
            return "이 페이지에 대한 자세한 정보와 가이드를 확인하세요."
