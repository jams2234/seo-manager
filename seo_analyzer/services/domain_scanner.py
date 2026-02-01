"""
Domain Scanner Service for discovering pages and subdomains
"""
import logging
import requests
from urllib.parse import urlparse, urljoin
from typing import Dict, List, Set, Optional
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from django.core.cache import cache

logger = logging.getLogger(__name__)


class DomainScanner:
    """
    Service for discovering subdomains and building page hierarchy
    """

    def __init__(self, max_pages: int = 1000):
        """
        Initialize domain scanner

        Args:
            max_pages: Maximum number of pages to discover per domain
        """
        self.max_pages = max_pages
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; SEOAnalyzerBot/1.0)'
        })

    def discover_from_sitemap(self, sitemap_url: str) -> List[Dict]:
        """
        Discover URLs from sitemap with full entry data

        Args:
            sitemap_url: URL to sitemap.xml

        Returns:
            List of sitemap entries with url, lastmod, changefreq, priority
        """
        entries = []

        try:
            logger.info(f"Fetching sitemap: {sitemap_url}")
            response = self.session.get(sitemap_url, timeout=30)
            response.raise_for_status()

            # Parse XML
            root = ET.fromstring(response.content)

            # Check if it's a sitemap index or regular sitemap
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            # Check for sitemap index (contains other sitemaps)
            sitemap_elements = root.findall('.//ns:sitemap/ns:loc', namespace)
            if sitemap_elements:
                logger.info(f"Found {len(sitemap_elements)} child sitemaps")
                for sitemap in sitemap_elements[:10]:  # Limit to 10 child sitemaps
                    child_entries = self.discover_from_sitemap(sitemap.text)
                    entries.extend(child_entries)
                    if len(entries) >= self.max_pages:
                        break
            else:
                # Regular sitemap with URLs - extract full entry data
                url_elements = root.findall('.//ns:url', namespace)
                logger.info(f"Found {len(url_elements)} URLs in sitemap")
                for url_elem in url_elements:
                    if len(entries) >= self.max_pages:
                        break

                    # Extract all sitemap entry fields
                    loc = url_elem.find('ns:loc', namespace)
                    lastmod = url_elem.find('ns:lastmod', namespace)
                    changefreq = url_elem.find('ns:changefreq', namespace)
                    priority = url_elem.find('ns:priority', namespace)

                    entry = {
                        'url': loc.text if loc is not None else None,
                        'lastmod': lastmod.text if lastmod is not None else None,
                        'changefreq': changefreq.text if changefreq is not None else None,
                        'priority': priority.text if priority is not None else None,
                    }

                    if entry['url']:
                        entries.append(entry)

            logger.info(f"Discovered {len(entries)} URLs from sitemap")
            return entries[:self.max_pages]

        except ET.ParseError as e:
            logger.error(f"Failed to parse sitemap XML {sitemap_url}: {e}")
            return []
        except requests.RequestException as e:
            logger.error(f"Failed to fetch sitemap {sitemap_url}: {e}")
            return []

    def discover_from_domain(self, domain: str, protocol: str = 'https') -> Dict:
        """
        Discover pages and subdomains from a domain

        Args:
            domain: Domain name (e.g., 'example.com')
            protocol: 'http' or 'https'

        Returns:
            Dictionary with discovered pages and metadata
        """
        base_url = f"{protocol}://{domain}"
        # Store entries as dict with URL as key to preserve sitemap data
        sitemap_entries = {}  # url -> entry dict

        # Try common sitemap locations
        sitemap_urls = [
            f"{base_url}/sitemap.xml",
            f"{base_url}/sitemap_index.xml",
            f"{base_url}/sitemap-index.xml",
            f"{base_url}/wp-sitemap.xml",  # WordPress
        ]

        for sitemap_url in sitemap_urls:
            entries = self.discover_from_sitemap(sitemap_url)
            if entries:
                for entry in entries:
                    if entry['url'] and entry['url'] not in sitemap_entries:
                        sitemap_entries[entry['url']] = entry
                logger.info(f"Successfully used sitemap: {sitemap_url}")
                break

        # If no sitemap found, try crawling the homepage
        if not sitemap_entries:
            logger.info(f"No sitemap found, attempting to crawl homepage: {base_url}")
            homepage_urls = self._crawl_page(base_url, base_url, max_depth=2)
            # Convert crawled URLs to entry format (no sitemap data)
            for url in homepage_urls:
                if url not in sitemap_entries:
                    sitemap_entries[url] = {'url': url, 'lastmod': None, 'changefreq': None, 'priority': None}

        # Organize URLs by subdomain and path
        organized = self._organize_urls(sitemap_entries, domain)

        return {
            'domain': domain,
            'protocol': protocol,
            'total_urls': len(sitemap_entries),
            'pages': organized['pages'],
            'subdomains': organized['subdomains'],
            'mismatch_count': organized.get('mismatch_count', 0),
        }

    def _crawl_page(
        self,
        url: str,
        base_domain: str,
        max_depth: int = 2,
        current_depth: int = 0,
        visited: Optional[Set[str]] = None
    ) -> Set[str]:
        """
        Recursively crawl pages to discover URLs

        Args:
            url: URL to crawl
            base_domain: Base domain to stay within
            max_depth: Maximum crawl depth
            current_depth: Current recursion depth
            visited: Set of already visited URLs

        Returns:
            Set of discovered URLs
        """
        if visited is None:
            visited = set()

        if current_depth >= max_depth or len(visited) >= self.max_pages:
            return visited

        if url in visited:
            return visited

        visited.add(url)

        try:
            logger.info(f"Crawling: {url} (depth {current_depth})")
            response = self.session.get(url, timeout=15, allow_redirects=True)
            response.raise_for_status()

            # Only process HTML content
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type:
                return visited

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(url, href)

                # Only follow links within the same domain
                parsed = urlparse(absolute_url)
                if base_domain in parsed.netloc:
                    # Remove fragments and query params for cleaner URLs
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

                    if clean_url not in visited and len(visited) < self.max_pages:
                        # Recursively crawl (with depth limit)
                        if current_depth + 1 < max_depth:
                            self._crawl_page(
                                clean_url,
                                base_domain,
                                max_depth,
                                current_depth + 1,
                                visited
                            )
                        else:
                            visited.add(clean_url)

        except requests.RequestException as e:
            logger.warning(f"Failed to crawl {url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error crawling {url}: {e}")

        return visited

    def _organize_urls(self, sitemap_entries: Dict[str, Dict], base_domain: str) -> Dict:
        """
        Organize URLs by subdomain and path hierarchy

        Args:
            sitemap_entries: Dictionary of URL -> sitemap entry data
            base_domain: Base domain name

        Returns:
            Dictionary with organized pages and subdomains
        """
        pages = []
        subdomains = set()
        mismatch_count = 0

        for url, entry in sitemap_entries.items():
            # Check for redirects and get canonical URL
            redirect_info = self._check_url_redirects(url)
            canonical_url = redirect_info['canonical_url']
            has_mismatch = redirect_info['has_mismatch']
            redirect_chain = redirect_info['redirect_chain']

            if has_mismatch:
                mismatch_count += 1
                logger.info(f"Sitemap mismatch detected: {url} -> {canonical_url}")

            # Use canonical URL for parsing
            parsed = urlparse(canonical_url)

            # Determine if it's a subdomain
            is_subdomain = False
            subdomain = None

            if parsed.netloc != base_domain and parsed.netloc != f"www.{base_domain}":
                # Extract subdomain
                if base_domain in parsed.netloc:
                    subdomain = parsed.netloc.replace(f".{base_domain}", "").replace(base_domain, "")
                    is_subdomain = bool(subdomain)
                    if is_subdomain:
                        subdomains.add(subdomain)

            # Calculate depth (number of path segments)
            path = parsed.path.strip('/')
            depth_level = len(path.split('/')) if path else 0

            # Build sitemap entry for storage (original sitemap data)
            sitemap_entry_data = {
                'loc': url,  # Original URL from sitemap
                'lastmod': entry.get('lastmod'),
                'changefreq': entry.get('changefreq'),
                'priority': entry.get('priority'),
            }

            page_data = {
                'url': canonical_url,  # Use canonical URL as primary
                'sitemap_url': url if has_mismatch else None,  # Original sitemap URL if different
                'path': parsed.path,
                'is_subdomain': is_subdomain,
                'subdomain': subdomain,
                'depth_level': depth_level,
                'has_sitemap_mismatch': has_mismatch,
                'redirect_chain': redirect_chain if redirect_chain else None,
                'sitemap_entry': sitemap_entry_data,  # Full sitemap entry data
            }

            pages.append(page_data)

        logger.info(f"Organized {len(pages)} pages, found {len(subdomains)} subdomains, {mismatch_count} sitemap mismatches")

        return {
            'pages': pages,
            'subdomains': list(subdomains),
            'mismatch_count': mismatch_count,
        }

    def _check_url_redirects(self, url: str) -> Dict:
        """
        Check if URL redirects to a different URL (canonical URL detection)

        Args:
            url: URL to check

        Returns:
            Dictionary with canonical URL and redirect info
        """
        try:
            # Send HEAD request following redirects
            response = self.session.head(
                url,
                timeout=10,
                allow_redirects=True
            )

            final_url = response.url
            redirect_chain = []

            # Get redirect history first
            if response.history:
                redirect_chain = [
                    {
                        'url': r.url,
                        'status_code': r.status_code
                    }
                    for r in response.history
                ]
                redirect_chain.append({
                    'url': final_url,
                    'status_code': response.status_code
                })

            # If any redirect occurred, it's a mismatch (sitemap URL != canonical URL)
            # This includes trailing slash redirects (308)
            has_mismatch = len(redirect_chain) > 0

            return {
                'canonical_url': final_url,
                'has_mismatch': has_mismatch,
                'redirect_chain': redirect_chain,
                'status_code': response.status_code,
            }

        except requests.RequestException as e:
            logger.warning(f"Failed to check redirects for {url}: {e}")
            # On error, return original URL
            return {
                'canonical_url': url,
                'has_mismatch': False,
                'redirect_chain': None,
                'status_code': None,
                'error': str(e),
            }

    def build_hierarchy(self, pages: List[Dict]) -> Dict:
        """
        Build parent-child hierarchy for pages

        Args:
            pages: List of page dictionaries

        Returns:
            Dictionary with hierarchy information
        """
        # Sort by depth (shallow to deep)
        sorted_pages = sorted(pages, key=lambda x: x.get('depth_level', 0))

        # Build hierarchy by matching paths
        for i, page in enumerate(sorted_pages):
            page['parent_index'] = None
            page_path = page['path'].strip('/')

            # Find parent (closest ancestor path)
            for j in range(i - 1, -1, -1):
                potential_parent = sorted_pages[j]
                parent_path = potential_parent['path'].strip('/')

                # Check if current page is a child of this parent
                if page_path.startswith(parent_path + '/') if parent_path else False:
                    page['parent_index'] = j
                    break

        return {
            'pages': sorted_pages,
            'total_pages': len(sorted_pages),
        }

    @staticmethod
    def check_url_status(url: str) -> Dict:
        """
        Check HTTP status of a URL

        Args:
            url: URL to check

        Returns:
            Dictionary with status information
        """
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            return {
                'url': url,
                'status_code': response.status_code,
                'status': 'active' if response.status_code < 400 else 'error',
                'final_url': response.url,
            }
        except requests.RequestException as e:
            return {
                'url': url,
                'status_code': None,
                'status': 'error',
                'error': str(e),
            }
