"""
SEO Analyzer Models

This module defines the database models for the SEO analyzer application.
Models include Domain, Page, SEOMetrics, AnalyticsData, HistoricalMetrics,
APIQuotaUsage, and ScanJob.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from .constants import IssueSeverity, IssueStatus, VerificationStatus


class Domain(models.Model):
    """
    Main domain being analyzed.
    Stores domain information and aggregated SEO scores.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('error', 'Error'),
    ]

    PROTOCOL_CHOICES = [
        ('http', 'HTTP'),
        ('https', 'HTTPS'),
    ]

    # Basic Information
    domain_name = models.CharField(max_length=255, unique=True, db_index=True)
    protocol = models.CharField(max_length=10, default='https', choices=PROTOCOL_CHOICES)

    # Status
    status = models.CharField(max_length=20, default='active', choices=STATUS_CHOICES)
    last_scanned_at = models.DateTimeField(null=True, blank=True)
    next_scan_at = models.DateTimeField(null=True, blank=True)

    # Google API Connections
    search_console_connected = models.BooleanField(default=False)
    analytics_connected = models.BooleanField(default=False)

    # Aggregated Scores (cached from pages)
    avg_seo_score = models.FloatField(null=True, blank=True)
    avg_performance_score = models.FloatField(null=True, blank=True)
    avg_accessibility_score = models.FloatField(null=True, blank=True)
    avg_pwa_score = models.FloatField(null=True, blank=True)

    # Metadata
    total_pages = models.IntegerField(default=0)
    total_subdomains = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Owner (optional, for multi-user support)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    # Git & Vercel Deployment Configuration
    git_enabled = models.BooleanField(default=False, help_text='Enable Git auto-deployment for SEO fixes')
    git_repository = models.CharField(max_length=500, null=True, blank=True, help_text='Git repository URL (e.g., https://github.com/user/repo.git)')
    git_branch = models.CharField(max_length=100, default='main', help_text='Git branch to push to')
    git_token = models.CharField(max_length=500, null=True, blank=True, help_text='Git personal access token (encrypted)')
    git_target_path = models.CharField(max_length=500, default='public', help_text='Path in repo where HTML files are located (e.g., public, dist)')
    vercel_project_id = models.CharField(max_length=200, null=True, blank=True, help_text='Vercel project ID (optional)')
    vercel_token = models.CharField(max_length=500, null=True, blank=True, help_text='Vercel API token (optional, for deployment tracking)')
    last_deployed_at = models.DateTimeField(null=True, blank=True, help_text='Last Git push timestamp')
    deployment_status = models.CharField(max_length=50, default='never', help_text='Deployment status: never, pending, success, failed')
    last_deployment_error = models.TextField(null=True, blank=True, help_text='Last deployment error message')

    class Meta:
        db_table = 'seo_domains'
        ordering = ['-updated_at']
        verbose_name_plural = 'Domains'

    def __str__(self):
        return f"{self.protocol}://{self.domain_name}"

    def get_full_url(self):
        """Return the full URL with protocol."""
        return f"{self.protocol}://{self.domain_name}"

    def update_aggregate_scores(self):
        """
        Update aggregate scores based on all pages' latest metrics.
        Optimized to use single aggregate query with Subquery instead of prefetch + loop.
        """
        from django.db.models import Subquery, OuterRef, Avg, Count, FloatField

        # Create subqueries for latest scores of each metric type
        def create_latest_score_subquery(field_name):
            return Subquery(
                SEOMetrics.objects.filter(
                    page_id=OuterRef('id')
                ).order_by('-snapshot_date').values(field_name)[:1],
                output_field=FloatField()
            )

        # Single optimized query to get all aggregate data
        active_pages = self.pages.filter(status='active')

        result = active_pages.annotate(
            latest_seo_score=create_latest_score_subquery('seo_score'),
            latest_performance_score=create_latest_score_subquery('performance_score'),
            latest_accessibility_score=create_latest_score_subquery('accessibility_score'),
            latest_pwa_score=create_latest_score_subquery('pwa_score'),
        ).aggregate(
            avg_seo=Avg('latest_seo_score'),
            avg_performance=Avg('latest_performance_score'),
            avg_accessibility=Avg('latest_accessibility_score'),
            avg_pwa=Avg('latest_pwa_score'),
            total_pages=Count('id'),
        )

        # Update domain fields
        self.total_pages = result['total_pages'] or 0
        self.total_subdomains = active_pages.filter(
            is_subdomain=True
        ).values('subdomain').distinct().count()

        # Update average scores (round to 1 decimal)
        self.avg_seo_score = round(result['avg_seo'], 1) if result['avg_seo'] else None
        self.avg_performance_score = round(result['avg_performance'], 1) if result['avg_performance'] else None
        self.avg_accessibility_score = round(result['avg_accessibility'], 1) if result['avg_accessibility'] else None
        self.avg_pwa_score = round(result['avg_pwa'], 1) if result['avg_pwa'] else None

        # Save changes (but don't call save() to avoid triggering updated_at)
        # Caller should call save() explicitly
        return {
            'total_pages': self.total_pages,
            'total_subdomains': self.total_subdomains,
            'avg_seo_score': self.avg_seo_score,
            'avg_performance_score': self.avg_performance_score,
            'avg_accessibility_score': self.avg_accessibility_score,
            'avg_pwa_score': self.avg_pwa_score,
        }


class PageGroupCategory(models.Model):
    """
    Category for organizing groups.
    Provides a hierarchical organization: Category > Group > Page
    Examples: "Marketing", "Technical Docs", "Customer Support"
    """
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='group_categories')
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    icon = models.CharField(max_length=50, default='📁', help_text="Emoji or icon name")
    order = models.IntegerField(default=0, help_text="Display order")
    is_expanded = models.BooleanField(default=True, help_text="UI expansion state")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seo_page_group_categories'
        unique_together = [['domain', 'name']]
        ordering = ['domain', 'order', 'name']
        verbose_name_plural = 'Page Group Categories'

    def __str__(self):
        return f"{self.icon} {self.name}"

    @property
    def group_count(self):
        """Number of groups in this category"""
        return self.groups.count()

    @property
    def page_count(self):
        """Total number of pages in all groups in this category"""
        return sum(group.pages.count() for group in self.groups.all())


class PageGroup(models.Model):
    """
    Custom groups for organizing pages in tree view.
    Allows users to categorize pages with custom colors and names.
    Now supports categorization via PageGroupCategory.
    """
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='page_groups')
    category = models.ForeignKey(
        PageGroupCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='groups',
        help_text="Optional category for organizing groups"
    )
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default='#3B82F6', help_text="Hex color code (e.g., #FF5733)")
    description = models.TextField(null=True, blank=True)
    order = models.IntegerField(default=0, help_text="Display order within category")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seo_page_groups'
        unique_together = [['domain', 'name']]
        ordering = ['domain', 'category__order', 'order', 'name']
        verbose_name_plural = 'Page Groups'

    def __str__(self):
        if self.category:
            return f"{self.category.icon} {self.category.name} > {self.name}"
        return f"{self.name} ({self.domain.domain_name})"

    @property
    def page_count(self):
        """Number of pages in this group"""
        return self.pages.count()

    @property
    def avg_seo_score(self):
        """
        Average SEO score of pages in this group.
        Optimized to use single query with Subquery instead of N+1 queries.
        """
        from django.db.models import Subquery, OuterRef, Avg, FloatField
        from seo_analyzer.models import SEOMetrics

        # Subquery to get the latest SEO score for each page
        # This gets the most recent metric's seo_score for each page
        latest_seo_score_subquery = SEOMetrics.objects.filter(
            page_id=OuterRef('id')
        ).order_by('-snapshot_date').values('seo_score')[:1]

        # Annotate each page with its latest SEO score, then calculate average
        # This results in a single SQL query instead of N+1 queries
        result = self.pages.annotate(
            latest_seo_score=Subquery(
                latest_seo_score_subquery,
                output_field=FloatField()
            )
        ).aggregate(
            avg_score=Avg('latest_seo_score')
        )

        if result['avg_score'] is None:
            return None

        return round(result['avg_score'], 1)


class Page(models.Model):
    """
    Individual pages/subdomains under a domain.
    Supports hierarchical tree structure for subdomain relationships.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('404', 'Not Found'),
        ('500', 'Server Error'),
        ('redirected', 'Redirected'),
    ]

    # Basic Information
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='pages')
    url = models.URLField(max_length=500, db_index=True)  # Reduced for MySQL index limit
    path = models.CharField(max_length=500)  # /about, /products, etc.

    # Subdomain Information
    is_subdomain = models.BooleanField(default=False)
    subdomain = models.CharField(max_length=255, null=True, blank=True)  # blog, shop, etc.

    # Hierarchy (for tree structure)
    parent_page = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children'
    )
    depth_level = models.IntegerField(default=0)  # 0 = root, 1 = subdomain, 2+ = nested

    # Grouping & Organization
    group = models.ForeignKey(
        PageGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pages',
        help_text="Optional group for organizing pages"
    )

    # Page Metadata
    title = models.CharField(max_length=500, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    canonical_url = models.URLField(max_length=2048, null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, default='active', choices=STATUS_CHOICES)
    http_status_code = models.IntegerField(null=True, blank=True)

    # Cache Timestamps
    last_analyzed_at = models.DateTimeField(null=True, blank=True)
    cache_expires_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Manual Customization Fields
    manual_position_x = models.FloatField(
        null=True,
        blank=True,
        help_text="Custom X position in tree visualization"
    )
    manual_position_y = models.FloatField(
        null=True,
        blank=True,
        help_text="Custom Y position in tree visualization"
    )
    use_manual_position = models.BooleanField(
        default=False,
        help_text="Use manual position instead of auto-calculated layout"
    )
    custom_label = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Custom display label (overrides auto-generated label)"
    )
    is_visible = models.BooleanField(
        default=True,
        help_text="Show or hide node in tree visualization"
    )
    is_collapsed = models.BooleanField(
        default=False,
        help_text="Collapse subtree in tree visualization"
    )

    # Audit Trail
    last_manually_edited_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when manual customizations were last made"
    )
    last_edited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edited_pages',
        help_text="User who last manually edited this page"
    )

    class Meta:
        db_table = 'seo_pages'
        ordering = ['depth_level', 'url']
        unique_together = [['domain', 'url']]
        indexes = [
            models.Index(fields=['domain', 'is_subdomain']),
            models.Index(fields=['domain', 'status']),
            models.Index(fields=['domain', 'use_manual_position']),
            models.Index(fields=['is_visible']),
        ]

    def __str__(self):
        return self.url

    def is_cache_valid(self):
        """Check if cached data is still valid."""
        if not self.cache_expires_at:
            return False
        return timezone.now() < self.cache_expires_at


class SEOMetrics(models.Model):
    """
    SEO scores and metrics for a page.
    Includes Lighthouse scores and Core Web Vitals.
    """
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='seo_metrics')

    # Lighthouse Scores (0-100)
    seo_score = models.FloatField(null=True, blank=True)
    performance_score = models.FloatField(null=True, blank=True)
    accessibility_score = models.FloatField(null=True, blank=True)
    best_practices_score = models.FloatField(null=True, blank=True)
    pwa_score = models.FloatField(null=True, blank=True)

    # Core Web Vitals
    lcp = models.FloatField(null=True, blank=True, help_text="Largest Contentful Paint (ms)")
    fid = models.FloatField(null=True, blank=True, help_text="First Input Delay (ms)")
    cls = models.FloatField(null=True, blank=True, help_text="Cumulative Layout Shift")
    fcp = models.FloatField(null=True, blank=True, help_text="First Contentful Paint (ms)")
    tti = models.FloatField(null=True, blank=True, help_text="Time to Interactive (ms)")
    tbt = models.FloatField(null=True, blank=True, help_text="Total Blocking Time (ms)")

    # Search Console Metrics
    impressions = models.BigIntegerField(null=True, blank=True)
    clicks = models.BigIntegerField(null=True, blank=True)
    ctr = models.FloatField(null=True, blank=True, help_text="Click-through rate")
    avg_position = models.FloatField(null=True, blank=True)

    # Indexing Status
    is_indexed = models.BooleanField(default=False)
    index_status = models.CharField(max_length=100, null=True, blank=True)
    coverage_state = models.CharField(max_length=100, null=True, blank=True)

    # Mobile vs Desktop
    mobile_friendly = models.BooleanField(default=False)
    mobile_score = models.FloatField(null=True, blank=True)
    desktop_score = models.FloatField(null=True, blank=True)

    # Snapshot Timestamp
    snapshot_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'seo_metrics'
        ordering = ['-snapshot_date']
        indexes = [
            models.Index(fields=['page', '-snapshot_date']),
        ]
        verbose_name_plural = 'SEO Metrics'

    def __str__(self):
        return f"SEO Metrics for {self.page.url} at {self.snapshot_date}"

    def get_overall_score(self):
        """Calculate weighted overall SEO score."""
        weights = {
            'seo_score': 0.30,
            'performance_score': 0.25,
            'accessibility_score': 0.20,
            'best_practices_score': 0.15,
            'pwa_score': 0.10,
        }

        scores = [
            (self.seo_score or 0) * weights['seo_score'],
            (self.performance_score or 0) * weights['performance_score'],
            (self.accessibility_score or 0) * weights['accessibility_score'],
            (self.best_practices_score or 0) * weights['best_practices_score'],
            (self.pwa_score or 0) * weights['pwa_score'],
        ]

        return round(sum(scores), 2)


class AnalyticsData(models.Model):
    """
    Google Analytics data for a page.
    Stores traffic and engagement metrics.
    """
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='analytics')

    # Traffic Metrics
    page_views = models.BigIntegerField(null=True, blank=True)
    unique_visitors = models.BigIntegerField(null=True, blank=True)
    sessions = models.BigIntegerField(null=True, blank=True)
    avg_session_duration = models.FloatField(null=True, blank=True, help_text="Seconds")
    bounce_rate = models.FloatField(null=True, blank=True, help_text="Percentage")

    # Engagement
    pages_per_session = models.FloatField(null=True, blank=True)
    new_users = models.BigIntegerField(null=True, blank=True)
    returning_users = models.BigIntegerField(null=True, blank=True)

    # Conversions
    goal_completions = models.BigIntegerField(null=True, blank=True)
    conversion_rate = models.FloatField(null=True, blank=True)

    # Traffic Sources (aggregated)
    organic_traffic = models.BigIntegerField(null=True, blank=True)
    direct_traffic = models.BigIntegerField(null=True, blank=True)
    referral_traffic = models.BigIntegerField(null=True, blank=True)
    social_traffic = models.BigIntegerField(null=True, blank=True)

    # Date Range
    date_from = models.DateField()
    date_to = models.DateField()
    snapshot_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'seo_analytics_data'
        ordering = ['-snapshot_date']
        indexes = [
            models.Index(fields=['page', '-snapshot_date']),
            models.Index(fields=['date_from', 'date_to']),
        ]
        verbose_name_plural = 'Analytics Data'

    def __str__(self):
        return f"Analytics for {self.page.url} ({self.date_from} to {self.date_to})"


class HistoricalMetrics(models.Model):
    """
    Historical tracking for trend analysis.
    Stores daily snapshots of key metrics.
    """
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='historical_metrics')

    # Key Scores (denormalized for faster queries)
    seo_score = models.FloatField(null=True, blank=True)
    performance_score = models.FloatField(null=True, blank=True)
    accessibility_score = models.FloatField(null=True, blank=True)

    # Aggregated Metrics
    avg_position = models.FloatField(null=True, blank=True)
    total_clicks = models.BigIntegerField(null=True, blank=True)
    total_impressions = models.BigIntegerField(null=True, blank=True)

    # Snapshot Date (daily snapshots)
    date = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'seo_historical_metrics'
        ordering = ['-date']
        unique_together = [['page', 'date']]
        indexes = [
            models.Index(fields=['page', '-date']),
        ]
        verbose_name_plural = 'Historical Metrics'

    def __str__(self):
        return f"Historical metrics for {self.page.url} on {self.date}"


class APIQuotaUsage(models.Model):
    """
    Track Google API quota usage to manage rate limits.
    """
    API_CHOICES = [
        ('search_console', 'Search Console'),
        ('pagespeed', 'PageSpeed Insights'),
        ('lighthouse', 'Lighthouse'),
        ('analytics', 'Google Analytics'),
    ]

    api_name = models.CharField(max_length=50, choices=API_CHOICES)

    # Quota Tracking
    requests_made = models.IntegerField(default=0)
    quota_limit = models.IntegerField(null=True, blank=True)
    quota_remaining = models.IntegerField(null=True, blank=True)

    # Errors
    rate_limit_hits = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    last_error = models.TextField(null=True, blank=True)

    # Time Window
    date = models.DateField(auto_now_add=True, db_index=True)
    reset_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'seo_api_quota_usage'
        ordering = ['-date']
        unique_together = [['api_name', 'date']]
        verbose_name_plural = 'API Quota Usage'

    def __str__(self):
        return f"{self.api_name} quota on {self.date}: {self.requests_made} requests"

    def is_near_limit(self, threshold=0.8):
        """Check if quota usage is near the limit (default 80%)."""
        if not self.quota_limit:
            return False
        return self.requests_made >= (self.quota_limit * threshold)


class ScanJob(models.Model):
    """
    Track background scan jobs for domains.
    """
    JOB_TYPE_CHOICES = [
        ('full_scan', 'Full Scan'),
        ('quick_refresh', 'Quick Refresh'),
        ('subdomain_discovery', 'Subdomain Discovery'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    # Job Information
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='scan_jobs')
    job_type = models.CharField(max_length=50, choices=JOB_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    # Celery Task ID
    celery_task_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)

    # Progress Tracking
    progress_percent = models.IntegerField(default=0)
    pages_scanned = models.IntegerField(default=0)
    total_pages = models.IntegerField(default=0)

    # Results
    result_summary = models.JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'seo_scan_jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['domain', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
        verbose_name_plural = 'Scan Jobs'

    def __str__(self):
        return f"{self.job_type} for {self.domain.domain_name} - {self.status}"

    def mark_started(self):
        """Mark job as started."""
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])

    def mark_completed(self, summary=None):
        """Mark job as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.progress_percent = 100
        if summary:
            self.result_summary = summary
        self.save(update_fields=['status', 'completed_at', 'progress_percent', 'result_summary'])

    def mark_failed(self, error_message):
        """Mark job as failed."""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'error_message'])

    def update_progress(self, percent, pages_scanned=None):
        """Update job progress."""
        self.progress_percent = min(percent, 100)
        if pages_scanned is not None:
            self.pages_scanned = pages_scanned
        self.save(update_fields=['progress_percent', 'pages_scanned'])


class SEOIssue(models.Model):
    """
    SEO Issue Tracking
    Records SEO problems found on each page
    """
    # Use centralized constants for choices
    SEVERITY_CHOICES = IssueSeverity.CHOICES
    STATUS_CHOICES = IssueStatus.CHOICES

    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='seo_issues')
    issue_type = models.CharField(max_length=100, db_index=True)  # meta_description_missing, etc.
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=IssueStatus.OPEN, db_index=True)

    title = models.CharField(max_length=200)
    message = models.TextField()
    fix_suggestion = models.TextField(null=True, blank=True)

    # Auto-fix related
    auto_fix_available = models.BooleanField(default=False)
    auto_fix_method = models.CharField(max_length=100, null=True, blank=True)

    # Impact level
    impact = models.CharField(max_length=20, default='medium')  # critical, high, medium, low

    # Metadata
    current_value = models.TextField(null=True, blank=True)
    suggested_value = models.TextField(null=True, blank=True)
    extra_data = models.JSONField(default=dict, blank=True)  # Additional information

    # Git Deployment Tracking
    deployed_to_git = models.BooleanField(default=False, help_text='Whether the fix was deployed to Git')
    deployed_at = models.DateTimeField(null=True, blank=True, help_text='When the fix was deployed to Git')
    deployment_commit_hash = models.CharField(max_length=40, null=True, blank=True, help_text='Git commit hash of deployment')

    # Verification Status (after Git deployment)
    VERIFICATION_STATUS_CHOICES = VerificationStatus.CHOICES
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default=VerificationStatus.NOT_DEPLOYED,
        help_text='Verification status after Git deployment'
    )
    verified_at = models.DateTimeField(null=True, blank=True, help_text='When the fix was verified')

    # Timestamps
    detected_at = models.DateTimeField(auto_now_add=True, db_index=True)
    fixed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'seo_issues'
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['page', 'status']),
            models.Index(fields=['severity', 'status']),
            models.Index(fields=['detected_at']),
        ]
        verbose_name_plural = 'SEO Issues'

    def __str__(self):
        return f"[{self.severity}] {self.title} - {self.page.url}"

    def mark_fixed(self):
        """Mark issue as fixed."""
        self.status = 'fixed'
        self.fixed_at = timezone.now()
        self.save(update_fields=['status', 'fixed_at'])

    def mark_auto_fixed(self):
        """Mark issue as automatically fixed."""
        self.status = 'auto_fixed'
        self.fixed_at = timezone.now()
        self.save(update_fields=['status', 'fixed_at'])


class SitemapConfig(models.Model):
    """
    Sitemap Configuration
    """
    DEPLOYMENT_METHODS = [
        ('direct', 'Direct (Django Static)'),
        ('ftp', 'FTP'),
        ('sftp', 'SFTP'),
        ('git', 'Git'),
    ]

    domain = models.OneToOneField(Domain, on_delete=models.CASCADE, related_name='sitemap_config')

    # Generation settings
    include_images = models.BooleanField(default=True)
    include_videos = models.BooleanField(default=False)
    max_urls = models.IntegerField(default=50000)

    # Deployment settings
    deployment_method = models.CharField(max_length=20, choices=DEPLOYMENT_METHODS, default='direct')
    deployment_config = models.JSONField(default=dict, blank=True)  # FTP/SFTP/Git config

    # Automation
    auto_generate = models.BooleanField(default=True)
    auto_deploy = models.BooleanField(default=False)
    auto_submit_to_search_console = models.BooleanField(default=False)

    # Existing sitemap URL (for importing)
    existing_sitemap_url = models.URLField(max_length=500, null=True, blank=True, help_text="URL of existing sitemap to import")

    # Timestamps
    last_generated_at = models.DateTimeField(null=True, blank=True)
    last_deployed_at = models.DateTimeField(null=True, blank=True)
    last_submitted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seo_sitemap_configs'
        verbose_name_plural = 'Sitemap Configs'

    def __str__(self):
        return f"Sitemap Config: {self.domain.domain_name}"


class SitemapHistory(models.Model):
    """
    Sitemap Generation/Deployment History
    """
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='sitemap_history')

    # Sitemap information
    url_count = models.IntegerField()
    file_size_bytes = models.BigIntegerField()
    sitemap_url = models.URLField(max_length=500, null=True, blank=True)

    # Status
    generated = models.BooleanField(default=False)
    deployed = models.BooleanField(default=False)
    submitted_to_search_console = models.BooleanField(default=False)

    # Validation results
    validation_errors = models.JSONField(default=list, blank=True)
    validation_warnings = models.JSONField(default=list, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'seo_sitemap_history'
        ordering = ['-created_at']
        verbose_name_plural = 'Sitemap History'

    def __str__(self):
        return f"Sitemap: {self.domain.domain_name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class SEOAnalysisReport(models.Model):
    """
    SEO Analysis Report
    Full domain or individual page analysis results
    """
    REPORT_TYPES = [
        ('page', 'Page Analysis'),
        ('domain', 'Domain Analysis'),
    ]

    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='seo_reports')
    page = models.ForeignKey(Page, on_delete=models.CASCADE, null=True, blank=True, related_name='seo_reports')

    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)

    # Analysis results
    overall_health_score = models.IntegerField(default=0)  # 0-100
    critical_issues_count = models.IntegerField(default=0)
    warning_issues_count = models.IntegerField(default=0)
    info_issues_count = models.IntegerField(default=0)

    # Auto-fix
    auto_fixable_count = models.IntegerField(default=0)
    fixed_count = models.IntegerField(default=0)

    # Detailed data (JSON)
    issues = models.JSONField(default=list, blank=True)
    action_plan = models.JSONField(default=dict, blank=True)
    auto_fix_results = models.JSONField(default=dict, blank=True)

    # Expected improvement
    potential_score_gain = models.IntegerField(default=0)
    estimated_fix_time_minutes = models.IntegerField(default=0)

    # Timestamps
    analyzed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'seo_analysis_reports'
        ordering = ['-analyzed_at']
        indexes = [
            models.Index(fields=['domain', 'report_type', '-analyzed_at']),
        ]
        verbose_name_plural = 'SEO Analysis Reports'

    def __str__(self):
        return f"SEO Report: {self.domain.domain_name} - {self.analyzed_at.strftime('%Y-%m-%d')}"
