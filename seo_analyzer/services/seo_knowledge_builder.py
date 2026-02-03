"""
SEO Knowledge Builder Service
Transforms raw database data into AI-friendly structured context.

This provides semantic understanding of website structure for better AI analysis.
"""
import logging
from typing import Dict, List, Optional
from collections import defaultdict
from urllib.parse import urlparse
from django.db.models import Avg, Count, Q, OuterRef, Subquery
from django.db.models.fields import FloatField

logger = logging.getLogger(__name__)


class SEOKnowledgeBuilder:
    """
    Builds structured SEO knowledge context for AI analysis.

    Transforms flat database records into semantic relationships:
    - URL hierarchy and patterns
    - Content type inference
    - Link structure analysis
    - Keyword clustering
    - Issue patterns
    """

    # URL pattern → Content type mapping (SEO knowledge)
    CONTENT_TYPE_PATTERNS = {
        'blog': {'type': 'blog', 'priority_range': (0.6, 0.8), 'changefreq': 'weekly'},
        'news': {'type': 'news', 'priority_range': (0.7, 0.9), 'changefreq': 'daily'},
        'product': {'type': 'product', 'priority_range': (0.7, 0.9), 'changefreq': 'weekly'},
        'category': {'type': 'category', 'priority_range': (0.6, 0.8), 'changefreq': 'weekly'},
        'about': {'type': 'static', 'priority_range': (0.4, 0.6), 'changefreq': 'monthly'},
        'contact': {'type': 'static', 'priority_range': (0.3, 0.5), 'changefreq': 'yearly'},
        'faq': {'type': 'support', 'priority_range': (0.5, 0.7), 'changefreq': 'monthly'},
        'help': {'type': 'support', 'priority_range': (0.5, 0.7), 'changefreq': 'monthly'},
        'docs': {'type': 'documentation', 'priority_range': (0.6, 0.8), 'changefreq': 'weekly'},
        'api': {'type': 'documentation', 'priority_range': (0.5, 0.7), 'changefreq': 'weekly'},
    }

    # SEO issue severity weights for scoring
    ISSUE_WEIGHTS = {
        'critical': 25,
        'high': 15,
        'medium': 8,
        'low': 3,
        'info': 1,
    }

    def __init__(self, domain):
        self.domain = domain
        self._cache = {}

    def build_full_context(self) -> Dict:
        """
        Build complete SEO knowledge context for AI.

        Returns structured data optimized for Claude analysis.
        """
        return {
            'domain_overview': self._build_domain_overview(),
            'url_structure': self._build_url_structure(),
            'content_analysis': self._build_content_analysis(),
            'seo_health': self._build_seo_health(),
            'keyword_insights': self._build_keyword_insights(),
            'improvement_opportunities': self._build_improvement_opportunities(),
        }

    def build_node_context(self, page) -> Dict:
        """
        Build context for a specific page/node in the tree.
        """
        from ..models import SEOMetrics, SEOIssue, SitemapEntry

        # Get latest metrics
        metrics = SEOMetrics.objects.filter(page=page).order_by('-snapshot_date').first()

        # Get issues
        issues = list(SEOIssue.objects.filter(
            page=page,
            status='open'
        ).values('issue_type', 'severity', 'title', 'fix_suggestion'))

        # Get sitemap entry
        sitemap_entry = SitemapEntry.objects.filter(page=page).first()

        # Infer content type
        content_type = self._infer_content_type(page.url)

        # Get sibling pages (same depth)
        siblings = page.domain.pages.filter(
            depth_level=page.depth_level
        ).exclude(id=page.id).values('url', 'title')[:5]

        # Get child pages
        children = page.domain.pages.filter(
            parent_page=page
        ).values('url', 'title')[:10]

        return {
            'page': {
                'url': page.url,
                'title': page.title,
                'depth': page.depth_level,
                'content_type': content_type,
            },
            'metrics': {
                'seo_score': metrics.seo_score if metrics else None,
                'performance': metrics.performance_score if metrics else None,
                'accessibility': metrics.accessibility_score if metrics else None,
                'mobile_friendly': metrics.mobile_friendly if metrics else None,
            } if metrics else None,
            'sitemap': {
                'priority': float(sitemap_entry.priority) if sitemap_entry and sitemap_entry.priority else None,
                'changefreq': sitemap_entry.changefreq if sitemap_entry else None,
                'is_appropriate': self._check_sitemap_appropriateness(page, sitemap_entry),
            } if sitemap_entry else None,
            'issues': issues,
            'structure': {
                'siblings_count': len(siblings),
                'children_count': len(children),
                'sample_siblings': list(siblings),
                'sample_children': list(children),
            },
            'recommendations': self._generate_node_recommendations(page, metrics, sitemap_entry, issues),
        }

    def _build_domain_overview(self) -> Dict:
        """Build domain-level overview."""
        from ..models import Page, SitemapEntry, SEOIssue

        pages = Page.objects.filter(domain=self.domain)
        entries = SitemapEntry.objects.filter(domain=self.domain)

        # Issue summary
        issues = SEOIssue.objects.filter(
            page__domain=self.domain,
            status='open'
        ).values('severity').annotate(count=Count('id'))

        issue_summary = {item['severity']: item['count'] for item in issues}

        return {
            'domain_name': self.domain.domain_name,
            'total_pages': pages.count(),
            'indexed_in_sitemap': entries.count(),
            'avg_seo_score': self.domain.avg_seo_score,
            'avg_performance': self.domain.avg_performance_score,
            'issue_summary': issue_summary,
            'health_score': self._calculate_health_score(issue_summary),
            'google_connected': self.domain.search_console_connected,
        }

    def _build_url_structure(self) -> Dict:
        """Analyze URL structure and hierarchy."""
        from ..models import Page

        pages = Page.objects.filter(domain=self.domain).values('url', 'depth_level', 'title')

        # Group by depth
        depth_distribution = defaultdict(list)
        path_patterns = defaultdict(int)

        for page in pages:
            depth_distribution[page['depth_level']].append(page['url'])

            # Extract path pattern
            parsed = urlparse(page['url'])
            path_parts = [p for p in parsed.path.split('/') if p]
            if path_parts:
                path_patterns[path_parts[0]] += 1

        # Find orphan pages (no parent, depth > 0)
        orphan_count = Page.objects.filter(
            domain=self.domain,
            depth_level__gt=0,
            parent_page__isnull=True
        ).count()

        return {
            'depth_distribution': {
                depth: len(urls) for depth, urls in depth_distribution.items()
            },
            'max_depth': max(depth_distribution.keys()) if depth_distribution else 0,
            'path_patterns': dict(path_patterns),
            'orphan_pages': orphan_count,
            'structure_quality': 'good' if orphan_count == 0 else 'needs_improvement',
        }

    def _build_content_analysis(self) -> Dict:
        """Analyze content types and their SEO settings."""
        from ..models import SitemapEntry

        entries = SitemapEntry.objects.filter(domain=self.domain)

        content_types = defaultdict(lambda: {
            'count': 0,
            'avg_priority': 0,
            'priorities': [],
            'changefreqs': defaultdict(int),
            'issues': [],
        })

        for entry in entries:
            content_type = self._infer_content_type(entry.loc)
            ct_data = content_types[content_type]
            ct_data['count'] += 1
            if entry.priority:
                ct_data['priorities'].append(float(entry.priority))
            if entry.changefreq:
                ct_data['changefreqs'][entry.changefreq] += 1

            # Check for issues
            expected = self.CONTENT_TYPE_PATTERNS.get(content_type, {})
            if expected and entry.priority:
                min_p, max_p = expected.get('priority_range', (0, 1))
                if not (min_p <= float(entry.priority) <= max_p):
                    ct_data['issues'].append({
                        'url': entry.loc,
                        'issue': f'priority {entry.priority} outside expected {min_p}-{max_p}'
                    })

        # Calculate averages
        result = {}
        for ct, data in content_types.items():
            result[ct] = {
                'count': data['count'],
                'avg_priority': sum(data['priorities']) / len(data['priorities']) if data['priorities'] else None,
                'changefreq_distribution': dict(data['changefreqs']),
                'issues_count': len(data['issues']),
                'sample_issues': data['issues'][:3],
            }

        return result

    def _build_seo_health(self) -> Dict:
        """Build SEO health analysis."""
        from ..models import SEOIssue, Page, SEOMetrics

        # Issue patterns
        issue_patterns = SEOIssue.objects.filter(
            page__domain=self.domain,
            status='open'
        ).values('issue_type', 'severity').annotate(
            count=Count('id')
        ).order_by('-count')

        # Pages with most issues
        problem_pages = Page.objects.filter(
            domain=self.domain
        ).annotate(
            issue_count=Count('seo_issues', filter=Q(seo_issues__status='open'))
        ).filter(issue_count__gt=0).order_by('-issue_count').values(
            'url', 'title', 'issue_count'
        )[:10]

        # Score distribution - using subquery for DB compatibility
        from ..models import SEOMetrics, Page
        from django.db.models import OuterRef, Subquery

        # Get latest score per page using subquery
        latest_score_subquery = SEOMetrics.objects.filter(
            page_id=OuterRef('id')
        ).order_by('-snapshot_date').values('seo_score')[:1]

        page_scores = Page.objects.filter(
            domain=self.domain
        ).annotate(
            latest_seo_score=Subquery(latest_score_subquery, output_field=FloatField())
        ).values('latest_seo_score')

        score_ranges = {'excellent': 0, 'good': 0, 'average': 0, 'poor': 0}
        for p in page_scores:
            score = p['latest_seo_score']
            if score is None:
                continue
            if score >= 90:
                score_ranges['excellent'] += 1
            elif score >= 70:
                score_ranges['good'] += 1
            elif score >= 50:
                score_ranges['average'] += 1
            else:
                score_ranges['poor'] += 1

        return {
            'issue_patterns': list(issue_patterns),
            'problem_pages': list(problem_pages),
            'score_distribution': score_ranges,
            'auto_fixable_count': SEOIssue.objects.filter(
                page__domain=self.domain,
                status='open',
                auto_fix_available=True
            ).count(),
        }

    def _build_keyword_insights(self) -> Dict:
        """Build keyword and search performance insights."""
        from ..models import SEOMetrics

        # Get top queries from all pages
        all_queries = []
        metrics = SEOMetrics.objects.filter(
            page__domain=self.domain,
            top_queries__isnull=False
        ).order_by('-snapshot_date').values('page__url', 'top_queries', 'impressions', 'clicks')[:50]

        keyword_performance = defaultdict(lambda: {
            'impressions': 0,
            'clicks': 0,
            'pages': set(),
        })

        for m in metrics:
            if m['top_queries']:
                for query in m['top_queries'][:5]:  # Top 5 per page
                    if isinstance(query, dict):
                        keyword = query.get('query', query.get('keyword', ''))
                        keyword_performance[keyword]['impressions'] += query.get('impressions', 0)
                        keyword_performance[keyword]['clicks'] += query.get('clicks', 0)
                        keyword_performance[keyword]['pages'].add(m['page__url'])

        # Convert to list and sort
        keyword_list = [
            {
                'keyword': kw,
                'impressions': data['impressions'],
                'clicks': data['clicks'],
                'ctr': data['clicks'] / data['impressions'] if data['impressions'] > 0 else 0,
                'page_count': len(data['pages']),
            }
            for kw, data in keyword_performance.items()
        ]
        keyword_list.sort(key=lambda x: x['impressions'], reverse=True)

        return {
            'top_keywords': keyword_list[:20],
            'total_keywords': len(keyword_list),
            'keyword_cannibalization': self._detect_cannibalization(keyword_performance),
        }

    def _build_improvement_opportunities(self) -> Dict:
        """Identify improvement opportunities with priorities."""
        from ..models import SitemapEntry, SEOIssue, Page

        opportunities = []

        # 1. Missing sitemap entries
        pages_without_sitemap = Page.objects.filter(
            domain=self.domain,
            status='active'
        ).exclude(
            id__in=SitemapEntry.objects.filter(domain=self.domain).values('page_id')
        ).count()

        if pages_without_sitemap > 0:
            opportunities.append({
                'type': 'sitemap_coverage',
                'priority': 'high',
                'impact': 'indexing',
                'description': f'{pages_without_sitemap}개 페이지가 사이트맵에 없음',
                'action': 'sitemap에 누락된 페이지 추가 필요',
            })

        # 2. Auto-fixable issues
        auto_fixable = SEOIssue.objects.filter(
            page__domain=self.domain,
            status='open',
            auto_fix_available=True
        ).count()

        if auto_fixable > 0:
            opportunities.append({
                'type': 'auto_fix',
                'priority': 'high',
                'impact': 'quick_win',
                'description': f'{auto_fixable}개 이슈 자동 수정 가능',
                'action': 'Auto-fix 실행으로 즉시 개선 가능',
            })

        # 3. Priority optimization
        wrong_priority = SitemapEntry.objects.filter(
            domain=self.domain
        ).extra(
            where=["priority < 0.3 OR priority > 0.9"]
        ).count()

        if wrong_priority > 0:
            opportunities.append({
                'type': 'priority_optimization',
                'priority': 'medium',
                'impact': 'crawl_budget',
                'description': f'{wrong_priority}개 URL의 priority 값 최적화 필요',
                'action': '콘텐츠 중요도에 맞게 priority 조정',
            })

        # 4. Critical issues
        critical_count = SEOIssue.objects.filter(
            page__domain=self.domain,
            status='open',
            severity='critical'
        ).count()

        if critical_count > 0:
            opportunities.append({
                'type': 'critical_issues',
                'priority': 'urgent',
                'impact': 'ranking',
                'description': f'{critical_count}개 Critical 이슈 해결 필요',
                'action': 'SEO 점수 및 순위에 직접 영향',
            })

        return {
            'opportunities': sorted(opportunities, key=lambda x: {
                'urgent': 0, 'high': 1, 'medium': 2, 'low': 3
            }.get(x['priority'], 4)),
            'estimated_score_gain': self._estimate_score_gain(opportunities),
        }

    def _infer_content_type(self, url: str) -> str:
        """Infer content type from URL pattern."""
        path = urlparse(url).path.lower()

        for pattern, config in self.CONTENT_TYPE_PATTERNS.items():
            if pattern in path:
                return config['type']

        # Check depth
        path_parts = [p for p in path.split('/') if p]
        if len(path_parts) == 0:
            return 'homepage'
        elif len(path_parts) == 1:
            return 'main_section'
        else:
            return 'content_page'

    def _check_sitemap_appropriateness(self, page, entry) -> Dict:
        """Check if sitemap settings are appropriate for the page."""
        if not entry:
            return {'status': 'missing', 'issues': ['사이트맵에 등록되지 않음']}

        issues = []
        content_type = self._infer_content_type(page.url)
        expected = self.CONTENT_TYPE_PATTERNS.get(content_type, {})

        # Check priority
        if entry.priority and expected.get('priority_range'):
            min_p, max_p = expected['priority_range']
            if not (min_p <= float(entry.priority) <= max_p):
                issues.append(f"priority {entry.priority}는 {content_type}에 적합하지 않음 (권장: {min_p}-{max_p})")

        # Check changefreq
        if expected.get('changefreq') and entry.changefreq != expected['changefreq']:
            issues.append(f"changefreq '{entry.changefreq}'는 {content_type}에 적합하지 않음 (권장: {expected['changefreq']})")

        return {
            'status': 'appropriate' if not issues else 'needs_adjustment',
            'issues': issues,
            'content_type': content_type,
        }

    def _generate_node_recommendations(self, page, metrics, entry, issues) -> List[Dict]:
        """Generate specific recommendations for a page."""
        recommendations = []

        # Check sitemap
        if not entry:
            recommendations.append({
                'type': 'sitemap',
                'priority': 'high',
                'action': '사이트맵에 페이지 추가',
                'reason': 'Google 크롤링 및 인덱싱 개선',
            })

        # Check metrics
        if metrics and metrics.seo_score and metrics.seo_score < 70:
            recommendations.append({
                'type': 'seo_score',
                'priority': 'high',
                'action': f'SEO 점수 개선 필요 (현재: {metrics.seo_score})',
                'reason': '70점 이상 권장',
            })

        if metrics and metrics.mobile_friendly is False:
            recommendations.append({
                'type': 'mobile',
                'priority': 'urgent',
                'action': '모바일 최적화 필요',
                'reason': 'Mobile-first indexing 대응',
            })

        # Check issues
        critical_issues = [i for i in issues if i['severity'] == 'critical']
        if critical_issues:
            recommendations.append({
                'type': 'critical_fix',
                'priority': 'urgent',
                'action': f'{len(critical_issues)}개 Critical 이슈 수정',
                'issues': [i['title'] for i in critical_issues[:3]],
            })

        return recommendations

    def _calculate_health_score(self, issue_summary: Dict) -> float:
        """Calculate overall health score from issues."""
        total_penalty = sum(
            self.ISSUE_WEIGHTS.get(severity, 1) * count
            for severity, count in issue_summary.items()
        )
        # Base score of 100, subtract penalties (min 0)
        return max(0, 100 - total_penalty)

    def _detect_cannibalization(self, keyword_performance: Dict) -> List[Dict]:
        """Detect keyword cannibalization (multiple pages targeting same keyword)."""
        cannibalization = []

        for keyword, data in keyword_performance.items():
            if len(data['pages']) > 1:
                cannibalization.append({
                    'keyword': keyword,
                    'competing_pages': list(data['pages'])[:5],
                    'recommendation': '페이지 통합 또는 canonical 태그 검토',
                })

        return cannibalization[:10]  # Top 10

    def _estimate_score_gain(self, opportunities: List[Dict]) -> float:
        """Estimate potential score gain from addressing opportunities."""
        gain = 0
        for opp in opportunities:
            if opp['priority'] == 'urgent':
                gain += 15
            elif opp['priority'] == 'high':
                gain += 10
            elif opp['priority'] == 'medium':
                gain += 5
        return min(gain, 30)  # Cap at 30 points

    def to_ai_context(self) -> str:
        """
        Convert full context to AI-friendly text format.
        Optimized for Claude prompts.
        """
        ctx = self.build_full_context()

        parts = [
            f"=== 도메인 분석: {ctx['domain_overview']['domain_name']} ===",
            f"",
            f"## 개요",
            f"- 총 페이지: {ctx['domain_overview']['total_pages']}",
            f"- 사이트맵 등록: {ctx['domain_overview']['indexed_in_sitemap']}",
            f"- 평균 SEO 점수: {ctx['domain_overview']['avg_seo_score'] or 'N/A'}",
            f"- 건강 점수: {ctx['domain_overview']['health_score']:.1f}/100",
            f"- Google Search Console: {'연동됨' if ctx['domain_overview']['google_connected'] else '미연동'}",
            f"",
            f"## URL 구조",
            f"- 최대 깊이: {ctx['url_structure']['max_depth']}",
            f"- 깊이별 분포: {ctx['url_structure']['depth_distribution']}",
            f"- 고아 페이지: {ctx['url_structure']['orphan_pages']}",
            f"",
            f"## 콘텐츠 유형별 분석",
        ]

        for ct, data in ctx['content_analysis'].items():
            avg_p = f"{data['avg_priority']:.2f}" if data['avg_priority'] else 'N/A'
            parts.append(f"- {ct}: {data['count']}개, 평균 priority: {avg_p}")

        parts.extend([
            f"",
            f"## SEO 이슈 현황",
            f"- 점수 분포: {ctx['seo_health']['score_distribution']}",
            f"- 자동 수정 가능: {ctx['seo_health']['auto_fixable_count']}개",
            f"",
            f"## 개선 기회 (우선순위순)",
        ])

        for opp in ctx['improvement_opportunities']['opportunities']:
            parts.append(f"- [{opp['priority'].upper()}] {opp['description']}")

        parts.append(f"")
        parts.append(f"예상 점수 향상: +{ctx['improvement_opportunities']['estimated_score_gain']}점")

        return "\n".join(parts)
