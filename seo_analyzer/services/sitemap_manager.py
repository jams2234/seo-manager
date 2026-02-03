"""
Sitemap Manager Service
Generates, validates, optimizes, and deploys XML sitemaps
"""
import os
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse
from io import BytesIO
import ftplib
import paramiko
from django.utils import timezone

from .base import ManagerService

logger = logging.getLogger(__name__)


class SitemapManager(ManagerService):
    """
    Service for managing XML sitemaps
    """

    # Sitemap constraints (as per protocol)
    MAX_URLS_PER_SITEMAP = 50000
    MAX_SITEMAP_SIZE = 50 * 1024 * 1024  # 50MB uncompressed
    NAMESPACE = 'http://www.sitemaps.org/schemas/sitemap/0.9'

    # Default change frequencies
    DEFAULT_CHANGEFREQ = {
        0: 'daily',      # Homepage
        1: 'weekly',     # Category pages
        2: 'weekly',     # Subcategory pages
        3: 'monthly',    # Content pages
    }

    def __init__(self):
        super().__init__()

    def generate(self, domain_obj, **kwargs) -> Dict:
        """
        Generate sitemap XML for a domain

        Args:
            domain_obj: Domain model instance
            **kwargs: Options (include_images, priority_config, etc.)

        Returns:
            Generation result with XML content
        """
        try:
            from seo_analyzer.models import Page, SEOMetrics
            from django.db.models import OuterRef, Subquery, FloatField

            self.log_info(f"Generating sitemap for domain: {domain_obj.name}")

            # Subquery to get latest SEO score for each page (avoids N+1 queries)
            latest_seo_score_subquery = SEOMetrics.objects.filter(
                page_id=OuterRef('id')
            ).order_by('-snapshot_date').values('seo_score')[:1]

            # Get all active pages with annotated SEO score
            pages = Page.objects.filter(
                domain=domain_obj,
                status='active'
            ).annotate(
                seo_score=Subquery(latest_seo_score_subquery, output_field=FloatField())
            ).order_by('depth_level', '-last_crawled_at')

            if not pages.exists():
                return {
                    'error': True,
                    'message': 'No active pages found for sitemap generation'
                }

            # Check if we need sitemap index (multiple sitemaps)
            total_pages = pages.count()
            needs_index = total_pages > self.MAX_URLS_PER_SITEMAP

            if needs_index:
                # Generate sitemap index with multiple sitemaps
                result = self._generate_sitemap_index(domain_obj, pages, **kwargs)
            else:
                # Generate single sitemap
                result = self._generate_single_sitemap(domain_obj, pages, **kwargs)

            self.log_info(f"Sitemap generation completed: {total_pages} URLs")
            return result

        except Exception as e:
            self.log_error(f"Sitemap generation failed: {e}", exc_info=True)
            return {
                'error': True,
                'message': f"Generation failed: {str(e)}"
            }

    def _generate_single_sitemap(
        self,
        domain_obj,
        pages,
        include_images: bool = True,
        **kwargs
    ) -> Dict:
        """Generate a single sitemap XML"""
        # Create XML structure
        urlset = ET.Element('urlset')
        urlset.set('xmlns', self.NAMESPACE)

        if include_images:
            urlset.set('xmlns:image', 'http://www.google.com/schemas/sitemap-image/1.1')

        # Add URLs
        for page in pages:
            url_elem = self._create_url_element(page, include_images)
            urlset.append(url_elem)

        # Convert to string
        xml_string = self._prettify_xml(urlset)

        return {
            'error': False,
            'type': 'single',
            'url_count': pages.count(),
            'xml_content': xml_string,
            'size_bytes': len(xml_string.encode('utf-8')),
            'generated_at': timezone.now().isoformat()
        }

    def _generate_sitemap_index(
        self,
        domain_obj,
        pages,
        **kwargs
    ) -> Dict:
        """Generate sitemap index with multiple sitemap files"""
        total_pages = pages.count()
        num_sitemaps = (total_pages // self.MAX_URLS_PER_SITEMAP) + 1

        sitemaps = []
        sitemap_urls = []

        # Generate individual sitemaps
        for i in range(num_sitemaps):
            start_idx = i * self.MAX_URLS_PER_SITEMAP
            end_idx = start_idx + self.MAX_URLS_PER_SITEMAP
            page_batch = list(pages[start_idx:end_idx])

            sitemap_result = self._generate_single_sitemap(
                domain_obj,
                page_batch,
                **kwargs
            )

            sitemap_filename = f"sitemap-{i+1}.xml"
            sitemap_url = f"https://{domain_obj.name}/{sitemap_filename}"

            sitemaps.append({
                'filename': sitemap_filename,
                'xml_content': sitemap_result['xml_content'],
                'url_count': len(page_batch),
                'size_bytes': sitemap_result['size_bytes']
            })

            sitemap_urls.append(sitemap_url)

        # Generate sitemap index
        sitemapindex = ET.Element('sitemapindex')
        sitemapindex.set('xmlns', self.NAMESPACE)

        for sitemap_url in sitemap_urls:
            sitemap_elem = ET.SubElement(sitemapindex, 'sitemap')
            loc_elem = ET.SubElement(sitemap_elem, 'loc')
            loc_elem.text = sitemap_url
            lastmod_elem = ET.SubElement(sitemap_elem, 'lastmod')
            lastmod_elem.text = timezone.now().strftime('%Y-%m-%d')

        index_xml_string = self._prettify_xml(sitemapindex)

        return {
            'error': False,
            'type': 'index',
            'url_count': total_pages,
            'sitemap_count': num_sitemaps,
            'index_xml_content': index_xml_string,
            'sitemaps': sitemaps,
            'generated_at': timezone.now().isoformat()
        }

    def _create_url_element(self, page, include_images: bool = True) -> ET.Element:
        """Create a URL element for a page"""
        url_elem = ET.Element('url')

        # Location (required)
        loc = ET.SubElement(url_elem, 'loc')
        loc.text = page.url

        # Last modified
        if page.last_crawled_at:
            lastmod = ET.SubElement(url_elem, 'lastmod')
            lastmod.text = page.last_crawled_at.strftime('%Y-%m-%d')

        # Change frequency
        changefreq = ET.SubElement(url_elem, 'changefreq')
        depth = page.depth_level if hasattr(page, 'depth_level') else 3
        changefreq.text = self.DEFAULT_CHANGEFREQ.get(depth, 'monthly')

        # Priority (based on depth and SEO score)
        priority = ET.SubElement(url_elem, 'priority')
        priority.text = str(self._calculate_priority(page))

        # Images (if enabled and available)
        if include_images and hasattr(page, 'images_data'):
            # Add image elements if available
            # This would require image data to be stored in the page model
            pass

        return url_elem

    def _calculate_priority(self, page) -> float:
        """Calculate URL priority (0.0 to 1.0)"""
        # Base priority on depth
        depth = page.depth_level if hasattr(page, 'depth_level') else 3
        if depth == 0:
            base_priority = 1.0  # Homepage
        elif depth == 1:
            base_priority = 0.8  # Main sections
        elif depth == 2:
            base_priority = 0.6  # Subsections
        else:
            base_priority = 0.4  # Deep pages

        # Adjust based on SEO score if available
        if hasattr(page, 'seo_score') and page.seo_score:
            # Boost by up to 0.2 based on SEO score
            score_boost = (page.seo_score / 100) * 0.2
            base_priority = min(1.0, base_priority + score_boost)

        return round(base_priority, 1)

    def _prettify_xml(self, elem: ET.Element) -> str:
        """Convert XML element to pretty-printed string"""
        # Create XML declaration
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'

        # Convert to string with proper formatting
        ET.indent(elem, space="  ")
        xml_bytes = ET.tostring(elem, encoding='utf-8', method='xml')
        xml_string = xml_bytes.decode('utf-8')

        return xml_declaration + xml_string

    def validate(self, xml_content: str, **kwargs) -> Dict:
        """
        Validate sitemap XML

        Args:
            xml_content: XML content to validate
            **kwargs: Validation options

        Returns:
            Validation result
        """
        try:
            self.log_info("Validating sitemap XML")

            issues = []
            warnings = []

            # Parse XML
            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError as e:
                return {
                    'valid': False,
                    'error': f"XML parsing error: {str(e)}",
                    'issues': ['Invalid XML format']
                }

            # Check namespace
            if self.NAMESPACE not in root.tag:
                issues.append("Invalid or missing sitemap namespace")

            # Determine if it's sitemap index or urlset
            is_index = 'sitemapindex' in root.tag
            is_urlset = 'urlset' in root.tag

            if not is_index and not is_urlset:
                issues.append("Root element must be either 'urlset' or 'sitemapindex'")

            # Validate URLs or sitemaps
            if is_urlset:
                url_elements = root.findall(f'.//{{{self.NAMESPACE}}}url')
                url_count = len(url_elements)

                # Check URL count
                if url_count > self.MAX_URLS_PER_SITEMAP:
                    issues.append(f"Too many URLs ({url_count}). Maximum is {self.MAX_URLS_PER_SITEMAP}")

                # Validate each URL
                for i, url_elem in enumerate(url_elements[:100]):  # Check first 100
                    loc = url_elem.find(f'{{{self.NAMESPACE}}}loc')
                    if loc is None or not loc.text:
                        issues.append(f"URL #{i+1} missing <loc> element")
                    elif not self._is_valid_url(loc.text):
                        issues.append(f"URL #{i+1} has invalid format: {loc.text}")

            elif is_index:
                sitemap_elements = root.findall(f'.//{{{self.NAMESPACE}}}sitemap')
                sitemap_count = len(sitemap_elements)

                if sitemap_count == 0:
                    issues.append("Sitemap index contains no sitemaps")

                # Validate each sitemap
                for i, sitemap_elem in enumerate(sitemap_elements):
                    loc = sitemap_elem.find(f'{{{self.NAMESPACE}}}loc')
                    if loc is None or not loc.text:
                        issues.append(f"Sitemap #{i+1} missing <loc> element")

            # Check size
            size_bytes = len(xml_content.encode('utf-8'))
            if size_bytes > self.MAX_SITEMAP_SIZE:
                issues.append(f"Sitemap size ({size_bytes} bytes) exceeds maximum ({self.MAX_SITEMAP_SIZE} bytes)")
            elif size_bytes > self.MAX_SITEMAP_SIZE * 0.9:
                warnings.append(f"Sitemap size ({size_bytes} bytes) is close to maximum")

            valid = len(issues) == 0

            return {
                'valid': valid,
                'issues': issues,
                'warnings': warnings,
                'url_count': url_count if is_urlset else 0,
                'sitemap_count': sitemap_count if is_index else 0,
                'size_bytes': size_bytes,
                'type': 'index' if is_index else 'urlset'
            }

        except Exception as e:
            self.log_error(f"Sitemap validation failed: {e}", exc_info=True)
            return {
                'valid': False,
                'error': str(e),
                'issues': [f"Validation error: {str(e)}"]
            }

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False

    def deploy(self, config_obj, xml_content: str, **kwargs) -> Dict:
        """
        Deploy sitemap to server

        Args:
            config_obj: SitemapConfig model instance
            xml_content: XML content to deploy
            **kwargs: Deployment options

        Returns:
            Deployment result
        """
        try:
            method = config_obj.deployment_method

            self.log_info(f"Deploying sitemap using method: {method}")

            if method == 'direct':
                return self._deploy_direct(config_obj, xml_content, **kwargs)
            elif method == 'ftp':
                return self._deploy_ftp(config_obj, xml_content, **kwargs)
            elif method == 'sftp':
                return self._deploy_sftp(config_obj, xml_content, **kwargs)
            elif method == 'git':
                return self._deploy_git(config_obj, xml_content, **kwargs)
            else:
                return {
                    'success': False,
                    'error': f"Unknown deployment method: {method}"
                }

        except Exception as e:
            self.log_error(f"Sitemap deployment failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': f"Deployment failed: {str(e)}"
            }

    def _deploy_direct(self, config_obj, xml_content: str, **kwargs) -> Dict:
        """Deploy by writing directly to filesystem"""
        try:
            deployment_path = config_obj.deployment_path or '/var/www/html/sitemap.xml'

            # Ensure directory exists
            os.makedirs(os.path.dirname(deployment_path), exist_ok=True)

            # Write file
            with open(deployment_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)

            self.log_info(f"Sitemap deployed directly to: {deployment_path}")

            return {
                'success': True,
                'method': 'direct',
                'path': deployment_path,
                'deployed_at': timezone.now().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"Direct deployment failed: {str(e)}"
            }

    def _deploy_ftp(self, config_obj, xml_content: str, **kwargs) -> Dict:
        """Deploy via FTP"""
        try:
            credentials = config_obj.deployment_config or {}

            ftp_host = credentials.get('host')
            ftp_user = credentials.get('username')
            ftp_pass = credentials.get('password')
            ftp_path = credentials.get('path', '/sitemap.xml')

            if not all([ftp_host, ftp_user, ftp_pass]):
                return {
                    'success': False,
                    'error': 'FTP credentials incomplete'
                }

            # Connect to FTP
            ftp = ftplib.FTP(ftp_host)
            ftp.login(ftp_user, ftp_pass)

            # Upload file
            bio = BytesIO(xml_content.encode('utf-8'))
            ftp.storbinary(f'STOR {ftp_path}', bio)
            ftp.quit()

            self.log_info(f"Sitemap deployed via FTP to: {ftp_host}{ftp_path}")

            return {
                'success': True,
                'method': 'ftp',
                'host': ftp_host,
                'path': ftp_path,
                'deployed_at': timezone.now().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"FTP deployment failed: {str(e)}"
            }

    def _deploy_sftp(self, config_obj, xml_content: str, **kwargs) -> Dict:
        """Deploy via SFTP"""
        try:
            credentials = config_obj.deployment_config or {}

            sftp_host = credentials.get('host')
            sftp_user = credentials.get('username')
            sftp_pass = credentials.get('password')
            sftp_port = credentials.get('port', 22)
            sftp_path = credentials.get('path', '/sitemap.xml')

            if not all([sftp_host, sftp_user, sftp_pass]):
                return {
                    'success': False,
                    'error': 'SFTP credentials incomplete'
                }

            # Connect via SSH
            transport = paramiko.Transport((sftp_host, sftp_port))
            transport.connect(username=sftp_user, password=sftp_pass)

            # Open SFTP session
            sftp = paramiko.SFTPClient.from_transport(transport)

            # Upload file
            bio = BytesIO(xml_content.encode('utf-8'))
            sftp.putfo(bio, sftp_path)

            sftp.close()
            transport.close()

            self.log_info(f"Sitemap deployed via SFTP to: {sftp_host}{sftp_path}")

            return {
                'success': True,
                'method': 'sftp',
                'host': sftp_host,
                'path': sftp_path,
                'deployed_at': timezone.now().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"SFTP deployment failed: {str(e)}"
            }

    def _deploy_git(self, config_obj, xml_content: str, **kwargs) -> Dict:
        """Deploy via Git commit and push"""
        try:
            credentials = config_obj.deployment_config or {}

            repo_path = credentials.get('repo_path')
            file_path = credentials.get('file_path', 'sitemap.xml')
            branch = credentials.get('branch', 'main')

            if not repo_path:
                return {
                    'success': False,
                    'error': 'Git repository path not configured'
                }

            # Write file to repo
            full_path = os.path.join(repo_path, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)

            # Git operations
            import subprocess

            os.chdir(repo_path)

            # Add file
            subprocess.run(['git', 'add', file_path], check=True)

            # Commit
            commit_msg = f"Update sitemap - {timezone.now().strftime('%Y-%m-%d %H:%M')}"
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)

            # Push
            subprocess.run(['git', 'push', 'origin', branch], check=True)

            self.log_info(f"Sitemap deployed via Git to: {repo_path}/{file_path}")

            return {
                'success': True,
                'method': 'git',
                'repo_path': repo_path,
                'file_path': file_path,
                'branch': branch,
                'deployed_at': timezone.now().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"Git deployment failed: {str(e)}"
            }

    def import_existing_sitemap(self, sitemap_url: str, domain_obj) -> Dict:
        """
        Import existing sitemap from URL

        Args:
            sitemap_url: URL of existing sitemap
            domain_obj: Domain model instance

        Returns:
            Import result with discovered URLs
        """
        try:
            self.log_info(f"Importing existing sitemap from: {sitemap_url}")

            # Fetch sitemap
            response = requests.get(sitemap_url, timeout=30)
            response.raise_for_status()

            xml_content = response.text

            # Parse XML
            root = ET.fromstring(xml_content)

            # Determine if it's sitemap index or urlset
            is_index = 'sitemapindex' in root.tag
            is_urlset = 'urlset' in root.tag

            urls = []

            if is_urlset:
                # Parse URL set
                url_elements = root.findall(f'.//{{{self.NAMESPACE}}}url')

                for url_elem in url_elements:
                    loc = url_elem.find(f'{{{self.NAMESPACE}}}loc')
                    lastmod = url_elem.find(f'{{{self.NAMESPACE}}}lastmod')
                    changefreq = url_elem.find(f'{{{self.NAMESPACE}}}changefreq')
                    priority = url_elem.find(f'{{{self.NAMESPACE}}}priority')

                    if loc is not None and loc.text:
                        url_data = {
                            'url': loc.text,
                            'lastmod': lastmod.text if lastmod is not None else None,
                            'changefreq': changefreq.text if changefreq is not None else None,
                            'priority': float(priority.text) if priority is not None else None,
                        }
                        urls.append(url_data)

            elif is_index:
                # Parse sitemap index
                sitemap_elements = root.findall(f'.//{{{self.NAMESPACE}}}sitemap')

                # Recursively fetch each child sitemap
                for sitemap_elem in sitemap_elements:
                    loc = sitemap_elem.find(f'{{{self.NAMESPACE}}}loc')
                    if loc is not None and loc.text:
                        child_result = self.import_existing_sitemap(loc.text, domain_obj)
                        if not child_result.get('error'):
                            urls.extend(child_result.get('urls', []))

            self.log_info(f"Successfully imported {len(urls)} URLs from sitemap")

            return {
                'error': False,
                'sitemap_url': sitemap_url,
                'type': 'index' if is_index else 'urlset',
                'url_count': len(urls),
                'urls': urls,
                'imported_at': timezone.now().isoformat()
            }

        except requests.RequestException as e:
            self.log_error(f"Failed to fetch sitemap from {sitemap_url}: {e}")
            return {
                'error': True,
                'message': f"Failed to fetch sitemap: {str(e)}"
            }
        except ET.ParseError as e:
            self.log_error(f"Failed to parse sitemap XML: {e}")
            return {
                'error': True,
                'message': f"Invalid sitemap XML: {str(e)}"
            }
        except Exception as e:
            self.log_error(f"Sitemap import failed: {e}", exc_info=True)
            return {
                'error': True,
                'message': f"Import failed: {str(e)}"
            }

    def submit_to_search_console(self, sitemap_url: str, domain_obj) -> Dict:
        """
        Submit sitemap to Google Search Console

        Args:
            sitemap_url: URL of the sitemap
            domain_obj: Domain model instance

        Returns:
            Submission result
        """
        try:
            from .search_console import SearchConsoleService

            self.log_info(f"Submitting sitemap to Search Console: {sitemap_url}")

            # Get Search Console service
            search_console = SearchConsoleService()

            # Submit sitemap
            result = search_console.submit_sitemap(domain_obj.name, sitemap_url)

            return {
                'success': True,
                'sitemap_url': sitemap_url,
                'submitted_at': timezone.now().isoformat(),
                'result': result
            }

        except Exception as e:
            self.log_error(f"Sitemap submission failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': f"Submission failed: {str(e)}"
            }

    def optimize_sitemap(self, domain_obj, **kwargs) -> Dict:
        """
        Optimize sitemap by recalculating priorities and change frequencies

        Args:
            domain_obj: Domain model instance
            **kwargs: Optimization options

        Returns:
            Optimization result
        """
        try:
            from seo_analyzer.models import Page, SEOMetrics
            from django.db.models import OuterRef, Subquery, FloatField

            self.log_info(f"Optimizing sitemap for domain: {domain_obj.name}")

            # Subquery to get latest SEO score for each page (avoids N+1 queries)
            latest_seo_score_subquery = SEOMetrics.objects.filter(
                page_id=OuterRef('id')
            ).order_by('-snapshot_date').values('seo_score')[:1]

            pages = Page.objects.filter(
                domain=domain_obj,
                status='active'
            ).annotate(
                seo_score=Subquery(latest_seo_score_subquery, output_field=FloatField())
            )

            optimization_changes = []

            for page in pages:
                # Calculate optimal priority based on:
                # - Depth level
                # - SEO score
                # - Crawl frequency
                # - Internal links

                old_priority = getattr(page, 'sitemap_priority', None)
                new_priority = self._calculate_priority(page)

                if old_priority != new_priority:
                    optimization_changes.append({
                        'url': page.url,
                        'old_priority': old_priority,
                        'new_priority': new_priority
                    })

            return {
                'success': True,
                'changes_count': len(optimization_changes),
                'changes': optimization_changes[:50],  # Return first 50
                'optimized_at': timezone.now().isoformat()
            }

        except Exception as e:
            self.log_error(f"Sitemap optimization failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': f"Optimization failed: {str(e)}"
            }
