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

    # Sitemap AI Analysis
    sitemap_ai_enabled = models.BooleanField(default=True, help_text='Include in Sitemap AI analysis target list')

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

    # Sitemap Mismatch Tracking
    sitemap_url = models.URLField(
        max_length=2048,
        null=True,
        blank=True,
        help_text="URL as it appears in the sitemap (may differ from canonical due to redirects)"
    )
    has_sitemap_mismatch = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if sitemap URL differs from canonical URL (redirect issue)"
    )
    redirect_chain = models.JSONField(
        null=True,
        blank=True,
        help_text="List of redirect hops from sitemap URL to canonical URL"
    )
    sitemap_entry = models.JSONField(
        null=True,
        blank=True,
        help_text="Original sitemap entry data (loc, lastmod, changefreq, priority)"
    )

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

    def get_latest_metrics(self):
        """
        Get the latest SEO metrics for this page.
        Returns None if no metrics exist.

        Note: If using with prefetch_related('seo_metrics'),
        this will use the cached queryset.
        """
        return self.seo_metrics.first()

    @property
    def latest_seo_score(self):
        """
        Get the latest SEO score for this page.
        Returns None if no metrics exist.
        """
        metrics = self.get_latest_metrics()
        return metrics.seo_score if metrics else None

    @property
    def latest_performance_score(self):
        """Get the latest performance score for this page."""
        metrics = self.get_latest_metrics()
        return metrics.performance_score if metrics else None

    @property
    def latest_accessibility_score(self):
        """Get the latest accessibility score for this page."""
        metrics = self.get_latest_metrics()
        return metrics.accessibility_score if metrics else None


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
    top_queries = models.JSONField(
        null=True,
        blank=True,
        help_text="Top search queries for this page from Search Console"
    )

    # Indexing Status (for sitemap URL)
    is_indexed = models.BooleanField(default=False)
    index_status = models.CharField(max_length=100, null=True, blank=True)
    coverage_state = models.CharField(max_length=100, null=True, blank=True)

    # Canonical URL Index Status (when different from sitemap URL)
    canonical_is_indexed = models.BooleanField(null=True, blank=True, help_text="Index status of canonical URL")
    canonical_index_status = models.CharField(max_length=100, null=True, blank=True)
    canonical_coverage_state = models.CharField(max_length=100, null=True, blank=True)

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

    # AI Fix Fields
    ai_fix_generated = models.BooleanField(default=False, help_text='Whether an AI fix was generated')
    ai_fix_generated_at = models.DateTimeField(null=True, blank=True, help_text='When AI fix was generated')
    ai_fix_confidence = models.FloatField(null=True, blank=True, help_text='AI confidence score (0-1)')
    ai_fix_explanation = models.TextField(null=True, blank=True, help_text='AI explanation for the fix')

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


class AIFixHistory(models.Model):
    """
    AI Fix History - 페이지별 AI 수정 이력 추적

    동일 페이지에서 반복되는 문제 해결 시 과거 이력을 참조하여
    더 나은 수정안을 생성할 수 있도록 합니다.
    """
    FIX_STATUS_CHOICES = [
        ('applied', '적용됨'),
        ('deployed', '배포됨'),
        ('verified', '검증됨'),
        ('reverted', '되돌림'),
        ('superseded', '대체됨'),  # 새 수정으로 덮어쓰임
        ('failed', '실패'),
    ]

    EFFECTIVENESS_CHOICES = [
        ('unknown', '알 수 없음'),
        ('effective', '효과적'),  # 이슈가 해결됨
        ('partial', '부분적'),    # 개선되었지만 완전히 해결되지 않음
        ('ineffective', '비효과적'),  # 이슈가 재발
        ('negative', '부정적'),   # 오히려 악화됨
    ]

    # 관계
    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name='ai_fix_history',
        help_text='수정이 적용된 페이지'
    )
    issue = models.ForeignKey(
        SEOIssue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fix_history',
        help_text='원본 이슈 (삭제되어도 이력은 유지)'
    )

    # 수정 내용
    issue_type = models.CharField(max_length=100, db_index=True, help_text='이슈 유형')
    original_value = models.TextField(null=True, blank=True, help_text='수정 전 값')
    fixed_value = models.TextField(help_text='AI가 제안한 수정 값')

    # AI 분석 정보
    ai_explanation = models.TextField(help_text='AI가 이 수정을 제안한 이유')
    ai_confidence = models.FloatField(default=0.0, help_text='AI 신뢰도 (0-1)')
    ai_model = models.CharField(max_length=100, default='claude-sonnet-4-20250514', help_text='사용된 AI 모델')

    # 수정 시점의 컨텍스트 스냅샷 (추후 분석용)
    context_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text='수정 시점의 SEO 데이터 스냅샷 (Search Console, 키워드 등)'
    )

    # 상태 추적
    fix_status = models.CharField(
        max_length=20,
        choices=FIX_STATUS_CHOICES,
        default='applied',
        db_index=True
    )

    # 효과성 평가
    effectiveness = models.CharField(
        max_length=20,
        choices=EFFECTIVENESS_CHOICES,
        default='unknown',
        help_text='수정의 효과성'
    )
    effectiveness_evaluated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='효과성 평가 시점'
    )

    # 이슈 재발 추적
    issue_recurred = models.BooleanField(
        default=False,
        help_text='동일 이슈가 재발했는지'
    )
    recurrence_detected_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='재발 감지 시점'
    )
    recurrence_count = models.IntegerField(
        default=0,
        help_text='재발 횟수'
    )

    # SEO 성과 변화 (수정 전후 비교용)
    pre_fix_metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text='수정 전 SEO 지표 (CTR, 순위 등)'
    )
    post_fix_metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text='수정 후 SEO 지표'
    )

    # Git 배포 정보
    deployed_to_git = models.BooleanField(default=False)
    deployment_commit_hash = models.CharField(max_length=40, null=True, blank=True)
    deployed_at = models.DateTimeField(null=True, blank=True)

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_fix_history'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['page', 'issue_type']),
            models.Index(fields=['page', 'created_at']),
            models.Index(fields=['issue_type', 'effectiveness']),
            models.Index(fields=['fix_status']),
        ]
        verbose_name = 'AI Fix History'
        verbose_name_plural = 'AI Fix Histories'

    def __str__(self):
        return f"[{self.issue_type}] {self.page.url} - {self.created_at.strftime('%Y-%m-%d')}"

    def mark_as_effective(self, post_metrics: dict = None):
        """수정이 효과적이었음을 표시"""
        self.effectiveness = 'effective'
        self.effectiveness_evaluated_at = timezone.now()
        if post_metrics:
            self.post_fix_metrics = post_metrics
        self.save(update_fields=['effectiveness', 'effectiveness_evaluated_at', 'post_fix_metrics'])

    def mark_as_recurred(self):
        """이슈 재발 표시"""
        self.issue_recurred = True
        self.recurrence_count += 1
        self.recurrence_detected_at = timezone.now()
        self.effectiveness = 'ineffective'
        self.effectiveness_evaluated_at = timezone.now()
        self.save(update_fields=[
            'issue_recurred', 'recurrence_count', 'recurrence_detected_at',
            'effectiveness', 'effectiveness_evaluated_at'
        ])

    def mark_as_superseded(self):
        """새 수정으로 대체됨 표시"""
        self.fix_status = 'superseded'
        self.save(update_fields=['fix_status'])

    @classmethod
    def get_page_history(cls, page, issue_type: str = None, limit: int = 10):
        """페이지의 AI 수정 이력 조회"""
        qs = cls.objects.filter(page=page)
        if issue_type:
            qs = qs.filter(issue_type=issue_type)
        return qs.order_by('-created_at')[:limit]

    @classmethod
    def get_effective_fixes(cls, issue_type: str, limit: int = 5):
        """특정 이슈 유형에서 효과적이었던 수정 패턴 조회"""
        return cls.objects.filter(
            issue_type=issue_type,
            effectiveness='effective'
        ).order_by('-ai_confidence', '-created_at')[:limit]


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


# =============================================================================
# Sitemap Editor Models
# =============================================================================

class SitemapEntry(models.Model):
    """
    Individual sitemap entry for editing.
    Separate from Page model to allow editing before deployment.
    """
    CHANGEFREQ_CHOICES = [
        ('always', 'Always'),
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('never', 'Never'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('pending_add', 'Pending Add'),
        ('pending_remove', 'Pending Remove'),
        ('pending_modify', 'Pending Modify'),
    ]

    # Relations
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='sitemap_entries')
    page = models.ForeignKey(
        Page,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sitemap_entries',
        help_text="Linked page (if exists)"
    )

    # Sitemap Entry Fields
    loc = models.URLField(max_length=2048, help_text="URL location")
    loc_hash = models.CharField(
        max_length=64,
        db_index=True,
        editable=False,
        help_text="SHA256 hash of loc for uniqueness constraint"
    )
    lastmod = models.DateField(null=True, blank=True, help_text="Last modification date")
    changefreq = models.CharField(
        max_length=20,
        choices=CHANGEFREQ_CHOICES,
        null=True,
        blank=True,
        help_text="Change frequency"
    )
    priority = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Priority (0.0-1.0)"
    )

    # Entry Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', db_index=True)

    # Validation
    is_valid = models.BooleanField(default=True)
    validation_errors = models.JSONField(default=list, blank=True)

    # AI Suggestions
    ai_suggested = models.BooleanField(default=False, help_text="Entry suggested by AI")
    ai_suggestion_reason = models.TextField(null=True, blank=True)

    # AI Analysis Target
    ai_analysis_enabled = models.BooleanField(default=True, help_text="Include in AI analysis")

    # URL Status (cached from HTTP check)
    http_status_code = models.IntegerField(null=True, blank=True)
    redirect_url = models.URLField(max_length=2048, null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seo_sitemap_entries'
        ordering = ['domain', 'loc']
        unique_together = [['domain', 'loc_hash']]
        indexes = [
            models.Index(fields=['domain', 'status']),
            models.Index(fields=['domain', 'is_valid']),
            models.Index(fields=['ai_suggested']),
        ]
        verbose_name_plural = 'Sitemap Entries'

    def __str__(self):
        return f"{self.loc} ({self.status})"

    def save(self, *args, **kwargs):
        """Auto-generate loc_hash before saving"""
        import hashlib
        if self.loc:
            self.loc_hash = hashlib.sha256(self.loc.encode('utf-8')).hexdigest()
        super().save(*args, **kwargs)

    def to_xml_element(self):
        """Generate XML element for sitemap"""
        lines = ['  <url>']
        lines.append(f'    <loc>{self.loc}</loc>')
        if self.lastmod:
            lines.append(f'    <lastmod>{self.lastmod.isoformat()}</lastmod>')
        if self.changefreq:
            lines.append(f'    <changefreq>{self.changefreq}</changefreq>')
        if self.priority is not None:
            lines.append(f'    <priority>{self.priority}</priority>')
        lines.append('  </url>')
        return '\n'.join(lines)


class SitemapEditSession(models.Model):
    """
    Edit session for tracking sitemap changes.
    Supports draft → preview → deploy workflow.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('preview', 'Preview'),
        ('validating', 'Validating'),
        ('deploying', 'Deploying'),
        ('deployed', 'Deployed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    # Relations
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='sitemap_edit_sessions')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sitemap_edit_sessions'
    )

    # Session Info
    name = models.CharField(max_length=200, null=True, blank=True, help_text="Optional session name")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)

    # Change Summary
    entries_added = models.IntegerField(default=0)
    entries_removed = models.IntegerField(default=0)
    entries_modified = models.IntegerField(default=0)
    total_entries = models.IntegerField(default=0)

    # AI Analysis Results
    ai_issues_found = models.JSONField(default=list, blank=True, help_text="List of issues found by AI")
    ai_suggestions = models.JSONField(default=list, blank=True, help_text="AI suggestions for improvements")
    ai_analysis_completed_at = models.DateTimeField(null=True, blank=True)

    # Deployment Info
    deployment_commit_hash = models.CharField(max_length=40, null=True, blank=True)
    deployment_message = models.TextField(null=True, blank=True)
    deployment_error = models.TextField(null=True, blank=True)
    deployed_at = models.DateTimeField(null=True, blank=True)

    # Preview XML (cached)
    preview_xml = models.TextField(null=True, blank=True, help_text="Generated XML preview")
    preview_generated_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seo_sitemap_edit_sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['domain', 'status']),
            models.Index(fields=['domain', '-created_at']),
        ]
        verbose_name_plural = 'Sitemap Edit Sessions'

    def __str__(self):
        name = self.name or f"Session #{self.id}"
        return f"{name} ({self.domain.domain_name}) - {self.status}"

    def get_changes_summary(self):
        """Get summary of changes in this session"""
        return {
            'added': self.entries_added,
            'removed': self.entries_removed,
            'modified': self.entries_modified,
            'total': self.total_entries,
            'has_changes': self.entries_added > 0 or self.entries_removed > 0 or self.entries_modified > 0,
        }


class SitemapEntryChange(models.Model):
    """
    Audit trail for sitemap entry changes.
    Tracks all modifications for rollback and history.
    """
    CHANGE_TYPE_CHOICES = [
        ('add', 'Add'),
        ('remove', 'Remove'),
        ('modify', 'Modify'),
    ]

    SOURCE_CHOICES = [
        ('manual', 'Manual Edit'),
        ('ai_suggestion', 'AI Suggestion'),
        ('bulk_import', 'Bulk Import'),
        ('sync', 'Sync from Live'),
    ]

    # Relations
    session = models.ForeignKey(
        SitemapEditSession,
        on_delete=models.CASCADE,
        related_name='changes'
    )
    entry = models.ForeignKey(
        SitemapEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='change_history'
    )

    # Change Details
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual')

    # URL (kept even if entry is deleted)
    url = models.URLField(max_length=2048)

    # Values (for modify and rollback)
    old_values = models.JSONField(null=True, blank=True, help_text="Values before change")
    new_values = models.JSONField(null=True, blank=True, help_text="Values after change")

    # AI related
    ai_reason = models.TextField(null=True, blank=True, help_text="Reason if AI suggested")

    # User who made the change
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sitemap_changes'
    )

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'seo_sitemap_entry_changes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session', '-created_at']),
            models.Index(fields=['entry', '-created_at']),
            models.Index(fields=['change_type']),
        ]
        verbose_name_plural = 'Sitemap Entry Changes'

    def __str__(self):
        return f"{self.change_type.upper()}: {self.url}"

    def get_diff(self):
        """Get diff between old and new values"""
        if self.change_type == 'add':
            return {'added': self.new_values}
        elif self.change_type == 'remove':
            return {'removed': self.old_values}
        else:
            # modify
            diff = {}
            old = self.old_values or {}
            new = self.new_values or {}
            all_keys = set(old.keys()) | set(new.keys())
            for key in all_keys:
                if old.get(key) != new.get(key):
                    diff[key] = {'old': old.get(key), 'new': new.get(key)}
            return diff


class AIAnalysisCache(models.Model):
    """
    Cache for AI analysis results.
    Reduces API calls by caching analysis for similar contexts.
    """
    ANALYSIS_TYPE_CHOICES = [
        ('sitemap', 'Sitemap Analysis'),
        ('seo_issues', 'SEO Issues Analysis'),
        ('page_content', 'Page Content Analysis'),
        ('full_domain', 'Full Domain Analysis'),
    ]

    # Relations
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='ai_analysis_cache')
    page = models.ForeignKey(Page, on_delete=models.CASCADE, null=True, blank=True, related_name='ai_analysis_cache')

    # Analysis Info
    analysis_type = models.CharField(max_length=30, choices=ANALYSIS_TYPE_CHOICES)
    context_hash = models.CharField(max_length=64, db_index=True, help_text="Hash of input context for cache lookup")

    # Results
    analysis_result = models.JSONField(help_text="AI analysis result")
    suggestions = models.JSONField(default=list, blank=True)
    issues = models.JSONField(default=list, blank=True)

    # API Usage
    model_used = models.CharField(max_length=50, default='claude-sonnet-4-20250514')
    tokens_used = models.IntegerField(default=0)
    api_cost = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)

    # Cache Control
    expires_at = models.DateTimeField(help_text="Cache expiration time")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'seo_ai_analysis_cache'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['domain', 'analysis_type', 'context_hash']),
            models.Index(fields=['expires_at']),
        ]
        verbose_name_plural = 'AI Analysis Cache'

    def __str__(self):
        return f"{self.analysis_type} for {self.domain.domain_name}"

    def is_valid(self):
        """Check if cache is still valid"""
        return timezone.now() < self.expires_at


# =============================================================================
# SEO Analysis Report (existing)
# =============================================================================

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


class AIConversation(models.Model):
    """
    AI Conversation Session
    Stores conversations with Claude AI for SEO analysis
    """
    CONVERSATION_TYPES = [
        ('sitemap_analysis', 'Sitemap Analysis'),
        ('seo_issues', 'SEO Issues Analysis'),
        ('full_report', 'Full Report'),
        ('general', 'General Question'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('archived', 'Archived'),
    ]

    # Relationships
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='ai_conversations',
        null=True,
        blank=True,
        help_text="Domain being analyzed (optional for general questions)"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_conversations'
    )

    # Conversation info
    title = models.CharField(max_length=200, blank=True)
    conversation_type = models.CharField(
        max_length=30,
        choices=CONVERSATION_TYPES,
        default='general'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # Metadata
    total_messages = models.IntegerField(default=0)
    total_tokens_used = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'seo_ai_conversations'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['domain', '-updated_at']),
            models.Index(fields=['created_by', '-updated_at']),
            models.Index(fields=['conversation_type']),
        ]
        verbose_name_plural = 'AI Conversations'

    def __str__(self):
        domain_name = self.domain.domain_name if self.domain else 'General'
        return f"AI Chat: {domain_name} - {self.title or self.conversation_type}"

    def save(self, *args, **kwargs):
        if not self.title:
            domain_name = self.domain.domain_name if self.domain else 'General'
            self.title = f"{domain_name} - {self.get_conversation_type_display()}"
        super().save(*args, **kwargs)


class AIMessage(models.Model):
    """
    Individual message in an AI conversation
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('analysis', 'Analysis Result'),
        ('suggestion', 'Suggestion'),
        ('error', 'Error'),
    ]

    # Relationships
    conversation = models.ForeignKey(
        AIConversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )

    # Message content
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    content = models.TextField(help_text="Message text content")

    # Structured data (for analysis results)
    structured_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Structured data like analysis results, suggestions"
    )

    # Token usage
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'seo_ai_messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]
        verbose_name_plural = 'AI Messages'

    def __str__(self):
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"[{self.role}] {preview}"


# =============================================================================
# Tree Workspace Models
# =============================================================================

class Workspace(models.Model):
    """
    Tree Workspace - 여러 도메인 트리를 탭으로 관리하는 워크스페이스
    사용자가 여러 트리를 조합하여 편집하고 저장할 수 있음
    """
    # Owner
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tree_workspaces',
        null=True,
        blank=True,
        help_text="워크스페이스 소유자"
    )

    # Basic Info
    name = models.CharField(max_length=100, help_text="워크스페이스 이름")
    description = models.TextField(null=True, blank=True, help_text="워크스페이스 설명")

    # Settings
    is_default = models.BooleanField(
        default=False,
        help_text="기본 워크스페이스 여부 (로그인 시 자동 로드)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_opened_at = models.DateTimeField(null=True, blank=True, help_text="마지막 열람 시간")

    class Meta:
        db_table = 'seo_workspaces'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['owner', '-updated_at']),
            models.Index(fields=['owner', 'is_default']),
        ]
        verbose_name = 'Workspace'
        verbose_name_plural = 'Workspaces'

    def __str__(self):
        return f"{self.name}"

    def save(self, *args, **kwargs):
        # 기본 워크스페이스 설정 시 다른 기본 워크스페이스 해제
        if self.is_default and self.owner:
            Workspace.objects.filter(owner=self.owner, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @property
    def tab_count(self):
        """탭 개수"""
        return self.tabs.count()

    def get_active_tab(self):
        """현재 활성 탭 반환"""
        return self.tabs.filter(is_active=True).first()


class WorkspaceTab(models.Model):
    """
    Workspace Tab - 워크스페이스 내 개별 탭
    각 탭은 하나의 도메인 트리를 표시하며 독립적인 뷰포트/설정을 가짐
    """
    # Relations
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='tabs',
        help_text="소속 워크스페이스"
    )
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='workspace_tabs',
        help_text="표시할 도메인"
    )

    # Tab Settings
    name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="커스텀 탭 이름 (비어있으면 도메인명 사용)"
    )
    order = models.PositiveIntegerField(default=0, help_text="탭 순서")
    is_active = models.BooleanField(default=False, help_text="현재 활성 탭")

    # Viewport State (React Flow 줌/팬 상태)
    viewport = models.JSONField(
        default=dict,
        blank=True,
        help_text="뷰포트 상태 {x, y, zoom}"
    )

    # Tab-specific Preferences (필터, 레이아웃 등)
    preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="탭별 설정 {filterMode, layoutDirection, showHiddenNodes, ...}"
    )

    # Custom Node Positions (도메인 원본과 별개로 탭에서만 사용)
    custom_positions = models.JSONField(
        default=dict,
        blank=True,
        help_text="커스텀 노드 위치 {nodeId: {x, y}, ...}"
    )

    # Unsaved Changes Tracking
    has_unsaved_changes = models.BooleanField(
        default=False,
        help_text="미저장 변경사항 존재 여부"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seo_workspace_tabs'
        ordering = ['workspace', 'order']
        indexes = [
            models.Index(fields=['workspace', 'order']),
            models.Index(fields=['workspace', 'is_active']),
        ]
        verbose_name = 'Workspace Tab'
        verbose_name_plural = 'Workspace Tabs'

    def __str__(self):
        tab_name = self.name or self.domain.domain_name
        return f"{self.workspace.name} - {tab_name}"

    def save(self, *args, **kwargs):
        # 활성 탭 설정 시 같은 워크스페이스의 다른 활성 탭 해제
        if self.is_active:
            WorkspaceTab.objects.filter(
                workspace=self.workspace,
                is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def get_display_name(self):
        """표시용 이름 반환"""
        return self.name or self.domain.domain_name

    def update_viewport(self, x, y, zoom):
        """뷰포트 상태 업데이트"""
        self.viewport = {'x': x, 'y': y, 'zoom': zoom}
        self.save(update_fields=['viewport', 'updated_at'])

    def update_preferences(self, preferences_dict):
        """탭 설정 업데이트"""
        self.preferences.update(preferences_dict)
        self.save(update_fields=['preferences', 'updated_at'])

    def update_custom_positions(self, positions_dict):
        """커스텀 노드 위치 업데이트"""
        self.custom_positions.update(positions_dict)
        self.has_unsaved_changes = True
        self.save(update_fields=['custom_positions', 'has_unsaved_changes', 'updated_at'])

    def clear_unsaved_changes(self):
        """미저장 플래그 초기화"""
        self.has_unsaved_changes = False
        self.save(update_fields=['has_unsaved_changes', 'updated_at'])


# =============================================================================
# Canvas Tab Models (Per-Domain)
# =============================================================================

class CanvasTab(models.Model):
    """
    Canvas Tab - 도메인별 캔버스 탭
    main 탭: 읽기 전용, 실제 배포된 트리 그대로 표시
    커스텀 탭: 편집 가능, 커스텀 위치/뷰포트 저장
    """
    # Domain relation
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='canvas_tabs',
        help_text="소속 도메인"
    )

    # Tab Settings
    name = models.CharField(
        max_length=100,
        help_text="탭 이름 (main, 2, 3, ...)"
    )
    is_main = models.BooleanField(
        default=False,
        help_text="메인 탭 여부 (메인 탭은 읽기 전용)"
    )
    order = models.PositiveIntegerField(default=0, help_text="탭 순서")
    is_active = models.BooleanField(default=False, help_text="현재 활성 탭")

    # Viewport State (React Flow 줌/팬 상태)
    viewport = models.JSONField(
        default=dict,
        blank=True,
        help_text="뷰포트 상태 {x, y, zoom}"
    )

    # Custom Node Positions (main 탭에서는 사용 안 함)
    custom_positions = models.JSONField(
        default=dict,
        blank=True,
        help_text="커스텀 노드 위치 {pageId: {x, y}, ...}"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seo_canvas_tabs'
        ordering = ['domain', 'order']
        indexes = [
            models.Index(fields=['domain', 'order']),
            models.Index(fields=['domain', 'is_active']),
        ]
        verbose_name = 'Canvas Tab'
        verbose_name_plural = 'Canvas Tabs'
        constraints = [
            # 도메인당 main 탭은 하나만
            models.UniqueConstraint(
                fields=['domain'],
                condition=models.Q(is_main=True),
                name='unique_main_tab_per_domain'
            )
        ]

    def __str__(self):
        return f"{self.domain.domain_name} - {self.name}"

    def save(self, *args, **kwargs):
        # 활성 탭 설정 시 같은 도메인의 다른 활성 탭 해제
        if self.is_active:
            CanvasTab.objects.filter(
                domain=self.domain,
                is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_or_create_main_tab(cls, domain):
        """main 탭 가져오거나 생성"""
        tab, created = cls.objects.get_or_create(
            domain=domain,
            is_main=True,
            defaults={
                'name': 'main',
                'order': 0,
                'is_active': True,
            }
        )
        return tab

    def can_edit(self):
        """편집 가능 여부 (main 탭은 편집 불가)"""
        return not self.is_main
