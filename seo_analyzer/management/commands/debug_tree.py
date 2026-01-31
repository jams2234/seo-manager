"""
Debug Tree Structure
"""
from django.core.management.base import BaseCommand
from seo_analyzer.models import Domain, Page


class Command(BaseCommand):
    help = 'Debug tree structure for a domain'

    def add_arguments(self, parser):
        parser.add_argument('domain_id', type=int, help='Domain ID to debug')

    def handle(self, *args, **options):
        domain_id = options['domain_id']

        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Domain {domain_id} not found'))
            return

        self.stdout.write(f"\nDomain: {domain.domain_name}")
        self.stdout.write("=" * 80)

        # Get all pages
        pages = Page.objects.filter(domain=domain).order_by('depth_level', 'url')

        self.stdout.write(f"\nTotal pages: {pages.count()}")
        self.stdout.write(f"Subdomains: {pages.filter(is_subdomain=True).count()}")

        # Show tree structure
        self.stdout.write("\nTree Structure:")
        self.stdout.write("-" * 80)

        for page in pages:
            indent = "  " * page.depth_level
            parent_info = f"(parent: {page.parent_page.path})" if page.parent_page else "(no parent)"
            subdomain_info = f"[SUBDOMAIN: {page.subdomain}]" if page.is_subdomain else ""

            self.stdout.write(
                f"{indent}L{page.depth_level} {page.path} {parent_info} {subdomain_info}"
            )

        # Check for orphaned pages (should have parent but don't)
        self.stdout.write("\nOrphaned Pages (depth > 0 but no parent):")
        self.stdout.write("-" * 80)
        orphans = pages.filter(depth_level__gt=0, parent_page__isnull=True)
        if orphans.exists():
            for page in orphans:
                self.stdout.write(self.style.WARNING(f"  {page.path} (depth {page.depth_level})"))
        else:
            self.stdout.write(self.style.SUCCESS("  No orphaned pages found"))

        # Check for subdomain detection
        self.stdout.write("\nSubdomain Detection:")
        self.stdout.write("-" * 80)
        for page in pages:
            if page.is_subdomain:
                self.stdout.write(
                    f"  {page.url} -> subdomain={page.subdomain}, depth={page.depth_level}"
                )

        if not pages.filter(is_subdomain=True).exists():
            self.stdout.write(self.style.WARNING("  No subdomains found"))

        self.stdout.write("\n" + "=" * 80)
