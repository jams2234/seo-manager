"""
Sitemap AI Analyzer Service
AI-powered analysis and suggestions for sitemap optimization.
"""
import logging
import hashlib
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from django.utils import timezone
from django.db import transaction

from .base import ManagerService
from .claude_client import ClaudeAPIClient, ClaudeAnalyzer

logger = logging.getLogger(__name__)


class SitemapAIAnalyzerService(ManagerService):
    """
    Service for AI-powered sitemap and SEO analysis.
    Uses Claude to provide intelligent suggestions and issue detection.
    """

    def __init__(self):
        super().__init__()
        self.claude = ClaudeAnalyzer()
        self.client = ClaudeAPIClient()

    # Abstract method implementations (required by ManagerService)
    def generate(self, **kwargs) -> Dict:
        """Generate AI report"""
        domain = kwargs.get('domain')
        if domain:
            return self.generate_full_report(domain)
        return {'error': True, 'message': 'Domain required'}

    def validate(self, target, **kwargs) -> Dict:
        """Validate - not applicable for AI service"""
        return {'valid': True}

    def deploy(self, target, **kwargs) -> Dict:
        """Deploy - not applicable for AI service"""
        return {'error': False, 'message': 'AI service does not deploy'}

    def analyze_domain_sitemap(self, domain) -> Dict:
        """
        Perform full AI analysis on a domain's sitemap.

        Args:
            domain: Domain model instance

        Returns:
            Analysis result with issues and suggestions
        """
        from ..models import SitemapEntry, AIAnalysisCache

        try:
            self.log_info(f"Starting AI sitemap analysis for {domain.domain_name}")

            # Get all entries
            entries = list(SitemapEntry.objects.filter(domain=domain).values(
                'id', 'loc', 'lastmod', 'changefreq', 'priority',
                'status', 'is_valid', 'http_status_code', 'redirect_url'
            ))

            if not entries:
                return {
                    'error': True,
                    'message': 'No sitemap entries found for this domain'
                }

            # Convert dates to strings
            for entry in entries:
                if entry.get('lastmod'):
                    entry['lastmod'] = entry['lastmod'].isoformat()

            # Check cache
            context_hash = self._generate_context_hash(entries)
            cached = self._get_cached_analysis(domain, 'sitemap', context_hash)
            if cached:
                self.log_info("Returning cached AI analysis")
                return {
                    'error': False,
                    'cached': True,
                    **cached.analysis_result
                }

            # Perform analysis
            domain_info = {
                'domain_name': domain.domain_name,
                'total_pages': domain.total_pages,
            }

            result = self.claude.analyze_sitemap(entries, domain_info)

            if not result.get('success'):
                return {
                    'error': True,
                    'message': result.get('error', 'AI analysis failed')
                }

            # Extract parsed result
            analysis = result.get('parsed', {})

            # Cache the result
            self._cache_analysis(
                domain=domain,
                analysis_type='sitemap',
                context_hash=context_hash,
                result=analysis,
                usage=result.get('usage', {})
            )

            return {
                'error': False,
                'cached': False,
                'analysis': analysis,
                'entries_analyzed': len(entries),
            }

        except Exception as e:
            self.log_error(f"AI sitemap analysis failed: {e}", exc_info=True)
            return {
                'error': True,
                'message': str(e)
            }

    def get_entry_suggestions(
        self,
        entry_id: int,
        include_metrics: bool = True
    ) -> Dict:
        """
        Get AI suggestions for a specific sitemap entry.

        Args:
            entry_id: SitemapEntry ID
            include_metrics: Whether to include page metrics in analysis

        Returns:
            Suggestions for the entry
        """
        from ..models import SitemapEntry, Page, SEOMetrics

        try:
            entry = SitemapEntry.objects.select_related('domain', 'page').get(id=entry_id)

            entry_data = {
                'loc': entry.loc,
                'lastmod': entry.lastmod.isoformat() if entry.lastmod else None,
                'changefreq': entry.changefreq,
                'priority': float(entry.priority) if entry.priority else None,
            }

            # Get page metrics if available and requested
            page_metrics = None
            if include_metrics and entry.page:
                latest_metrics = entry.page.seo_metrics.first()
                if latest_metrics:
                    page_metrics = {
                        'seo_score': latest_metrics.seo_score,
                        'clicks': latest_metrics.clicks,
                        'impressions': latest_metrics.impressions,
                        'avg_position': latest_metrics.avg_position,
                        'is_indexed': latest_metrics.is_indexed,
                    }

            result = self.claude.suggest_entry_improvements(entry_data, page_metrics)

            if not result.get('success'):
                return {
                    'error': True,
                    'message': result.get('error', 'Failed to get suggestions')
                }

            return {
                'error': False,
                'entry_id': entry_id,
                'suggestions': result.get('parsed', {}),
            }

        except SitemapEntry.DoesNotExist:
            return {'error': True, 'message': 'Entry not found'}
        except Exception as e:
            self.log_error(f"Failed to get entry suggestions: {e}", exc_info=True)
            return {'error': True, 'message': str(e)}

    def analyze_seo_issues(self, domain) -> Dict:
        """
        Analyze SEO issues for a domain and get prioritized action plan.

        Args:
            domain: Domain model instance

        Returns:
            Analysis with prioritized actions
        """
        from ..models import SEOIssue, AIAnalysisCache

        try:
            self.log_info(f"Starting AI SEO issues analysis for {domain.domain_name}")

            # Get open issues
            issues = list(SEOIssue.objects.filter(
                page__domain=domain,
                status='open'
            ).select_related('page').values(
                'id', 'issue_type', 'severity', 'title', 'message',
                'fix_suggestion', 'auto_fix_available', 'page__url'
            ))

            if not issues:
                return {
                    'error': False,
                    'message': 'No open SEO issues found',
                    'analysis': {
                        'priority_actions': [],
                        'quick_wins': [],
                        'summary': 'No issues to analyze'
                    }
                }

            # Format for AI
            formatted_issues = [{
                'id': i['id'],
                'type': i['issue_type'],
                'severity': i['severity'],
                'title': i['title'],
                'message': i['message'],
                'page_url': i['page__url'],
                'auto_fixable': i['auto_fix_available'],
            } for i in issues]

            # Check cache
            context_hash = self._generate_context_hash(formatted_issues)
            cached = self._get_cached_analysis(domain, 'seo_issues', context_hash)
            if cached:
                self.log_info("Returning cached SEO issues analysis")
                return {
                    'error': False,
                    'cached': True,
                    **cached.analysis_result
                }

            # Perform analysis
            domain_info = {
                'domain_name': domain.domain_name,
                'total_pages': domain.total_pages,
            }

            result = self.claude.analyze_seo_issues(formatted_issues, domain_info)

            if not result.get('success'):
                return {
                    'error': True,
                    'message': result.get('error', 'AI analysis failed')
                }

            analysis = result.get('parsed', {})

            # Cache the result
            self._cache_analysis(
                domain=domain,
                analysis_type='seo_issues',
                context_hash=context_hash,
                result=analysis,
                usage=result.get('usage', {})
            )

            return {
                'error': False,
                'cached': False,
                'analysis': analysis,
                'issues_analyzed': len(issues),
            }

        except Exception as e:
            self.log_error(f"AI SEO issues analysis failed: {e}", exc_info=True)
            return {'error': True, 'message': str(e)}

    def apply_ai_suggestions(
        self,
        domain,
        session_id: int,
        suggestions: List[Dict],
        user=None
    ) -> Dict:
        """
        Apply AI suggestions to sitemap entries.

        Args:
            domain: Domain model instance
            session_id: Edit session ID
            suggestions: List of suggestions to apply
            user: User applying suggestions

        Returns:
            Result with applied changes count
        """
        from ..models import SitemapEntry, SitemapEditSession
        from .sitemap_editor import SitemapEditorService

        try:
            editor = SitemapEditorService()
            applied_count = 0
            errors = []

            with transaction.atomic():
                for suggestion in suggestions:
                    entry_id = suggestion.get('entry_id')
                    updates = {}

                    if suggestion.get('priority') is not None:
                        updates['priority'] = suggestion['priority']
                    if suggestion.get('changefreq'):
                        updates['changefreq'] = suggestion['changefreq']

                    if updates:
                        result = editor.update_entry(
                            entry_id=entry_id,
                            session_id=session_id,
                            updates=updates,
                            user=user,
                            source='ai_suggestion'
                        )

                        if result.get('error'):
                            errors.append({
                                'entry_id': entry_id,
                                'error': result.get('message')
                            })
                        else:
                            applied_count += 1

                            # Mark entry as AI suggested
                            try:
                                entry = SitemapEntry.objects.get(id=entry_id)
                                entry.ai_suggested = True
                                entry.ai_suggestion_reason = suggestion.get('reason', '')
                                entry.save(update_fields=['ai_suggested', 'ai_suggestion_reason'])
                            except SitemapEntry.DoesNotExist:
                                pass

            return {
                'error': False,
                'applied_count': applied_count,
                'errors': errors,
            }

        except Exception as e:
            self.log_error(f"Failed to apply AI suggestions: {e}", exc_info=True)
            return {'error': True, 'message': str(e)}

    def generate_full_report(self, domain) -> Dict:
        """
        Generate a comprehensive AI analysis report for a domain.

        Args:
            domain: Domain model instance

        Returns:
            Full analysis report
        """
        try:
            self.log_info(f"Generating full AI report for {domain.domain_name}")

            # Collect all data
            sitemap_analysis = self.analyze_domain_sitemap(domain)
            seo_analysis = self.analyze_seo_issues(domain)

            # Get domain stats
            from ..models import SitemapEntry, Page, SEOIssue

            stats = {
                'total_sitemap_entries': SitemapEntry.objects.filter(domain=domain).count(),
                'invalid_entries': SitemapEntry.objects.filter(domain=domain, is_valid=False).count(),
                'total_pages': Page.objects.filter(domain=domain).count(),
                'pages_with_issues': Page.objects.filter(
                    domain=domain,
                    seo_issues__status='open'
                ).distinct().count(),
                'critical_issues': SEOIssue.objects.filter(
                    page__domain=domain,
                    status='open',
                    severity='critical'
                ).count(),
                'warning_issues': SEOIssue.objects.filter(
                    page__domain=domain,
                    status='open',
                    severity='warning'
                ).count(),
            }

            # Build summary prompt
            system = """당신은 SEO 전문가입니다. 분석 데이터를 기반으로 종합적인 요약과 실행 계획을 제공하세요. 모든 응답은 한국어로 작성하세요."""

            prompt = f"""{domain.domain_name}에 대한 종합 SEO 건강 보고서를 작성해주세요.

도메인 통계:
- 전체 사이트맵 항목: {stats['total_sitemap_entries']}
- 유효하지 않은 항목: {stats['invalid_entries']}
- 전체 페이지: {stats['total_pages']}
- 이슈가 있는 페이지: {stats['pages_with_issues']}
- 심각한 이슈: {stats['critical_issues']}
- 경고 이슈: {stats['warning_issues']}

사이트맵 분석 요약:
{sitemap_analysis.get('analysis', {}).get('summary', '분석 불가')}

SEO 이슈 분석 요약:
{seo_analysis.get('analysis', {}).get('summary', '분석 불가')}

다음 JSON 형식으로 종합 보고서를 제공하세요 (한국어로):
{{
    "overall_health_score": 0-100,
    "health_grade": "A|B|C|D|F",
    "executive_summary": "2-3문장 요약",
    "top_priorities": [
        {{
            "priority": 1,
            "category": "sitemap|technical|content",
            "action": "수행할 작업",
            "impact": "예상 개선 효과",
            "effort": "low|medium|high"
        }}
    ],
    "sitemap_health": {{
        "score": 0-100,
        "key_findings": ["발견사항1", "발견사항2"]
    }},
    "technical_seo_health": {{
        "score": 0-100,
        "key_findings": ["발견사항1", "발견사항2"]
    }},
    "next_steps": ["다음단계1", "다음단계2", "다음단계3"]
}}"""

            result = self.client.analyze_json(prompt, system=system)

            if not result.get('success'):
                return {
                    'error': True,
                    'message': result.get('error', 'Failed to generate report')
                }

            report = result.get('parsed', {})

            return {
                'error': False,
                'domain': domain.domain_name,
                'generated_at': timezone.now().isoformat(),
                'stats': stats,
                'report': report,
                'sitemap_analysis': sitemap_analysis.get('analysis'),
                'seo_analysis': seo_analysis.get('analysis'),
            }

        except Exception as e:
            self.log_error(f"Failed to generate full report: {e}", exc_info=True)
            return {'error': True, 'message': str(e)}

    def _generate_context_hash(self, data: List[Dict]) -> str:
        """Generate hash for caching based on data content"""
        content = str(sorted([str(sorted(d.items())) for d in data[:20]]))
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_cached_analysis(
        self,
        domain,
        analysis_type: str,
        context_hash: str
    ):
        """Get cached analysis if available and not expired"""
        from ..models import AIAnalysisCache

        try:
            cache = AIAnalysisCache.objects.filter(
                domain=domain,
                analysis_type=analysis_type,
                context_hash=context_hash,
                expires_at__gt=timezone.now()
            ).first()
            return cache
        except Exception:
            return None

    def _cache_analysis(
        self,
        domain,
        analysis_type: str,
        context_hash: str,
        result: Dict,
        usage: Dict = None
    ):
        """Cache analysis result"""
        from ..models import AIAnalysisCache
        from django.conf import settings

        try:
            cache_ttl = getattr(settings, 'CLAUDE_CACHE_TTL', 86400)
            expires_at = timezone.now() + timedelta(seconds=cache_ttl)

            AIAnalysisCache.objects.update_or_create(
                domain=domain,
                analysis_type=analysis_type,
                context_hash=context_hash,
                defaults={
                    'analysis_result': result,
                    'suggestions': result.get('suggestions', []),
                    'issues': result.get('issues', []),
                    'tokens_used': (usage.get('input_tokens', 0) + usage.get('output_tokens', 0)) if usage else 0,
                    'expires_at': expires_at,
                }
            )
        except Exception as e:
            self.log_warning(f"Failed to cache analysis: {e}")
