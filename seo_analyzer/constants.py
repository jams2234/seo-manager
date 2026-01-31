"""
SEO Analyzer Constants

Centralized constants for SEO analysis, auto-fix, and verification.
"""

# =============================================================================
# Issue Severity Levels
# =============================================================================
class IssueSeverity:
    CRITICAL = 'critical'
    WARNING = 'warning'
    INFO = 'info'

    CHOICES = [
        (CRITICAL, 'Critical'),
        (WARNING, 'Warning'),
        (INFO, 'Info'),
    ]


# =============================================================================
# Issue Status
# =============================================================================
class IssueStatus:
    OPEN = 'open'
    FIXED = 'fixed'
    IGNORED = 'ignored'
    AUTO_FIXED = 'auto_fixed'

    CHOICES = [
        (OPEN, 'Open'),
        (FIXED, 'Fixed'),
        (IGNORED, 'Ignored'),
        (AUTO_FIXED, 'Auto Fixed'),
    ]

    # Statuses that indicate the issue is resolved
    RESOLVED_STATUSES = [FIXED, AUTO_FIXED]


# =============================================================================
# Verification Status (after Git deployment)
# =============================================================================
class VerificationStatus:
    NOT_DEPLOYED = 'not_deployed'      # 아직 Git 배포 안됨
    PENDING = 'pending'                 # 배포됨, 검증 대기
    VERIFIED = 'verified'               # 검증 완료 (실제 웹사이트에 반영 확인됨)
    NEEDS_ATTENTION = 'needs_attention' # 반영 확인 필요 (아직 문제 있음)

    CHOICES = [
        (NOT_DEPLOYED, 'Not Deployed'),
        (PENDING, 'Pending Verification'),
        (VERIFIED, 'Verified'),
        (NEEDS_ATTENTION, 'Needs Attention'),
    ]

    # Statuses that need user attention
    ATTENTION_REQUIRED = [PENDING, NEEDS_ATTENTION]

    # Statuses that mean verification is not yet done
    UNVERIFIED = [NOT_DEPLOYED, PENDING]


# =============================================================================
# SEO Meta Tag Limits
# =============================================================================
class MetaLimits:
    # Title
    TITLE_MIN_LENGTH = 30
    TITLE_MAX_LENGTH = 60
    TITLE_OPTIMAL_MIN = 50
    TITLE_OPTIMAL_MAX = 60

    # Meta Description
    DESCRIPTION_MIN_LENGTH = 120
    DESCRIPTION_MAX_LENGTH = 160
    DESCRIPTION_OPTIMAL_MIN = 150
    DESCRIPTION_OPTIMAL_MAX = 160

    # OG Tags
    OG_TITLE_MAX_LENGTH = 60
    OG_DESCRIPTION_MAX_LENGTH = 200


# =============================================================================
# Auto-Fix Methods
# =============================================================================
class AutoFixMethod:
    FIX_TITLE = 'fix_title'
    FIX_META_DESCRIPTION = 'fix_meta_description'
    FIX_H1 = 'fix_h1'
    FIX_OG_TITLE = 'fix_og_title'
    FIX_OG_DESCRIPTION = 'fix_og_description'
    FIX_OG_IMAGE = 'fix_og_image'
    FIX_CANONICAL = 'fix_canonical'
    FIX_ROBOTS = 'fix_robots'

    ALL_METHODS = [
        FIX_TITLE,
        FIX_META_DESCRIPTION,
        FIX_H1,
        FIX_OG_TITLE,
        FIX_OG_DESCRIPTION,
        FIX_OG_IMAGE,
        FIX_CANONICAL,
        FIX_ROBOTS,
    ]


# =============================================================================
# Issue Types
# =============================================================================
class IssueType:
    # Title Issues
    TITLE_MISSING = 'title_missing'
    TITLE_TOO_SHORT = 'title_too_short'
    TITLE_TOO_LONG = 'title_too_long'

    # Meta Description Issues
    META_DESCRIPTION_MISSING = 'meta_description_missing'
    META_DESCRIPTION_TOO_SHORT = 'meta_description_too_short'
    META_DESCRIPTION_TOO_LONG = 'meta_description_too_long'

    # Heading Issues
    H1_MISSING = 'h1_missing'
    H1_MULTIPLE = 'h1_multiple'
    H1_TOO_LONG = 'h1_too_long'

    # Open Graph Issues
    OG_TITLE_MISSING = 'og_title_missing'
    OG_DESCRIPTION_MISSING = 'og_description_missing'
    OG_IMAGE_MISSING = 'og_image_missing'

    # Technical Issues
    CANONICAL_MISSING = 'canonical_missing'
    ROBOTS_BLOCKED = 'robots_blocked'
    VIEWPORT_MISSING = 'viewport_missing'

    # Image Issues
    IMAGES_WITHOUT_ALT = 'images_without_alt'


# =============================================================================
# Health Score Thresholds
# =============================================================================
class HealthScoreThreshold:
    EXCELLENT = 90
    GOOD = 70
    FAIR = 50
    POOR = 30

    @classmethod
    def get_grade(cls, score: int) -> str:
        """Get grade label for a given score."""
        if score >= cls.EXCELLENT:
            return 'Excellent'
        elif score >= cls.GOOD:
            return 'Good'
        elif score >= cls.FAIR:
            return 'Fair'
        elif score >= cls.POOR:
            return 'Poor'
        return 'Critical'

    @classmethod
    def get_color(cls, score: int) -> str:
        """Get color code for a given score."""
        if score >= cls.EXCELLENT:
            return '#10b981'  # Green
        elif score >= cls.GOOD:
            return '#22c55e'  # Light green
        elif score >= cls.FAIR:
            return '#f59e0b'  # Yellow
        elif score >= cls.POOR:
            return '#f97316'  # Orange
        return '#ef4444'  # Red
