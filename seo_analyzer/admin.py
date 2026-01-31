"""
Django Admin Configuration for SEO Analyzer
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Domain,
    Page,
    SEOMetrics,
    AnalyticsData,
    HistoricalMetrics,
    APIQuotaUsage,
    ScanJob,
    SEOIssue,
    SitemapConfig,
    SitemapHistory,
    SEOAnalysisReport
)


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = [
        'domain_name',
        'protocol',
        'status_badge',
        'avg_seo_score_colored',
        'total_pages',
        'total_subdomains',
        'last_scanned_at',
        'created_at'
    ]
    list_filter = ['status', 'protocol', 'search_console_connected', 'analytics_connected']
    search_fields = ['domain_name']
    readonly_fields = [
        'created_at',
        'updated_at',
        'last_scanned_at',
        'total_pages',
        'total_subdomains'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('domain_name', 'protocol', 'status', 'owner')
        }),
        ('Google API Connections', {
            'fields': ('search_console_connected', 'analytics_connected')
        }),
        ('Aggregated Scores', {
            'fields': (
                'avg_seo_score',
                'avg_performance_score',
                'avg_accessibility_score',
                'avg_pwa_score'
            )
        }),
        ('Statistics', {
            'fields': ('total_pages', 'total_subdomains')
        }),
        ('Timestamps', {
            'fields': ('last_scanned_at', 'next_scan_at', 'created_at', 'updated_at')
        }),
    )

    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'active': 'green',
            'paused': 'orange',
            'error': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def avg_seo_score_colored(self, obj):
        """Display SEO score with color coding."""
        if obj.avg_seo_score is None:
            return '-'

        score = obj.avg_seo_score
        if score >= 90:
            color = 'green'
        elif score >= 70:
            color = 'orange'
        else:
            color = 'red'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            f'{score:.1f}'
        )
    avg_seo_score_colored.short_description = 'Avg SEO Score'


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = [
        'url',
        'domain',
        'status_badge',
        'is_subdomain',
        'depth_level',
        'latest_seo_score',
        'last_analyzed_at'
    ]
    list_filter = ['status', 'is_subdomain', 'domain', 'depth_level']
    search_fields = ['url', 'title', 'domain__domain_name']
    raw_id_fields = ['domain', 'parent_page']
    readonly_fields = ['created_at', 'updated_at', 'last_analyzed_at', 'cache_expires_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('domain', 'url', 'path')
        }),
        ('Subdomain Information', {
            'fields': ('is_subdomain', 'subdomain', 'parent_page', 'depth_level')
        }),
        ('Page Metadata', {
            'fields': ('title', 'description', 'canonical_url')
        }),
        ('Status', {
            'fields': ('status', 'http_status_code')
        }),
        ('Cache', {
            'fields': ('last_analyzed_at', 'cache_expires_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'active': 'green',
            '404': 'red',
            '500': 'red',
            'redirected': 'orange',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def latest_seo_score(self, obj):
        """Display latest SEO score."""
        latest = obj.seo_metrics.first()
        if latest and latest.seo_score:
            score = latest.seo_score
            if score >= 90:
                color = 'green'
            elif score >= 70:
                color = 'orange'
            else:
                color = 'red'
            return format_html(
                '<span style="color: {};">{}</span>',
                color,
                f'{score:.1f}'
            )
        return '-'
    latest_seo_score.short_description = 'Latest SEO Score'


@admin.register(SEOMetrics)
class SEOMetricsAdmin(admin.ModelAdmin):
    list_display = [
        'page',
        'seo_score_colored',
        'performance_score_colored',
        'accessibility_score_colored',
        'is_indexed',
        'avg_position',
        'snapshot_date'
    ]
    list_filter = ['is_indexed', 'mobile_friendly', 'snapshot_date']
    search_fields = ['page__url']
    raw_id_fields = ['page']
    readonly_fields = ['snapshot_date']

    fieldsets = (
        ('Page', {
            'fields': ('page',)
        }),
        ('Lighthouse Scores', {
            'fields': (
                'seo_score',
                'performance_score',
                'accessibility_score',
                'best_practices_score',
                'pwa_score'
            )
        }),
        ('Core Web Vitals', {
            'fields': ('lcp', 'fid', 'cls', 'fcp', 'tti', 'tbt')
        }),
        ('Search Console Metrics', {
            'fields': ('impressions', 'clicks', 'ctr', 'avg_position')
        }),
        ('Indexing', {
            'fields': ('is_indexed', 'index_status', 'coverage_state')
        }),
        ('Mobile', {
            'fields': ('mobile_friendly', 'mobile_score', 'desktop_score')
        }),
        ('Snapshot', {
            'fields': ('snapshot_date',)
        }),
    )

    def seo_score_colored(self, obj):
        return self._colored_score(obj.seo_score)
    seo_score_colored.short_description = 'SEO Score'

    def performance_score_colored(self, obj):
        return self._colored_score(obj.performance_score)
    performance_score_colored.short_description = 'Performance'

    def accessibility_score_colored(self, obj):
        return self._colored_score(obj.accessibility_score)
    accessibility_score_colored.short_description = 'Accessibility'

    @staticmethod
    def _colored_score(score):
        """Helper to display colored scores."""
        if score is None:
            return '-'
        if score >= 90:
            color = 'green'
        elif score >= 70:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            f'{score:.1f}'
        )


@admin.register(AnalyticsData)
class AnalyticsDataAdmin(admin.ModelAdmin):
    list_display = [
        'page',
        'page_views',
        'sessions',
        'bounce_rate',
        'date_range',
        'snapshot_date'
    ]
    list_filter = ['date_from', 'date_to', 'snapshot_date']
    search_fields = ['page__url']
    raw_id_fields = ['page']
    readonly_fields = ['snapshot_date']

    fieldsets = (
        ('Page', {
            'fields': ('page',)
        }),
        ('Traffic Metrics', {
            'fields': (
                'page_views',
                'unique_visitors',
                'sessions',
                'avg_session_duration',
                'bounce_rate'
            )
        }),
        ('Engagement', {
            'fields': (
                'pages_per_session',
                'new_users',
                'returning_users'
            )
        }),
        ('Conversions', {
            'fields': ('goal_completions', 'conversion_rate')
        }),
        ('Traffic Sources', {
            'fields': (
                'organic_traffic',
                'direct_traffic',
                'referral_traffic',
                'social_traffic'
            )
        }),
        ('Date Range', {
            'fields': ('date_from', 'date_to', 'snapshot_date')
        }),
    )

    def date_range(self, obj):
        return f"{obj.date_from} to {obj.date_to}"
    date_range.short_description = 'Date Range'


@admin.register(HistoricalMetrics)
class HistoricalMetricsAdmin(admin.ModelAdmin):
    list_display = [
        'page',
        'date',
        'seo_score',
        'performance_score',
        'avg_position',
        'total_clicks'
    ]
    list_filter = ['date']
    search_fields = ['page__url']
    raw_id_fields = ['page']
    readonly_fields = ['created_at']
    date_hierarchy = 'date'


@admin.register(APIQuotaUsage)
class APIQuotaUsageAdmin(admin.ModelAdmin):
    list_display = [
        'api_name',
        'date',
        'requests_made',
        'quota_limit',
        'quota_remaining',
        'usage_percentage',
        'rate_limit_hits',
        'error_count'
    ]
    list_filter = ['api_name', 'date']
    readonly_fields = ['date']
    date_hierarchy = 'date'

    def usage_percentage(self, obj):
        """Display quota usage percentage."""
        if not obj.quota_limit:
            return '-'
        percentage = (obj.requests_made / obj.quota_limit) * 100
        if percentage >= 80:
            color = 'red'
        elif percentage >= 60:
            color = 'orange'
        else:
            color = 'green'
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            f'{percentage:.1f}%'
        )
    usage_percentage.short_description = 'Usage %'


@admin.register(ScanJob)
class ScanJobAdmin(admin.ModelAdmin):
    list_display = [
        'domain',
        'job_type',
        'status_badge',
        'progress_bar',
        'pages_scanned',
        'total_pages',
        'started_at',
        'completed_at'
    ]
    list_filter = ['job_type', 'status', 'started_at', 'completed_at']
    search_fields = ['domain__domain_name', 'celery_task_id']
    raw_id_fields = ['domain']
    readonly_fields = [
        'celery_task_id',
        'progress_percent',
        'pages_scanned',
        'started_at',
        'completed_at',
        'created_at'
    ]

    fieldsets = (
        ('Job Information', {
            'fields': ('domain', 'job_type', 'status')
        }),
        ('Celery Task', {
            'fields': ('celery_task_id',)
        }),
        ('Progress', {
            'fields': (
                'progress_percent',
                'pages_scanned',
                'total_pages'
            )
        }),
        ('Results', {
            'fields': ('result_summary', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at')
        }),
    )

    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'pending': 'gray',
            'running': 'blue',
            'completed': 'green',
            'failed': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def progress_bar(self, obj):
        """Display progress as HTML bar."""
        if obj.progress_percent == 0:
            return '-'
        return format_html(
            '<div style="width:100px; background-color:#f0f0f0; border:1px solid #ccc;">'
            '<div style="width:{}%; background-color:green; height:20px; text-align:center; color:white;">'
            '{}%'
            '</div></div>',
            obj.progress_percent,
            obj.progress_percent
        )
    progress_bar.short_description = 'Progress'


# ============================================================================
# AI SEO Advisor Admin (Day 2)
# ============================================================================

@admin.register(SEOIssue)
class SEOIssueAdmin(admin.ModelAdmin):
    """Admin for SEO Issues"""
    list_display = [
        'id',
        'page_link',
        'severity_badge',
        'status_badge',
        'title',
        'auto_fix_badge',
        'detected_at'
    ]
    list_filter = ['severity', 'status', 'auto_fix_available', 'issue_type', 'detected_at']
    search_fields = ['title', 'message', 'page__url']
    raw_id_fields = ['page']
    readonly_fields = ['detected_at', 'fixed_at']
    date_hierarchy = 'detected_at'

    fieldsets = (
        ('Issue Information', {
            'fields': ('page', 'issue_type', 'severity', 'status')
        }),
        ('Details', {
            'fields': ('title', 'message', 'fix_suggestion')
        }),
        ('Auto-Fix', {
            'fields': ('auto_fix_available', 'auto_fix_method')
        }),
        ('Impact & Values', {
            'fields': ('impact', 'current_value', 'suggested_value')
        }),
        ('Extra Data', {
            'fields': ('extra_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('detected_at', 'fixed_at')
        }),
    )

    def page_link(self, obj):
        """Display page URL as link"""
        return format_html('<a href="{}" target="_blank">{}</a>', obj.page.url, obj.page.url[:50])
    page_link.short_description = 'Page'

    def severity_badge(self, obj):
        """Display severity as colored badge"""
        colors = {
            'critical': 'red',
            'warning': 'orange',
            'info': 'blue',
        }
        color = colors.get(obj.severity, 'gray')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_severity_display().upper()
        )
    severity_badge.short_description = 'Severity'

    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'open': 'red',
            'fixed': 'green',
            'ignored': 'gray',
            'auto_fixed': 'blue',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def auto_fix_badge(self, obj):
        """Display auto-fix availability"""
        if obj.auto_fix_available:
            return format_html('<span style="color: green;">✓ Yes</span>')
        return format_html('<span style="color: gray;">✗ No</span>')
    auto_fix_badge.short_description = 'Auto-Fix'


@admin.register(SitemapConfig)
class SitemapConfigAdmin(admin.ModelAdmin):
    """Admin for Sitemap Configuration"""
    list_display = [
        'id',
        'domain',
        'deployment_method',
        'auto_generate',
        'auto_deploy',
        'auto_submit_to_search_console',
        'last_generated_at'
    ]
    list_filter = ['deployment_method', 'auto_generate', 'auto_deploy', 'auto_submit_to_search_console']
    search_fields = ['domain__domain_name']
    raw_id_fields = ['domain']
    readonly_fields = ['last_generated_at', 'last_deployed_at', 'created_at', 'updated_at']

    fieldsets = (
        ('Domain', {
            'fields': ('domain',)
        }),
        ('Sitemap Settings', {
            'fields': (
                'existing_sitemap_url',
                'include_images',
                'max_urls_per_sitemap',
                'update_frequency'
            )
        }),
        ('Deployment', {
            'fields': (
                'deployment_method',
                'deployment_path',
                'deployment_credentials',
                'auto_deploy',
                'auto_submit_to_search_console'
            )
        }),
        ('Status', {
            'fields': ('last_generated_at', 'last_deployed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(SitemapHistory)
class SitemapHistoryAdmin(admin.ModelAdmin):
    """Admin for Sitemap History"""
    list_display = [
        'id',
        'domain',
        'url_count',
        'file_size_kb',
        'generated_badge',
        'deployed_badge',
        'submitted_badge',
        'created_at'
    ]
    list_filter = ['generated', 'deployed', 'submitted_to_search_console', 'created_at']
    search_fields = ['domain__domain_name', 'sitemap_url']
    raw_id_fields = ['domain']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Domain', {
            'fields': ('domain',)
        }),
        ('Sitemap Info', {
            'fields': ('url_count', 'file_size_bytes', 'sitemap_url')
        }),
        ('Status', {
            'fields': ('generated', 'deployed', 'submitted_to_search_console')
        }),
        ('Validation', {
            'fields': ('validation_errors', 'validation_warnings'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )

    def file_size_kb(self, obj):
        """Display file size in KB"""
        if obj.file_size_bytes:
            kb = obj.file_size_bytes / 1024
            return f"{kb:.1f} KB"
        return '-'
    file_size_kb.short_description = 'File Size'

    def generated_badge(self, obj):
        return self._boolean_badge(obj.generated)
    generated_badge.short_description = 'Generated'

    def deployed_badge(self, obj):
        return self._boolean_badge(obj.deployed)
    deployed_badge.short_description = 'Deployed'

    def submitted_badge(self, obj):
        return self._boolean_badge(obj.submitted_to_search_console)
    submitted_badge.short_description = 'Submitted'

    @staticmethod
    def _boolean_badge(value):
        """Helper for boolean badges"""
        if value:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: gray;">✗</span>')


@admin.register(SEOAnalysisReport)
class SEOAnalysisReportAdmin(admin.ModelAdmin):
    """Admin for SEO Analysis Reports"""
    list_display = [
        'id',
        'domain',
        'page_link',
        'report_type',
        'health_score_badge',
        'critical_issues',
        'warning_issues',
        'auto_fixable_count',
        'analyzed_at'
    ]
    list_filter = ['report_type', 'analyzed_at']
    search_fields = ['domain__domain_name', 'page__url']
    raw_id_fields = ['domain', 'page']
    readonly_fields = ['analyzed_at']
    date_hierarchy = 'analyzed_at'

    fieldsets = (
        ('Report Info', {
            'fields': ('domain', 'page', 'report_type')
        }),
        ('Health Scores', {
            'fields': (
                'overall_health_score',
                'potential_score_gain',
                'estimated_fix_time_minutes'
            )
        }),
        ('Issue Counts', {
            'fields': (
                'critical_issues_count',
                'warning_issues_count',
                'info_issues_count',
                'auto_fixable_count',
                'fixed_count'
            )
        }),
        ('Detailed Data', {
            'fields': ('issues', 'action_plan', 'auto_fix_results'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('analyzed_at',)
        }),
    )

    def page_link(self, obj):
        """Display page URL as link"""
        if obj.page:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.page.url, obj.page.url[:50])
        return '-'
    page_link.short_description = 'Page'

    def health_score_badge(self, obj):
        """Display health score with color coding"""
        score = obj.overall_health_score
        if score >= 80:
            color = 'green'
        elif score >= 60:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            score
        )
    health_score_badge.short_description = 'Health Score'

    def critical_issues(self, obj):
        """Display critical issues count"""
        if obj.critical_issues_count > 0:
            return format_html('<span style="color: red; font-weight: bold;">{}</span>', obj.critical_issues_count)
        return format_html('<span style="color: green;">0</span>')
    critical_issues.short_description = 'Critical'

    def warning_issues(self, obj):
        """Display warning issues count"""
        if obj.warning_issues_count > 0:
            return format_html('<span style="color: orange; font-weight: bold;">{}</span>', obj.warning_issues_count)
        return format_html('<span style="color: green;">0</span>')
    warning_issues.short_description = 'Warnings'
