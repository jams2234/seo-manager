"""
Celery Tasks for SEO Analyzer
"""
import logging
from datetime import datetime, timezone
from celery import shared_task
from django.db import transaction
from .models import Domain, Page, SEOMetrics, HistoricalMetrics
from .services import DomainRefreshService

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def refresh_domain_cache(self, domain_id):
    """
    Background task to refresh all data for a domain

    Args:
        domain_id: ID of the domain to refresh

    Returns:
        dict: Refresh result with pages_discovered, pages_processed, etc.
    """
    try:
        domain = Domain.objects.get(id=domain_id)
        logger.info(f"Starting background scan for domain: {domain.domain_name}")

        # Progress callback for Celery state updates
        def progress_callback(current, total, message):
            """Update Celery task state with progress info"""
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': current,
                    'total': total,
                    'status': message,
                    'percent': int((current / total) * 100) if total > 0 else 0
                }
            )

        # Use DomainRefreshService (max 1000 pages, includes desktop)
        # mobile_only=False: Comprehensive analysis with both mobile and desktop scores
        service = DomainRefreshService(max_pages=1000, max_metrics=100, mobile_only=False)
        result = service.refresh_domain(domain, progress_callback=progress_callback)

        logger.info(
            f"Completed background scan for {domain.domain_name}: "
            f"{result['metrics_fetched']}/{result['pages_discovered']} pages processed"
        )

        return {
            'domain_id': domain_id,
            'domain_name': domain.domain_name,
            'pages_discovered': result['pages_discovered'],
            'pages_processed': result['pages_processed'],
            'metrics_fetched': result['metrics_fetched'],
            'status': 'completed'
        }

    except Domain.DoesNotExist:
        logger.error(f"Domain {domain_id} not found")
        return {
            'error': True,
            'message': f'Domain {domain_id} not found'
        }
    except Exception as e:
        logger.error(f"Error in refresh_domain_cache for domain {domain_id}: {e}")
        return {
            'error': True,
            'message': str(e)
        }


@shared_task
def nightly_cache_update():
    """
    Nightly task to update all active domains
    """
    logger.info("Starting nightly cache update")

    active_domains = Domain.objects.filter(status='active')
    logger.info(f"Found {active_domains.count()} active domains")

    for domain in active_domains:
        try:
            # Trigger individual domain refresh
            refresh_domain_cache.delay(domain.id)
            logger.info(f"Queued refresh for {domain.domain_name}")
        except Exception as e:
            logger.error(f"Failed to queue refresh for {domain.domain_name}: {e}")

    return {
        'status': 'completed',
        'domains_queued': active_domains.count()
    }


@shared_task
def generate_daily_snapshot():
    """
    Generate daily snapshots for historical tracking
    """
    logger.info("Generating daily snapshots")

    snapshot_date = datetime.now(timezone.utc).date()
    created_count = 0

    # Get all active pages with metrics
    pages = Page.objects.filter(status='active').prefetch_related('seo_metrics')

    for page in pages:
        latest_metrics = page.seo_metrics.first()
        if latest_metrics:
            # Check if snapshot already exists for today
            existing = HistoricalMetrics.objects.filter(
                page=page,
                date=snapshot_date
            ).exists()

            if not existing:
                HistoricalMetrics.objects.create(
                    page=page,
                    seo_score=latest_metrics.seo_score,
                    performance_score=latest_metrics.performance_score,
                    accessibility_score=latest_metrics.accessibility_score,
                    avg_position=latest_metrics.avg_position,
                    total_clicks=latest_metrics.clicks,
                    total_impressions=latest_metrics.impressions,
                    date=snapshot_date,
                )
                created_count += 1

    logger.info(f"Created {created_count} daily snapshots")

    return {
        'status': 'completed',
        'snapshots_created': created_count,
        'date': str(snapshot_date)
    }
