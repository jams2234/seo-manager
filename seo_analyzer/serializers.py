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
    SEOAnalysisReport
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
        """Get number of groups in this category"""
        return obj.groups.count()

    def get_page_count(self, obj):
        """Get total number of pages in all groups in this category"""
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
        """Get number of pages in this group"""
        return obj.pages.count()

    def get_avg_seo_score(self, obj):
        """Get average SEO score of pages in this group"""
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
            'deployed_to_git', 'deployed_at', 'deployment_commit_hash'
        ]
        read_only_fields = ['id', 'detected_at', 'page_url', 'page_title', 'deployed_to_git', 'deployed_at', 'deployment_commit_hash']


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
            'verification_status', 'verified_at',  # 검증 상태 필드 추가
            'detected_at', 'fixed_at'
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
