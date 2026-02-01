"""
Sitemap ViewSets
"""
import logging
from datetime import datetime, timezone as dt_timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import SitemapConfig, SitemapHistory
from ..serializers import SitemapConfigSerializer, SitemapHistorySerializer

logger = logging.getLogger(__name__)


class SitemapConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Sitemap Configuration
    """
    queryset = SitemapConfig.objects.all().select_related('domain').order_by('-created_at')
    serializer_class = SitemapConfigSerializer

    def get_queryset(self):
        """Filter by domain"""
        queryset = super().get_queryset()
        domain_id = self.request.query_params.get('domain')

        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)

        return queryset

    @action(detail=True, methods=['post'], url_path='generate')
    def generate(self, request, pk=None):
        """
        Generate sitemap for this configuration
        POST /api/v1/sitemap-configs/{id}/generate/
        """
        config = self.get_object()

        try:
            from ..services import SitemapManager

            manager = SitemapManager()
            result = manager.generate(config.domain)

            if result.get('error'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            SitemapHistory.objects.create(
                domain=config.domain,
                url_count=result.get('url_count', 0),
                file_size_bytes=result.get('size_bytes', 0),
                generated=True,
                deployed=False
            )

            config.last_generated_at = datetime.now(dt_timezone.utc)
            config.save()

            return Response({
                'message': 'Sitemap generated successfully',
                'url_count': result.get('url_count'),
                'size_bytes': result.get('size_bytes'),
                'type': result.get('type')
            })

        except Exception as e:
            logger.error(f"Sitemap generation failed: {e}", exc_info=True)
            return Response(
                {'error': f'Generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='deploy')
    def deploy(self, request, pk=None):
        """
        Deploy sitemap using configured method
        POST /api/v1/sitemap-configs/{id}/deploy/
        """
        config = self.get_object()

        try:
            from ..services import SitemapManager

            manager = SitemapManager()
            result = manager.generate(config.domain)

            if result.get('error'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            deploy_result = manager.deploy(config, result.get('xml_content'))

            if not deploy_result.get('success'):
                return Response(
                    {'error': deploy_result.get('error')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            config.last_deployed_at = datetime.now(dt_timezone.utc)
            config.save()

            SitemapHistory.objects.create(
                domain=config.domain,
                url_count=result.get('url_count', 0),
                file_size_bytes=result.get('size_bytes', 0),
                generated=True,
                deployed=True
            )

            return Response({
                'message': 'Sitemap deployed successfully',
                'method': deploy_result.get('method'),
                'path': deploy_result.get('path')
            })

        except Exception as e:
            logger.error(f"Sitemap deployment failed: {e}", exc_info=True)
            return Response(
                {'error': f'Deployment failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='import')
    def import_sitemap(self, request, pk=None):
        """
        Import existing sitemap from URL
        POST /api/v1/sitemap-configs/{id}/import/
        """
        config = self.get_object()
        sitemap_url = request.data.get('sitemap_url') or config.existing_sitemap_url

        if not sitemap_url:
            return Response(
                {'error': 'Sitemap URL is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from ..services import SitemapManager

            manager = SitemapManager()
            result = manager.import_existing_sitemap(sitemap_url, config.domain)

            if result.get('error'):
                return Response(
                    {'error': result.get('message')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            SitemapHistory.objects.create(
                domain=config.domain,
                url_count=result.get('url_count', 0),
                file_size_bytes=0,
                sitemap_url=sitemap_url,
                generated=False,
                deployed=False
            )

            return Response({
                'message': 'Sitemap imported successfully',
                'sitemap_url': sitemap_url,
                'url_count': result.get('url_count'),
                'type': result.get('type')
            })

        except Exception as e:
            logger.error(f"Sitemap import failed: {e}", exc_info=True)
            return Response(
                {'error': f'Import failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SitemapHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Sitemap History (Read-only)
    """
    queryset = SitemapHistory.objects.all().select_related('domain').order_by('-created_at')
    serializer_class = SitemapHistorySerializer

    def get_queryset(self):
        """Filter by domain"""
        queryset = super().get_queryset()
        domain_id = self.request.query_params.get('domain')

        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)

        return queryset


class SitemapAnalysisView(viewsets.ViewSet):
    """
    ViewSet for Sitemap Analysis
    Analyzes sitemap URLs for redirect mismatches
    """

    @action(detail=False, methods=['post'], url_path='analyze')
    def analyze_sitemap(self, request):
        """
        Analyze a sitemap URL for redirect issues
        POST /api/v1/sitemap-analysis/analyze/

        Request body:
        {
            "sitemap_url": "https://example.com/sitemap.xml",
            "max_urls": 100  // optional, default 100
        }
        """
        sitemap_url = request.data.get('sitemap_url')
        max_urls = min(request.data.get('max_urls', 100), 500)  # Cap at 500

        if not sitemap_url:
            return Response(
                {'error': 'sitemap_url is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            import requests
            import xml.etree.ElementTree as ET

            logger.info(f"Analyzing sitemap: {sitemap_url}")

            # Fetch sitemap
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (compatible; SEOAnalyzerBot/1.0)'
            })

            response = session.get(sitemap_url, timeout=30)
            response.raise_for_status()

            # Parse XML
            root = ET.fromstring(response.content)
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            # Check for sitemap index
            sitemap_elements = root.findall('.//ns:sitemap/ns:loc', namespace)
            if sitemap_elements:
                # This is a sitemap index
                return Response({
                    'type': 'sitemap_index',
                    'sitemap_count': len(sitemap_elements),
                    'sitemaps': [s.text for s in sitemap_elements[:20]],
                    'message': 'This is a sitemap index. Analyze individual sitemaps.'
                })

            # Regular sitemap with URLs
            url_elements = root.findall('.//ns:url/ns:loc', namespace)
            total_urls = len(url_elements)

            logger.info(f"Found {total_urls} URLs in sitemap")

            # Analyze URLs for redirects
            analysis_results = []
            mismatches = []

            for i, url_elem in enumerate(url_elements[:max_urls]):
                url = url_elem.text

                try:
                    # Check for redirects
                    head_response = session.head(
                        url,
                        timeout=10,
                        allow_redirects=True
                    )

                    final_url = head_response.url
                    redirect_chain = []

                    # Build redirect chain
                    if head_response.history:
                        for r in head_response.history:
                            redirect_chain.append({
                                'url': r.url,
                                'status_code': r.status_code
                            })
                        redirect_chain.append({
                            'url': final_url,
                            'status_code': head_response.status_code
                        })

                    # Check for mismatch
                    original_normalized = url.rstrip('/')
                    final_normalized = final_url.rstrip('/')
                    has_mismatch = original_normalized != final_normalized

                    result = {
                        'sitemap_url': url,
                        'canonical_url': final_url,
                        'has_mismatch': has_mismatch,
                        'status_code': head_response.status_code,
                        'redirect_chain': redirect_chain if redirect_chain else None
                    }

                    analysis_results.append(result)

                    if has_mismatch:
                        mismatches.append(result)

                except requests.RequestException as e:
                    analysis_results.append({
                        'sitemap_url': url,
                        'canonical_url': None,
                        'has_mismatch': False,
                        'error': str(e)
                    })

            return Response({
                'type': 'sitemap',
                'sitemap_url': sitemap_url,
                'total_urls': total_urls,
                'analyzed_urls': len(analysis_results),
                'mismatch_count': len(mismatches),
                'mismatches': mismatches,
                'all_results': analysis_results if request.data.get('include_all') else None,
                'summary': {
                    'total': total_urls,
                    'analyzed': len(analysis_results),
                    'mismatches': len(mismatches),
                    'mismatch_rate': f"{(len(mismatches) / len(analysis_results) * 100):.1f}%" if analysis_results else "0%"
                }
            })

        except requests.RequestException as e:
            logger.error(f"Failed to fetch sitemap: {e}")
            return Response(
                {'error': f'Failed to fetch sitemap: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except ET.ParseError as e:
            logger.error(f"Failed to parse sitemap XML: {e}")
            return Response(
                {'error': f'Invalid sitemap XML: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Sitemap analysis failed: {e}", exc_info=True)
            return Response(
                {'error': f'Analysis failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='domain/(?P<domain_id>[^/.]+)/mismatches')
    def get_domain_mismatches(self, request, domain_id=None):
        """
        Get all sitemap mismatches for a domain
        GET /api/v1/sitemap-analysis/domain/{domain_id}/mismatches/
        """
        try:
            from ..models import Domain, Page

            domain = Domain.objects.get(id=domain_id)
            pages_with_mismatch = Page.objects.filter(
                domain=domain,
                has_sitemap_mismatch=True
            ).values(
                'id', 'url', 'sitemap_url', 'redirect_chain', 'path', 'status'
            )

            return Response({
                'domain_id': domain_id,
                'domain_name': domain.domain_name,
                'mismatch_count': pages_with_mismatch.count(),
                'pages': list(pages_with_mismatch)
            })

        except Domain.DoesNotExist:
            return Response(
                {'error': 'Domain not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to get domain mismatches: {e}", exc_info=True)
            return Response(
                {'error': f'Failed to get mismatches: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
