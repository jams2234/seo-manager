"""
SEO Analyzer Serializers
"""
from rest_framework import serializers
from .models import (
    Domain,
    Page,
    PageGroup,
    PageGroupCategory,
    SEOMetrics,
    AnalyticsData,
    HistoricalMetrics,
    APIQuotaUsage,
    ScanJob,
    SEOIssue,
    SitemapConfig,
    SitemapHistory,
    SEOAnalysisReport,
    SitemapEntry,
    SitemapEditSession,
    SitemapEntryChange,
    AIAnalysisCache,
    AIConversation,
    AIMessage,
)
from .utils import is_descendant


class SEOMetricsSerializer(serializers.ModelSerializer):
    """Serializer for SEO Metrics"""
    overall_score = serializers.SerializerMethodField()

    class Meta:
        model = SEOMetrics
        fields = [
            'id',
            'seo_score',
            'performance_score',
            'accessibility_score',
            'best_practices_score',
            'pwa_score',
            'overall_score',
            'lcp',
            'fid',
            'cls',
            'fcp',
            'tti',
            'tbt',
            'impressions',
            'clicks',
            'ctr',
            'avg_position',
            'top_queries',
            'is_indexed',
            'index_status',
            'coverage_state',
            'mobile_friendly',
            'mobile_score',
            'desktop_score',
            'snapshot_date',
        ]

    def get_overall_score(self, obj):
        """Calculate weighted overall score"""
        return obj.get_overall_score()


class PageListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for page lists"""
    latest_seo_score = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = [
            'id',
            'url',
            'title',
            'is_subdomain',
            'subdomain',
            'depth_level',
            'status',
            'latest_seo_score',
            'last_analyzed_at',
        ]

    def get_latest_seo_score(self, obj):
        """Get latest SEO score"""
        latest = obj.seo_metrics.first()
        if latest and latest.seo_score:
            return latest.seo_score
        return None


class PageDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual pages"""
    metrics = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = [
            'id',
            'domain',
            'url',
            'path',
            'is_subdomain',
            'subdomain',
            'parent_page',
            'depth_level',
            'title',
            'description',
            'canonical_url',
            'status',
            'http_status_code',
            'last_analyzed_at',
            'cache_expires_at',
            'created_at',
            'updated_at',
            'metrics',
            'children_count',
        ]

    def get_metrics(self, obj):
        """Get latest metrics"""
        latest = obj.seo_metrics.first()
        if latest:
            return SEOMetricsSerializer(latest).data
        return None

    def get_children_count(self, obj):
        """Get number of child pages"""
        return obj.children.count()


class PageUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating page customizations"""

    class Meta:
        model = Page
        fields = [
            'id',
            'manual_position_x',
            'manual_position_y',
            'use_manual_position',
            'custom_label',
            'is_visible',
            'is_collapsed',
            'is_subdomain',
            'parent_page',
            'group',
        ]

    def validate_parent_page(self, value):
        """Validate parent page to prevent circular relationships"""
        if not value:
            return value

        page = self.instance
        if not page:
            return value

        # Cannot be own parent
        if value.id == page.id:
            raise serializers.ValidationError("Page cannot be its own parent")

        # Must be same domain
        if value.domain_id != page.domain_id:
            raise serializers.ValidationError("Parent must be from same domain")

        # Check for circular relationships
        if is_descendant(page, value):
            raise serializers.ValidationError(
                "Cannot create circular parent relationship - target is a descendant"
            )

        return value


class DomainListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for domain lists"""

    class Meta:
        model = Domain
        fields = [
            'id',
            'domain_name',
            'protocol',
            'status',
            'avg_seo_score',
            'avg_performance_score',
            'avg_accessibility_score',
            'avg_pwa_score',
            'total_pages',
            'total_subdomains',
            'search_console_connected',
            'analytics_connected',
            'last_scanned_at',
            'created_at',
            'sitemap_ai_enabled',
        ]


class DomainDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual domains"""

    class Meta:
        model = Domain
        fields = [
            'id',
            'domain_name',
            'protocol',
            'status',
            'last_scanned_at',
            'next_scan_at',
            'search_console_connected',
            'analytics_connected',
            'avg_seo_score',
            'avg_performance_score',
            'avg_accessibility_score',
            'avg_pwa_score',
            'total_pages',
            'total_subdomains',
            'owner',
            'created_at',
            'updated_at',
            # Git & Vercel Deployment
            'git_enabled',
            'git_repository',
            'git_branch',
            'git_token',
            'git_target_path',
            'vercel_project_id',
            'vercel_token',
            'last_deployed_at',
            'deployment_status',
            'last_deployment_error',
            # Sitemap AI
            'sitemap_ai_enabled',
        ]
        # Note: avg_* and total_* fields are model properties/fields, auto-handled by DRF
        read_only_fields = ['last_scanned_at', 'last_deployed_at', 'deployment_status', 'last_deployment_error']
        extra_kwargs = {
            'git_token': {'write_only': True},  # Don't expose token in responses
            'vercel_token': {'write_only': True},  # Don't expose token in responses
        }


class DomainCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating domains"""

    class Meta:
        model = Domain
        fields = ['id', 'domain_name', 'protocol']
        read_only_fields = ['id']

    def validate_domain_name(self, value):
        """Validate domain name"""
        # Remove protocol and www if present
        value = value.lower().strip()
        value = value.replace('http://', '').replace('https://', '')
        value = value.replace('www.', '')

        # Basic validation
        if not value:
            raise serializers.ValidationError("Domain name cannot be empty")

        if ' ' in value:
            raise serializers.ValidationError("Domain name cannot contain spaces")

        # Check if already exists
        if Domain.objects.filter(domain_name=value).exists():
            raise serializers.ValidationError("Domain already exists")

        return value


class TreeNodeSerializer(serializers.Serializer):
    """Serializer for tree structure nodes"""
    id = serializers.IntegerField()
    label = serializers.CharField()
    custom_label = serializers.CharField(allow_null=True, required=False)
    url = serializers.CharField()
    path = serializers.CharField(allow_null=True, required=False)
    seo_score = serializers.FloatField(allow_null=True)
    performance_score = serializers.FloatField(allow_null=True)
    accessibility_score = serializers.FloatField(allow_null=True)
    total_pages = serializers.IntegerField()
    is_subdomain = serializers.BooleanField()
    is_visible = serializers.BooleanField(default=True)
    status = serializers.CharField()
    depth_level = serializers.IntegerField(default=0)
    position = serializers.DictField()
    group = serializers.DictField(allow_null=True, required=False)
    # Index status from Search Console
    is_indexed = serializers.BooleanField(default=False)
    index_status = serializers.CharField(allow_null=True, required=False)
    coverage_state = serializers.CharField(allow_null=True, required=False)
    # Search Console analytics
    avg_position = serializers.FloatField(allow_null=True, required=False)
    impressions = serializers.IntegerField(allow_null=True, required=False)
    clicks = serializers.IntegerField(allow_null=True, required=False)
    ctr = serializers.FloatField(allow_null=True, required=False)
    top_queries = serializers.ListField(allow_null=True, required=False)
    # Sitemap mismatch tracking
    sitemap_url = serializers.CharField(allow_null=True, required=False)
    has_sitemap_mismatch = serializers.BooleanField(default=False)
    redirect_chain = serializers.ListField(allow_null=True, required=False)
    sitemap_entry = serializers.JSONField(allow_null=True, required=False)
    # Canonical URL index status (when different from sitemap URL)
    canonical_is_indexed = serializers.BooleanField(allow_null=True, required=False)
    canonical_index_status = serializers.CharField(allow_null=True, required=False)
    canonical_coverage_state = serializers.CharField(allow_null=True, required=False)


class TreeEdgeSerializer(serializers.Serializer):
    """Serializer for tree structure edges"""
    source = serializers.IntegerField()
    target = serializers.IntegerField()


class TreeStructureSerializer(serializers.Serializer):
    """Serializer for complete tree structure"""
    nodes = TreeNodeSerializer(many=True)
    edges = TreeEdgeSerializer(many=True)


class HistoricalMetricsSerializer(serializers.ModelSerializer):
    """Serializer for Historical Metrics"""

    class Meta:
        model = HistoricalMetrics
        fields = [
            'id',
            'page',
            'seo_score',
            'performance_score',
            'accessibility_score',
            'avg_position',
            'total_clicks',
            'total_impressions',
            'date',
            'created_at',
        ]


class PageGroupCategorySerializer(serializers.ModelSerializer):
    """Serializer for PageGroupCategory"""
    group_count = serializers.SerializerMethodField()
    page_count = serializers.SerializerMethodField()

    class Meta:
        model = PageGroupCategory
        fields = [
            'id',
            'domain',
            'name',
            'description',
            'icon',
            'order',
            'is_expanded',
            'group_count',
            'page_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_group_count(self, obj):
        """Get number of groups in this category (uses annotation if available)"""
        # Use annotated value if available (avoids N+1 query)
        if hasattr(obj, 'annotated_group_count'):
            return obj.annotated_group_count
        return obj.groups.count()

    def get_page_count(self, obj):
        """Get total number of pages in all groups in this category (uses annotation if available)"""
        # Use annotated value if available (avoids N+1 query)
        if hasattr(obj, 'annotated_page_count'):
            return obj.annotated_page_count
        # Fallback: This triggers N+1 queries but works without annotation
        return sum(group.pages.count() for group in obj.groups.all())


class PageGroupSerializer(serializers.ModelSerializer):
    """Serializer for PageGroup"""
    page_count = serializers.SerializerMethodField()
    avg_seo_score = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True, allow_null=True)

    class Meta:
        model = PageGroup
        fields = [
            'id',
            'domain',
            'category',
            'category_name',
            'category_icon',
            'name',
            'color',
            'description',
            'order',
            'page_count',
            'avg_seo_score',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_page_count(self, obj):
        """Get number of pages in this group (uses annotation if available)"""
        # Use annotated value if available (avoids N+1 query)
        if hasattr(obj, 'annotated_page_count'):
            return obj.annotated_page_count
        return obj.pages.count()

    def get_avg_seo_score(self, obj):
        """Get average SEO score of pages in this group (uses annotation if available)"""
        # Use annotated value if available (avoids N+1 query)
        if hasattr(obj, 'annotated_avg_seo_score'):
            return obj.annotated_avg_seo_score
        return obj.avg_seo_score

    def validate_color(self, value):
        """Validate hex color format"""
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', value):
            raise serializers.ValidationError("Color must be a valid hex color code (e.g., #FF5733)")
        return value


# ============================================================================
# AI SEO Advisor Serializers (Day 1 Models)
# ============================================================================

class SEOIssueSerializer(serializers.ModelSerializer):
    """Serializer for SEO Issues"""
    page_url = serializers.CharField(source='page.url', read_only=True)
    page_title = serializers.CharField(source='page.title', read_only=True)

    class Meta:
        model = SEOIssue
        fields = [
            'id', 'page', 'page_url', 'page_title',
            'issue_type', 'severity', 'status',
            'title', 'message', 'fix_suggestion',
            'auto_fix_available', 'auto_fix_method',
            'impact', 'current_value', 'suggested_value',
            'extra_data', 'detected_at', 'fixed_at',
            'deployed_to_git', 'deployed_at', 'deployment_commit_hash',
            # AI Fix fields
            'ai_fix_generated', 'ai_fix_generated_at',
            'ai_fix_confidence', 'ai_fix_explanation',
        ]
        read_only_fields = [
            'id', 'detected_at', 'page_url', 'page_title',
            'deployed_to_git', 'deployed_at', 'deployment_commit_hash',
            'ai_fix_generated', 'ai_fix_generated_at',
        ]


class SEOIssueListSerializer(serializers.ModelSerializer):
    """Serializer for listing issues with all necessary fields for UI"""
    page_url = serializers.CharField(source='page.url', read_only=True)

    class Meta:
        model = SEOIssue
        fields = [
            'id', 'page', 'page_url',
            'issue_type', 'severity', 'status',
            'title', 'message', 'fix_suggestion',
            'auto_fix_available', 'auto_fix_method',
            'current_value', 'suggested_value',
            'deployed_to_git', 'deployed_at', 'deployment_commit_hash',
            'verification_status', 'verified_at',
            'detected_at', 'fixed_at',
            # AI Fix fields
            'ai_fix_generated', 'ai_fix_generated_at',
            'ai_fix_confidence', 'ai_fix_explanation',
        ]


class SitemapConfigSerializer(serializers.ModelSerializer):
    """Serializer for Sitemap Configuration"""
    domain_name = serializers.CharField(source='domain.domain_name', read_only=True)

    class Meta:
        model = SitemapConfig
        fields = [
            'id', 'domain', 'domain_name',
            'existing_sitemap_url', 'include_images',
            'deployment_method', 'deployment_config',
            'auto_generate', 'auto_deploy',
            'auto_submit_to_search_console',
            'last_generated_at', 'last_deployed_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'domain_name', 'last_generated_at',
            'last_deployed_at', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'deployment_config': {'write_only': True}
        }


class SitemapHistorySerializer(serializers.ModelSerializer):
    """Serializer for Sitemap History"""
    domain_name = serializers.CharField(source='domain.domain_name', read_only=True)

    class Meta:
        model = SitemapHistory
        fields = [
            'id', 'domain', 'domain_name',
            'url_count', 'file_size_bytes', 'sitemap_url',
            'generated', 'deployed', 'submitted_to_search_console',
            'validation_errors', 'validation_warnings',
            'created_at'
        ]
        read_only_fields = ['id', 'domain_name', 'created_at']


class SEOAnalysisReportSerializer(serializers.ModelSerializer):
    """Serializer for SEO Analysis Reports"""
    domain_name = serializers.CharField(source='domain.domain_name', read_only=True)
    page_url = serializers.CharField(source='page.url', read_only=True, allow_null=True)

    class Meta:
        model = SEOAnalysisReport
        fields = [
            'id', 'domain', 'domain_name', 'page', 'page_url',
            'report_type', 'overall_health_score',
            'critical_issues_count', 'warning_issues_count', 'info_issues_count',
            'auto_fixable_count', 'fixed_count',
            'issues', 'action_plan', 'auto_fix_results',
            'potential_score_gain', 'estimated_fix_time_minutes',
            'analyzed_at'
        ]
        read_only_fields = ['id', 'domain_name', 'page_url', 'analyzed_at']


class SEOAnalysisReportListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing reports"""
    domain_name = serializers.CharField(source='domain.domain_name', read_only=True)
    page_url = serializers.CharField(source='page.url', read_only=True, allow_null=True)

    class Meta:
        model = SEOAnalysisReport
        fields = [
            'id', 'domain_name', 'page_url', 'report_type',
            'overall_health_score', 'critical_issues_count',
            'warning_issues_count', 'auto_fixable_count',
            'analyzed_at'
        ]


# Action Serializers (for custom actions)

class AnalyzePageSerializer(serializers.Serializer):
    """Serializer for page analysis request"""
    include_content_analysis = serializers.BooleanField(default=True)
    target_keywords = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )


class AutoFixIssueSerializer(serializers.Serializer):
    """Serializer for auto-fix request"""
    issue_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of issue IDs to fix. If not provided, fixes all auto-fixable issues for the page."
    )
    dry_run = serializers.BooleanField(
        default=False,
        help_text="If true, simulates the fix without actually applying it"
    )


class GenerateSitemapSerializer(serializers.Serializer):
    """Serializer for sitemap generation request"""
    domain_id = serializers.IntegerField()
    include_images = serializers.BooleanField(default=True)
    auto_deploy = serializers.BooleanField(default=False)
    auto_submit = serializers.BooleanField(default=False)


class ImportSitemapSerializer(serializers.Serializer):
    """Serializer for importing existing sitemap"""
    domain_id = serializers.IntegerField()
    sitemap_url = serializers.URLField(
        help_text="URL of the existing sitemap to import"
    )
    merge_with_existing = serializers.BooleanField(
        default=False,
        help_text="If true, merges with existing pages. If false, replaces them."
    )


class DeploySitemapSerializer(serializers.Serializer):
    """Serializer for sitemap deployment request"""
    config_id = serializers.IntegerField()
    submit_to_search_console = serializers.BooleanField(default=False)


class PageWithSEOIssuesSerializer(serializers.ModelSerializer):
    """Page serializer with SEO issues and latest analysis"""
    latest_analysis = serializers.SerializerMethodField()
    open_issues_count = serializers.SerializerMethodField()
    critical_issues_count = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = [
            'id', 'url', 'title', 'depth_level', 'status',
            'last_analyzed_at',
            'latest_analysis', 'open_issues_count', 'critical_issues_count'
        ]

    def get_latest_analysis(self, obj):
        latest = obj.seo_reports.first()
        if latest:
            return SEOAnalysisReportListSerializer(latest).data
        return None

    def get_open_issues_count(self, obj):
        return obj.seo_issues.filter(status='open').count()

    def get_critical_issues_count(self, obj):
        return obj.seo_issues.filter(status='open', severity='critical').count()


# =============================================================================
# Sitemap Editor Serializers
# =============================================================================

class SitemapEntrySerializer(serializers.ModelSerializer):
    """Serializer for SitemapEntry model"""
    page_id = serializers.IntegerField(source='page.id', read_only=True, allow_null=True)
    page_url = serializers.CharField(source='page.url', read_only=True, allow_null=True)

    class Meta:
        model = SitemapEntry
        fields = [
            'id',
            'domain',
            'page_id',
            'page_url',
            'loc',
            'lastmod',
            'changefreq',
            'priority',
            'status',
            'is_valid',
            'validation_errors',
            'ai_suggested',
            'ai_suggestion_reason',
            'ai_analysis_enabled',
            'http_status_code',
            'redirect_url',
            'last_checked_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'domain', 'loc_hash', 'created_at', 'updated_at']


class SitemapEntryCreateSerializer(serializers.Serializer):
    """Serializer for creating sitemap entries"""
    loc = serializers.URLField(max_length=2048, help_text="URL location")
    lastmod = serializers.DateField(required=False, allow_null=True, help_text="Last modification date")
    changefreq = serializers.ChoiceField(
        choices=['always', 'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'never'],
        required=False,
        allow_null=True,
        help_text="Change frequency"
    )
    priority = serializers.DecimalField(
        max_digits=2,
        decimal_places=1,
        required=False,
        allow_null=True,
        min_value=0.0,
        max_value=1.0,
        help_text="Priority (0.0-1.0)"
    )
    session_id = serializers.IntegerField(help_text="Edit session ID")


class SitemapEntryUpdateSerializer(serializers.Serializer):
    """Serializer for updating sitemap entries"""
    loc = serializers.URLField(max_length=2048, required=False)
    lastmod = serializers.DateField(required=False, allow_null=True)
    changefreq = serializers.ChoiceField(
        choices=['always', 'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'never'],
        required=False,
        allow_null=True,
    )
    priority = serializers.DecimalField(
        max_digits=2,
        decimal_places=1,
        required=False,
        allow_null=True,
        min_value=0.0,
        max_value=1.0,
    )
    session_id = serializers.IntegerField(help_text="Edit session ID")


class SitemapEditSessionSerializer(serializers.ModelSerializer):
    """Serializer for SitemapEditSession model"""
    domain_name = serializers.CharField(source='domain.domain_name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    changes_summary = serializers.SerializerMethodField()

    class Meta:
        model = SitemapEditSession
        fields = [
            'id',
            'domain',
            'domain_name',
            'created_by',
            'created_by_username',
            'name',
            'status',
            'entries_added',
            'entries_removed',
            'entries_modified',
            'total_entries',
            'changes_summary',
            'ai_issues_found',
            'ai_suggestions',
            'ai_analysis_completed_at',
            'deployment_commit_hash',
            'deployment_message',
            'deployment_error',
            'deployed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'entries_added', 'entries_removed', 'entries_modified',
            'deployment_commit_hash', 'deployed_at', 'created_at', 'updated_at'
        ]

    def get_changes_summary(self, obj):
        return obj.get_changes_summary()


class SitemapEditSessionCreateSerializer(serializers.Serializer):
    """Serializer for creating edit sessions"""
    domain_id = serializers.IntegerField(help_text="Domain ID")
    name = serializers.CharField(max_length=200, required=False, allow_blank=True)


class SitemapEntryChangeSerializer(serializers.ModelSerializer):
    """Serializer for SitemapEntryChange model"""
    changed_by_username = serializers.CharField(source='changed_by.username', read_only=True, allow_null=True)
    diff = serializers.SerializerMethodField()

    class Meta:
        model = SitemapEntryChange
        fields = [
            'id',
            'session',
            'entry',
            'change_type',
            'source',
            'url',
            'old_values',
            'new_values',
            'diff',
            'ai_reason',
            'changed_by',
            'changed_by_username',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_diff(self, obj):
        return obj.get_diff()


class SitemapPreviewSerializer(serializers.Serializer):
    """Serializer for sitemap preview response"""
    xml_content = serializers.CharField()
    url_count = serializers.IntegerField()
    size_bytes = serializers.IntegerField()
    generated_at = serializers.DateTimeField()


class SitemapDeployRequestSerializer(serializers.Serializer):
    """Serializer for sitemap deployment request"""
    session_id = serializers.IntegerField(help_text="Edit session ID")
    commit_message = serializers.CharField(max_length=500, required=False, allow_blank=True)


class SitemapSyncRequestSerializer(serializers.Serializer):
    """Serializer for sitemap sync request"""
    domain_id = serializers.IntegerField(help_text="Domain ID")
    sitemap_url = serializers.URLField(required=False, allow_blank=True, help_text="Optional sitemap URL")


class SitemapValidationResultSerializer(serializers.Serializer):
    """Serializer for validation result"""
    valid = serializers.BooleanField()
    entry_count = serializers.IntegerField()
    invalid_count = serializers.IntegerField()
    issues = serializers.ListField(child=serializers.CharField())
    warnings = serializers.ListField(child=serializers.CharField())


class SitemapDiffSerializer(serializers.Serializer):
    """Serializer for session diff"""
    session_id = serializers.IntegerField()
    session_name = serializers.CharField()
    diff = serializers.DictField()
    summary = serializers.DictField()


class BulkEntryImportSerializer(serializers.Serializer):
    """Serializer for bulk entry import"""
    session_id = serializers.IntegerField()
    entries = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of entry objects with loc, lastmod, changefreq, priority"
    )


# =============================================================================
# AI Conversation Serializers
# =============================================================================

class AIMessageSerializer(serializers.ModelSerializer):
    """Serializer for AI message"""

    class Meta:
        model = AIMessage
        fields = [
            'id',
            'role',
            'message_type',
            'content',
            'structured_data',
            'input_tokens',
            'output_tokens',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class AIConversationSerializer(serializers.ModelSerializer):
    """Serializer for AI conversation"""
    domain_name = serializers.CharField(source='domain.domain_name', read_only=True, allow_null=True)
    messages = AIMessageSerializer(many=True, read_only=True)
    message_count = serializers.IntegerField(source='total_messages', read_only=True)

    class Meta:
        model = AIConversation
        fields = [
            'id',
            'domain',
            'domain_name',
            'title',
            'conversation_type',
            'status',
            'total_messages',
            'message_count',
            'total_tokens_used',
            'created_at',
            'updated_at',
            'last_message_at',
            'messages',
        ]
        read_only_fields = ['id', 'total_messages', 'total_tokens_used', 'created_at', 'updated_at', 'last_message_at']


class AIConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing conversations"""
    domain_name = serializers.CharField(source='domain.domain_name', read_only=True, allow_null=True)
    last_message_preview = serializers.SerializerMethodField()

    class Meta:
        model = AIConversation
        fields = [
            'id',
            'domain',
            'domain_name',
            'title',
            'conversation_type',
            'status',
            'total_messages',
            'created_at',
            'updated_at',
            'last_message_at',
            'last_message_preview',
        ]

    def get_last_message_preview(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            content = last_msg.content
            return content[:100] + '...' if len(content) > 100 else content
        return None


class AIConversationCreateSerializer(serializers.Serializer):
    """Serializer for creating a new conversation"""
    domain_id = serializers.IntegerField(required=False, allow_null=True, help_text="Domain ID (optional)")
    conversation_type = serializers.ChoiceField(
        choices=AIConversation.CONVERSATION_TYPES,
        default='general'
    )
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    initial_message = serializers.CharField(required=False, allow_blank=True, help_text="Optional initial user message")


class AIChatRequestSerializer(serializers.Serializer):
    """Serializer for sending a chat message"""
    conversation_id = serializers.IntegerField(help_text="Conversation ID")
    message = serializers.CharField(help_text="User message")
    include_context = serializers.BooleanField(
        default=True,
        help_text="Whether to include domain/sitemap context in the AI prompt"
    )


class AIAnalyzeRequestSerializer(serializers.Serializer):
    """Serializer for analysis request with conversation tracking"""
    domain_id = serializers.IntegerField(help_text="Domain ID to analyze")
    analysis_type = serializers.ChoiceField(
        choices=['sitemap', 'seo_issues', 'full_report'],
        help_text="Type of analysis to perform"
    )
    conversation_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Existing conversation ID (creates new if not provided)"
    )
