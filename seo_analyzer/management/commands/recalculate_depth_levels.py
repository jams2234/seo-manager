"""
Management command to recalculate depth_level for all pages
"""
from django.core.management.base import BaseCommand
from seo_analyzer.models import Domain
from seo_analyzer.services.domain_refresh_service import DomainRefreshService


class Command(BaseCommand):
    help = 'Recalculate depth_level for all pages based on parent-child relationships'

    def handle(self, *args, **options):
        self.stdout.write('Recalculating depth levels for all domains...')

        domains = Domain.objects.all()

        for domain in domains:
            self.stdout.write(f'\nProcessing domain: {domain.domain_name}')

            # Create service instance
            service = DomainRefreshService()

            # Recalculate parent relationships and depth levels
            try:
                service._establish_parent_relationships(domain)
                self.stdout.write(self.style.SUCCESS(f'✓ Successfully updated {domain.domain_name}'))

                # Print summary
                pages = domain.pages.all()
                depth_summary = {}
                for page in pages:
                    depth_summary[page.depth_level] = depth_summary.get(page.depth_level, 0) + 1

                self.stdout.write(f'  Depth distribution:')
                for depth, count in sorted(depth_summary.items()):
                    self.stdout.write(f'    Level {depth}: {count} pages')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error processing {domain.domain_name}: {e}'))

        self.stdout.write(self.style.SUCCESS('\n✓ All done!'))
