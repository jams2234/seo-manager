"""
Page Analysis Service

Handles SEO analysis for pages including issue creation and report generation.
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
from django.db import transaction
from django.utils import timezone

from ..constants import IssueStatus, VerificationStatus, IssueSeverity

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Result of page SEO analysis"""
    report: any  # SEOAnalysisReport instance
    issues: List[any]  # List of SEOIssue instances
    seo_data: Dict
    content_data: Optional[Dict] = None


class PageAnalysisService:
    """
    Service for analyzing pages and creating SEO reports.

    Handles:
    - Running SEO analysis
    - Creating issues in database
    - Creating analysis reports
    - Optional content analysis
    """

    def __init__(self, logger_instance=None):
        """
        Initialize PageAnalysisService

        Args:
            logger_instance: Optional logger. Uses module logger if not provided.
        """
        self.logger = logger_instance or logger

    @transaction.atomic
    def analyze_page(
        self,
        page,
        include_content: bool = True,
        target_keywords: Optional[List[str]] = None,
        verify_mode: bool = False
    ) -> AnalysisResult:
        """
        Perform comprehensive SEO analysis on a page.

        Args:
            page: Page model instance to analyze
            include_content: Whether to include content analysis
            target_keywords: Keywords to check for in content analysis
            verify_mode: If True, verify deployed fixes against actual website

        Returns:
            AnalysisResult containing report, issues, and analysis data

        Raises:
            Exception: If analysis fails
        """
        from .seo_advisor import SEOAdvisor
        from .content_analyzer import ContentAnalyzer
        from ..models import SEOIssue, SEOAnalysisReport

        # 1. Run SEO analysis
        advisor = SEOAdvisor()
        seo_result = advisor.analyze(page.url)

        if seo_result.get('error'):
            raise Exception(seo_result.get('message', 'SEO analysis failed'))

        # 2. Optionally run content analysis
        content_result = None
        if include_content:
            content_result = self._run_content_analysis(
                page,
                target_keywords
            )

        # 3. Create issues or verify existing fixes
        if verify_mode:
            issues = self._verify_deployed_fixes(page, seo_result)
        else:
            issues = self._create_issues(page, seo_result)

        # 4. Create analysis report
        report = self._create_report(page, seo_result)

        # 5. Update page timestamp
        self._update_page_timestamp(page)

        return AnalysisResult(
            report=report,
            issues=issues,
            seo_data=seo_result,
            content_data=content_result
        )

    def _run_content_analysis(
        self,
        page,
        target_keywords: Optional[List[str]]
    ) -> Optional[Dict]:
        """
        Run content analysis on page.

        Args:
            page: Page instance
            target_keywords: Keywords to analyze

        Returns:
            Content analysis result dict or None if failed
        """
        try:
            from .content_analyzer import ContentAnalyzer

            analyzer = ContentAnalyzer()
            result = analyzer.analyze(
                page,
                target_keywords=target_keywords if target_keywords else None
            )

            if result and not result.get('error'):
                return result

            return None

        except Exception as e:
            self.logger.warning(f"Content analysis failed for {page.url}: {e}")
            return None

    def _get_previously_fixed_types(self, page) -> set:
        """
        Get set of issue types that were previously fixed for this page.

        Args:
            page: Page instance

        Returns:
            Set of issue type strings
        """
        from ..models import SEOIssue

        return set(
            SEOIssue.objects.filter(
                page=page,
                status__in=IssueStatus.RESOLVED_STATUSES
            ).values_list('issue_type', flat=True)
        )

    def _create_single_issue(self, page, issue_data: Dict):
        """
        Create a single SEOIssue from issue data dictionary.

        Args:
            page: Page instance
            issue_data: Dictionary containing issue information

        Returns:
            Created SEOIssue instance or None if creation failed
        """
        from ..models import SEOIssue

        try:
            return SEOIssue.objects.create(
                page=page,
                issue_type=issue_data.get('type'),
                severity=issue_data.get('severity'),
                title=issue_data.get('title'),
                message=issue_data.get('message'),
                fix_suggestion=issue_data.get('suggestion'),
                auto_fix_available=issue_data.get('auto_fix_available', False),
                auto_fix_method=issue_data.get('auto_fix_method'),
                current_value=issue_data.get('current'),
                suggested_value=issue_data.get('suggested'),
                extra_data=issue_data.get('extra_data', {})
            )
        except Exception as e:
            self.logger.error(f"Failed to create issue: {e}", exc_info=True)
            return None

    def _create_issues(self, page, seo_result: Dict) -> List:
        """
        Create SEOIssue instances from analysis results.
        Skips issues that were previously auto-fixed (user needs to apply to website).

        Args:
            page: Page instance
            seo_result: SEO analysis result dictionary

        Returns:
            List of created SEOIssue instances
        """
        from ..models import SEOIssue

        issues_created = []

        # Get previously fixed issue types (don't recreate if already fixed in DB)
        previously_fixed_types = self._get_previously_fixed_types(page)

        # Delete existing open issues for this page to avoid duplicates
        SEOIssue.objects.filter(page=page, status=IssueStatus.OPEN).delete()

        skipped_count = 0
        for issue_data in seo_result.get('issues', []):
            issue_type = issue_data.get('type')

            # Skip if already fixed in database (user needs to apply to actual website)
            if issue_type in previously_fixed_types:
                skipped_count += 1
                self.logger.info(
                    f"Skipping issue {issue_type} for page {page.id} - "
                    f"already fixed in database. User needs to apply to website."
                )
                continue

            issue = self._create_single_issue(page, issue_data)
            if issue:
                issues_created.append(issue)

        if skipped_count > 0:
            self.logger.info(
                f"Skipped {skipped_count} previously fixed issues for page {page.id}"
            )

        return issues_created

    def _verify_deployed_fixes(self, page, seo_result: Dict) -> List:
        """
        Verify deployed fixes against actual website analysis.
        Updates verification_status for deployed issues.

        Args:
            page: Page instance
            seo_result: SEO analysis result from actual website crawl

        Returns:
            List of updated SEOIssue instances
        """
        from ..models import SEOIssue

        # Get currently detected issue types from actual website
        current_issue_types = set(
            issue_data.get('type') for issue_data in seo_result.get('issues', [])
        )

        # Get deployed issues that need verification
        deployed_issues = SEOIssue.objects.filter(
            page=page,
            status__in=IssueStatus.RESOLVED_STATUSES,
            deployed_to_git=True,
            verification_status__in=VerificationStatus.UNVERIFIED
        )

        verified_count = 0
        needs_attention_count = 0
        updated_issues = []

        for issue in deployed_issues:
            if issue.issue_type in current_issue_types:
                # Issue still detected on actual website - needs attention
                issue.verification_status = VerificationStatus.NEEDS_ATTENTION
                needs_attention_count += 1
                self.logger.warning(
                    f"Issue {issue.issue_type} still detected on {page.url} after deployment"
                )
            else:
                # Issue no longer detected - verified!
                issue.verification_status = VerificationStatus.VERIFIED
                issue.verified_at = timezone.now()
                verified_count += 1
                self.logger.info(
                    f"Issue {issue.issue_type} verified as fixed on {page.url}"
                )

            issue.save(update_fields=['verification_status', 'verified_at'])
            updated_issues.append(issue)

        # Also update non-deployed fixed issues to 'not_deployed' status
        SEOIssue.objects.filter(
            page=page,
            status__in=IssueStatus.RESOLVED_STATUSES,
            deployed_to_git=False
        ).update(verification_status=VerificationStatus.NOT_DEPLOYED)

        # Create new issues for any NEW problems found (not previously tracked)
        previously_fixed_types = self._get_previously_fixed_types(page)

        # Delete existing open issues
        SEOIssue.objects.filter(page=page, status=IssueStatus.OPEN).delete()

        # Create new open issues (exclude already fixed types)
        for issue_data in seo_result.get('issues', []):
            issue_type = issue_data.get('type')
            if issue_type not in previously_fixed_types:
                issue = self._create_single_issue(page, issue_data)
                if issue:
                    updated_issues.append(issue)

        self.logger.info(
            f"Verification complete for page {page.id}: "
            f"{verified_count} verified, {needs_attention_count} needs attention"
        )

        return updated_issues

    def _create_report(self, page, seo_result: Dict):
        """
        Create SEOAnalysisReport from analysis results.

        Args:
            page: Page instance
            seo_result: SEO analysis result dictionary

        Returns:
            Created SEOAnalysisReport instance
        """
        from ..models import SEOAnalysisReport

        issues = seo_result.get('issues', [])

        # Count issues by severity
        critical_count = len([i for i in issues if i.get('severity') == IssueSeverity.CRITICAL])
        warning_count = len([i for i in issues if i.get('severity') == IssueSeverity.WARNING])
        info_count = len([i for i in issues if i.get('severity') == IssueSeverity.INFO])

        report = SEOAnalysisReport.objects.create(
            domain=page.domain,
            page=page,
            report_type='page',
            overall_health_score=seo_result.get('overall_health', 0),
            critical_issues_count=critical_count,
            warning_issues_count=warning_count,
            info_issues_count=info_count,
            auto_fixable_count=seo_result.get('auto_fix_count', 0),
            issues=issues,
            action_plan=seo_result.get('action_plan', {}),
            potential_score_gain=seo_result.get('potential_score_gain', 0),
            estimated_fix_time_minutes=seo_result.get('estimated_time_minutes', 0)
        )

        return report

    def _update_page_timestamp(self, page):
        """
        Update page's last_analyzed_at timestamp.

        Args:
            page: Page instance
        """
        page.last_analyzed_at = timezone.now()
        page.save(update_fields=['last_analyzed_at'])

    def format_response_data(
        self,
        result: AnalysisResult
    ) -> Dict:
        """
        Format AnalysisResult into response dictionary.

        Args:
            result: AnalysisResult instance

        Returns:
            Dictionary suitable for API response
        """
        # Count issues by severity
        issues = result.seo_data.get('issues', [])
        critical_count = len([i for i in issues if i.get('severity') == IssueSeverity.CRITICAL])
        warning_count = len([i for i in issues if i.get('severity') == IssueSeverity.WARNING])

        response_data = {
            'message': 'Analysis completed successfully',
            'report_id': result.report.id,
            'overall_health_score': result.seo_data.get('overall_health', 0),  # 프론트엔드와 필드명 일치
            'critical_issues_count': critical_count,
            'warning_issues_count': warning_count,
            'issues_found': len(issues),
            'issues_created': len(result.issues),
            'auto_fixable': result.seo_data.get('auto_fix_count', 0),
            'action_plan': result.seo_data.get('action_plan'),
        }

        # Add content analysis if available
        if result.content_data and not result.content_data.get('error'):
            response_data['content_analysis'] = {
                'word_count': result.content_data.get('word_count'),
                'quality_score': result.content_data.get('quality_score'),
                'readability': result.content_data.get('readability')
            }

        return response_data
