"""
Sitemap Editor Service
Provides CRUD operations for sitemap entries with edit sessions and Git deployment.
"""
import logging
import hashlib
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from django.utils import timezone
from django.db import transaction

from .base import ManagerService

logger = logging.getLogger(__name__)


class SitemapEditorService(ManagerService):
    """
    Service for editing sitemap entries with session-based workflow.
    Supports: load → edit → preview → validate → deploy
    """

    NAMESPACE = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    MAX_URLS_PER_SITEMAP = 50000

    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; SEOAnalyzerBot/1.0)'
        })

    # Abstract method implementations (required by ManagerService)
    def generate(self, **kwargs) -> Dict:
        """Generate sitemap XML - delegates to generate_preview_xml"""
        domain = kwargs.get('domain')
        session_id = kwargs.get('session_id')
        return self.generate_preview_xml(domain, session_id)

    def validate(self, target, **kwargs) -> Dict:
        """Validate session - delegates to validate_session"""
        session_id = target if isinstance(target, int) else target.id
        return self.validate_session(session_id)

    def deploy(self, target, **kwargs) -> Dict:
        """Deploy session - delegates to deploy_session"""
        session_id = target if isinstance(target, int) else target.id
        commit_message = kwargs.get('commit_message')
        return self.deploy_session(session_id, commit_message)

    # =========================================================================
    # Entry Loading
    # =========================================================================

    def load_entries_from_sitemap(self, domain, sitemap_url: str = None) -> Dict:
        """
        Load sitemap entries from live sitemap URL.

        Args:
            domain: Domain model instance
            sitemap_url: Optional sitemap URL (defaults to domain/sitemap.xml)

        Returns:
            Dictionary with entries and metadata
        """
        try:
            if not sitemap_url:
                sitemap_url = f"{domain.protocol}://{domain.domain_name}/sitemap.xml"

            self.log_info(f"Loading sitemap entries from: {sitemap_url}")

            response = self.session.get(sitemap_url, timeout=30)
            response.raise_for_status()

            entries = self._parse_sitemap_xml(response.content, sitemap_url)

            return {
                'error': False,
                'source': sitemap_url,
                'entries_count': len(entries),
                'entries': entries,
            }

        except requests.RequestException as e:
            self.log_error(f"Failed to fetch sitemap: {e}")
            return {
                'error': True,
                'message': f"Failed to fetch sitemap: {str(e)}"
            }
        except ET.ParseError as e:
            self.log_error(f"Failed to parse sitemap XML: {e}")
            return {
                'error': True,
                'message': f"Invalid XML: {str(e)}"
            }

    def _parse_sitemap_xml(self, content: bytes, source_url: str) -> List[Dict]:
        """Parse sitemap XML and extract entries"""
        root = ET.fromstring(content)
        entries = []

        # Check if it's a sitemap index
        if 'sitemapindex' in root.tag:
            # Parse child sitemaps
            ns = {'ns': self.NAMESPACE}
            for sitemap in root.findall('.//ns:sitemap/ns:loc', ns):
                if sitemap.text:
                    try:
                        child_response = self.session.get(sitemap.text, timeout=30)
                        child_entries = self._parse_sitemap_xml(
                            child_response.content,
                            sitemap.text
                        )
                        entries.extend(child_entries)
                    except Exception as e:
                        self.log_warning(f"Failed to fetch child sitemap {sitemap.text}: {e}")
        else:
            # Parse URL entries
            ns = {'ns': self.NAMESPACE}
            for url_elem in root.findall('.//ns:url', ns):
                loc = url_elem.find('ns:loc', ns)
                if loc is not None and loc.text:
                    entry = {
                        'loc': loc.text.strip(),
                        'lastmod': None,
                        'changefreq': None,
                        'priority': None,
                    }

                    lastmod = url_elem.find('ns:lastmod', ns)
                    if lastmod is not None and lastmod.text:
                        entry['lastmod'] = lastmod.text.strip()

                    changefreq = url_elem.find('ns:changefreq', ns)
                    if changefreq is not None and changefreq.text:
                        entry['changefreq'] = changefreq.text.strip()

                    priority = url_elem.find('ns:priority', ns)
                    if priority is not None and priority.text:
                        try:
                            entry['priority'] = float(priority.text.strip())
                        except ValueError:
                            pass

                    entries.append(entry)

        return entries

    def sync_entries_from_sitemap(self, domain, sitemap_url: str = None, user=None) -> Dict:
        """
        Sync sitemap entries from live sitemap to database.

        Args:
            domain: Domain model instance
            sitemap_url: Optional sitemap URL
            user: User making the sync (for audit trail)

        Returns:
            Sync result with counts
        """
        from ..models import SitemapEntry

        result = self.load_entries_from_sitemap(domain, sitemap_url)
        if result.get('error'):
            return result

        entries = result['entries']
        created_count = 0
        updated_count = 0
        errors = []

        with transaction.atomic():
            for entry_data in entries:
                try:
                    loc = entry_data['loc']
                    loc_hash = hashlib.sha256(loc.encode('utf-8')).hexdigest()

                    # Parse lastmod
                    lastmod = None
                    if entry_data.get('lastmod'):
                        try:
                            lastmod = datetime.fromisoformat(
                                entry_data['lastmod'].replace('Z', '+00:00')
                            ).date()
                        except ValueError:
                            # Try parsing as date only
                            try:
                                lastmod = datetime.strptime(
                                    entry_data['lastmod'][:10], '%Y-%m-%d'
                                ).date()
                            except ValueError:
                                pass

                    # Parse priority
                    priority = None
                    if entry_data.get('priority') is not None:
                        try:
                            priority = float(entry_data['priority'])
                            priority = max(0.0, min(1.0, priority))  # Clamp to 0-1
                        except (ValueError, TypeError):
                            pass

                    entry, created = SitemapEntry.objects.update_or_create(
                        domain=domain,
                        loc_hash=loc_hash,
                        defaults={
                            'loc': loc,
                            'lastmod': lastmod,
                            'changefreq': entry_data.get('changefreq'),
                            'priority': priority,
                            'status': 'active',
                            'is_valid': True,
                        }
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                except Exception as e:
                    errors.append({
                        'loc': entry_data.get('loc', 'unknown'),
                        'error': str(e)
                    })

        return {
            'error': False,
            'source': result['source'],
            'total_entries': len(entries),
            'created': created_count,
            'updated': updated_count,
            'errors': errors,
        }

    def populate_from_pages(self, domain, user=None) -> Dict:
        """
        Populate SitemapEntry from existing Page records in database.
        Use this when no sitemap.xml exists or as initial population.

        Args:
            domain: Domain model instance
            user: User making the sync

        Returns:
            Result with counts
        """
        from ..models import SitemapEntry, Page

        try:
            pages = Page.objects.filter(domain=domain)
            created_count = 0
            updated_count = 0
            errors = []

            with transaction.atomic():
                for page in pages:
                    try:
                        loc = page.url
                        loc_hash = hashlib.sha256(loc.encode('utf-8')).hexdigest()

                        # Determine priority based on depth
                        depth = page.depth or 0
                        if depth == 0:
                            priority = 1.0
                        elif depth == 1:
                            priority = 0.8
                        elif depth == 2:
                            priority = 0.6
                        else:
                            priority = 0.5

                        # Determine changefreq based on page type
                        changefreq = 'weekly'
                        if depth == 0:
                            changefreq = 'daily'
                        elif 'blog' in loc or 'news' in loc:
                            changefreq = 'daily'

                        entry, created = SitemapEntry.objects.update_or_create(
                            domain=domain,
                            loc_hash=loc_hash,
                            defaults={
                                'loc': loc,
                                'lastmod': page.last_fetched.date() if page.last_fetched else None,
                                'changefreq': changefreq,
                                'priority': priority,
                                'status': 'active',
                                'is_valid': True,
                                'page': page,  # Link to Page model
                            }
                        )

                        if created:
                            created_count += 1
                        else:
                            updated_count += 1

                    except Exception as e:
                        errors.append({
                            'url': page.url,
                            'error': str(e)
                        })

            return {
                'error': False,
                'source': 'database_pages',
                'total_entries': pages.count(),
                'created': created_count,
                'updated': updated_count,
                'errors': errors,
            }

        except Exception as e:
            self.log_error(f"Failed to populate from pages: {e}", exc_info=True)
            return {
                'error': True,
                'message': str(e)
            }

    # =========================================================================
    # Edit Sessions
    # =========================================================================

    def create_edit_session(self, domain, user=None, name: str = None) -> Dict:
        """
        Create a new edit session for a domain.

        Args:
            domain: Domain model instance
            user: User creating the session
            name: Optional session name

        Returns:
            Created session data
        """
        from ..models import SitemapEditSession, SitemapEntry

        try:
            # Count current entries
            total_entries = SitemapEntry.objects.filter(domain=domain).count()

            session = SitemapEditSession.objects.create(
                domain=domain,
                created_by=user,
                name=name or f"Edit Session {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                status='draft',
                total_entries=total_entries,
            )

            return {
                'error': False,
                'session_id': session.id,
                'session': self._session_to_dict(session),
            }

        except Exception as e:
            self.log_error(f"Failed to create edit session: {e}")
            return {
                'error': True,
                'message': f"Failed to create session: {str(e)}"
            }

    def get_session(self, session_id: int) -> Dict:
        """Get edit session by ID"""
        from ..models import SitemapEditSession

        try:
            session = SitemapEditSession.objects.select_related('domain', 'created_by').get(id=session_id)
            return {
                'error': False,
                'session': self._session_to_dict(session),
            }
        except SitemapEditSession.DoesNotExist:
            return {
                'error': True,
                'message': 'Session not found'
            }

    def _session_to_dict(self, session) -> Dict:
        """Convert session model to dictionary"""
        return {
            'id': session.id,
            'domain_id': session.domain_id,
            'domain_name': session.domain.domain_name,
            'name': session.name,
            'status': session.status,
            'entries_added': session.entries_added,
            'entries_removed': session.entries_removed,
            'entries_modified': session.entries_modified,
            'total_entries': session.total_entries,
            'ai_issues_found': session.ai_issues_found,
            'ai_suggestions': session.ai_suggestions,
            'deployment_commit_hash': session.deployment_commit_hash,
            'created_at': session.created_at.isoformat(),
            'updated_at': session.updated_at.isoformat(),
            'created_by': session.created_by.username if session.created_by else None,
        }

    # =========================================================================
    # Entry CRUD Operations
    # =========================================================================

    def get_entries(self, domain, filters: Dict = None) -> Dict:
        """
        Get all entries for a domain with optional filters.

        Args:
            domain: Domain model instance
            filters: Optional filters (status, is_valid, search)

        Returns:
            List of entries
        """
        from ..models import SitemapEntry

        try:
            queryset = SitemapEntry.objects.filter(domain=domain)

            if filters:
                if filters.get('status'):
                    queryset = queryset.filter(status=filters['status'])
                if filters.get('is_valid') is not None:
                    queryset = queryset.filter(is_valid=filters['is_valid'])
                if filters.get('search'):
                    queryset = queryset.filter(loc__icontains=filters['search'])
                if filters.get('ai_suggested') is not None:
                    queryset = queryset.filter(ai_suggested=filters['ai_suggested'])

            entries = list(queryset.values(
                'id', 'loc', 'lastmod', 'changefreq', 'priority',
                'status', 'is_valid', 'validation_errors',
                'ai_suggested', 'ai_suggestion_reason',
                'http_status_code', 'redirect_url',
                'created_at', 'updated_at'
            ))

            # Convert dates to strings
            for entry in entries:
                if entry['lastmod']:
                    entry['lastmod'] = entry['lastmod'].isoformat()
                if entry['priority']:
                    entry['priority'] = float(entry['priority'])
                entry['created_at'] = entry['created_at'].isoformat()
                entry['updated_at'] = entry['updated_at'].isoformat()

            return {
                'error': False,
                'count': len(entries),
                'entries': entries,
            }

        except Exception as e:
            self.log_error(f"Failed to get entries: {e}")
            return {
                'error': True,
                'message': str(e)
            }

    def add_entry(
        self,
        domain,
        session_id: int,
        loc: str,
        lastmod: str = None,
        changefreq: str = None,
        priority: float = None,
        user=None,
        source: str = 'manual'
    ) -> Dict:
        """
        Add a new sitemap entry.

        Args:
            domain: Domain model instance
            session_id: Edit session ID
            loc: URL location
            lastmod: Last modified date (YYYY-MM-DD)
            changefreq: Change frequency
            priority: Priority (0.0-1.0)
            user: User making the change
            source: Change source (manual, ai_suggestion, bulk_import)

        Returns:
            Created entry data
        """
        from ..models import SitemapEntry, SitemapEditSession, SitemapEntryChange

        try:
            with transaction.atomic():
                session = SitemapEditSession.objects.select_for_update().get(id=session_id)

                # Validate URL
                validation_errors = self._validate_entry(loc, changefreq, priority)

                # Parse lastmod
                lastmod_date = None
                if lastmod:
                    try:
                        lastmod_date = datetime.strptime(lastmod, '%Y-%m-%d').date()
                    except ValueError:
                        validation_errors.append(f"Invalid date format: {lastmod}")

                # Create entry
                entry = SitemapEntry.objects.create(
                    domain=domain,
                    loc=loc,
                    lastmod=lastmod_date,
                    changefreq=changefreq,
                    priority=priority,
                    status='pending_add',
                    is_valid=len(validation_errors) == 0,
                    validation_errors=validation_errors,
                )

                # Record change
                SitemapEntryChange.objects.create(
                    session=session,
                    entry=entry,
                    change_type='add',
                    source=source,
                    url=loc,
                    new_values={
                        'loc': loc,
                        'lastmod': lastmod,
                        'changefreq': changefreq,
                        'priority': float(priority) if priority else None,
                    },
                    changed_by=user,
                )

                # Update session counters
                session.entries_added += 1
                session.total_entries += 1
                session.save(update_fields=['entries_added', 'total_entries', 'updated_at'])

                return {
                    'error': False,
                    'entry_id': entry.id,
                    'entry': self._entry_to_dict(entry),
                    'validation_errors': validation_errors,
                }

        except SitemapEditSession.DoesNotExist:
            return {'error': True, 'message': 'Session not found'}
        except Exception as e:
            self.log_error(f"Failed to add entry: {e}")
            return {'error': True, 'message': str(e)}

    def update_entry(
        self,
        entry_id: int,
        session_id: int,
        updates: Dict,
        user=None,
        source: str = 'manual'
    ) -> Dict:
        """
        Update an existing sitemap entry.

        Args:
            entry_id: Entry ID to update
            session_id: Edit session ID
            updates: Dictionary of fields to update
            user: User making the change
            source: Change source

        Returns:
            Updated entry data
        """
        from ..models import SitemapEntry, SitemapEditSession, SitemapEntryChange

        try:
            with transaction.atomic():
                session = SitemapEditSession.objects.select_for_update().get(id=session_id)
                entry = SitemapEntry.objects.select_for_update().get(id=entry_id)

                # Store old values
                old_values = {
                    'loc': entry.loc,
                    'lastmod': entry.lastmod.isoformat() if entry.lastmod else None,
                    'changefreq': entry.changefreq,
                    'priority': float(entry.priority) if entry.priority else None,
                }

                # Apply updates
                if 'loc' in updates:
                    entry.loc = updates['loc']
                if 'lastmod' in updates:
                    if updates['lastmod']:
                        try:
                            entry.lastmod = datetime.strptime(updates['lastmod'], '%Y-%m-%d').date()
                        except ValueError:
                            pass
                    else:
                        entry.lastmod = None
                if 'changefreq' in updates:
                    entry.changefreq = updates['changefreq']
                if 'priority' in updates:
                    entry.priority = updates['priority']

                # Validate
                validation_errors = self._validate_entry(
                    entry.loc, entry.changefreq, entry.priority
                )
                entry.is_valid = len(validation_errors) == 0
                entry.validation_errors = validation_errors

                # Mark as modified if active
                if entry.status == 'active':
                    entry.status = 'pending_modify'

                entry.save()

                # Record change
                new_values = {
                    'loc': entry.loc,
                    'lastmod': entry.lastmod.isoformat() if entry.lastmod else None,
                    'changefreq': entry.changefreq,
                    'priority': float(entry.priority) if entry.priority else None,
                }

                SitemapEntryChange.objects.create(
                    session=session,
                    entry=entry,
                    change_type='modify',
                    source=source,
                    url=entry.loc,
                    old_values=old_values,
                    new_values=new_values,
                    changed_by=user,
                )

                # Update session counter
                if entry.status == 'pending_modify':
                    session.entries_modified += 1
                    session.save(update_fields=['entries_modified', 'updated_at'])

                return {
                    'error': False,
                    'entry': self._entry_to_dict(entry),
                    'validation_errors': validation_errors,
                }

        except SitemapEditSession.DoesNotExist:
            return {'error': True, 'message': 'Session not found'}
        except SitemapEntry.DoesNotExist:
            return {'error': True, 'message': 'Entry not found'}
        except Exception as e:
            self.log_error(f"Failed to update entry: {e}")
            return {'error': True, 'message': str(e)}

    def remove_entry(
        self,
        entry_id: int,
        session_id: int,
        user=None,
        source: str = 'manual'
    ) -> Dict:
        """
        Mark an entry for removal.

        Args:
            entry_id: Entry ID to remove
            session_id: Edit session ID
            user: User making the change
            source: Change source

        Returns:
            Result
        """
        from ..models import SitemapEntry, SitemapEditSession, SitemapEntryChange

        try:
            with transaction.atomic():
                session = SitemapEditSession.objects.select_for_update().get(id=session_id)
                entry = SitemapEntry.objects.select_for_update().get(id=entry_id)

                # Store old values
                old_values = {
                    'loc': entry.loc,
                    'lastmod': entry.lastmod.isoformat() if entry.lastmod else None,
                    'changefreq': entry.changefreq,
                    'priority': float(entry.priority) if entry.priority else None,
                }

                # Mark for removal
                entry.status = 'pending_remove'
                entry.save(update_fields=['status', 'updated_at'])

                # Record change
                SitemapEntryChange.objects.create(
                    session=session,
                    entry=entry,
                    change_type='remove',
                    source=source,
                    url=entry.loc,
                    old_values=old_values,
                    changed_by=user,
                )

                # Update session counter
                session.entries_removed += 1
                session.total_entries -= 1
                session.save(update_fields=['entries_removed', 'total_entries', 'updated_at'])

                return {
                    'error': False,
                    'message': 'Entry marked for removal',
                }

        except SitemapEditSession.DoesNotExist:
            return {'error': True, 'message': 'Session not found'}
        except SitemapEntry.DoesNotExist:
            return {'error': True, 'message': 'Entry not found'}
        except Exception as e:
            self.log_error(f"Failed to remove entry: {e}")
            return {'error': True, 'message': str(e)}

    def _entry_to_dict(self, entry) -> Dict:
        """Convert entry model to dictionary"""
        return {
            'id': entry.id,
            'loc': entry.loc,
            'lastmod': entry.lastmod.isoformat() if entry.lastmod else None,
            'changefreq': entry.changefreq,
            'priority': float(entry.priority) if entry.priority else None,
            'status': entry.status,
            'is_valid': entry.is_valid,
            'validation_errors': entry.validation_errors,
            'ai_suggested': entry.ai_suggested,
            'ai_suggestion_reason': entry.ai_suggestion_reason,
            'http_status_code': entry.http_status_code,
            'redirect_url': entry.redirect_url,
        }

    def _validate_entry(self, loc: str, changefreq: str = None, priority: float = None) -> List[str]:
        """Validate entry fields"""
        errors = []

        # Validate URL
        try:
            parsed = urlparse(loc)
            if not parsed.scheme or not parsed.netloc:
                errors.append(f"Invalid URL format: {loc}")
            if parsed.scheme not in ('http', 'https'):
                errors.append(f"URL must use http or https scheme: {loc}")
        except Exception:
            errors.append(f"Cannot parse URL: {loc}")

        # Validate changefreq
        valid_changefreq = ['always', 'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'never']
        if changefreq and changefreq not in valid_changefreq:
            errors.append(f"Invalid changefreq: {changefreq}")

        # Validate priority
        if priority is not None:
            try:
                p = float(priority)
                if p < 0 or p > 1:
                    errors.append(f"Priority must be between 0.0 and 1.0: {priority}")
            except (ValueError, TypeError):
                errors.append(f"Invalid priority value: {priority}")

        return errors

    # =========================================================================
    # Preview & Validation
    # =========================================================================

    def generate_preview_xml(self, domain, session_id: int = None) -> Dict:
        """
        Generate preview XML for the sitemap.

        Args:
            domain: Domain model instance
            session_id: Optional session ID to include pending changes

        Returns:
            Preview XML content
        """
        from ..models import SitemapEntry, SitemapEditSession

        try:
            # Get entries (excluding pending_remove)
            entries = SitemapEntry.objects.filter(
                domain=domain
            ).exclude(
                status='pending_remove'
            ).order_by('loc')

            # Generate XML
            xml_content = self._generate_xml(entries)

            # Update session if provided
            if session_id:
                try:
                    session = SitemapEditSession.objects.get(id=session_id)
                    session.preview_xml = xml_content
                    session.preview_generated_at = timezone.now()
                    session.status = 'preview'
                    session.save(update_fields=['preview_xml', 'preview_generated_at', 'status', 'updated_at'])
                except SitemapEditSession.DoesNotExist:
                    pass

            return {
                'error': False,
                'xml_content': xml_content,
                'url_count': entries.count(),
                'size_bytes': len(xml_content.encode('utf-8')),
                'generated_at': timezone.now().isoformat(),
            }

        except Exception as e:
            self.log_error(f"Failed to generate preview: {e}")
            return {'error': True, 'message': str(e)}

    def _generate_xml(self, entries) -> str:
        """Generate sitemap XML from entries"""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]

        for entry in entries:
            lines.append('  <url>')
            lines.append(f'    <loc>{self._escape_xml(entry.loc)}</loc>')
            if entry.lastmod:
                lines.append(f'    <lastmod>{entry.lastmod.isoformat()}</lastmod>')
            if entry.changefreq:
                lines.append(f'    <changefreq>{entry.changefreq}</changefreq>')
            if entry.priority is not None:
                lines.append(f'    <priority>{entry.priority}</priority>')
            lines.append('  </url>')

        lines.append('</urlset>')
        return '\n'.join(lines)

    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters"""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&apos;'))

    def validate_session(self, session_id: int) -> Dict:
        """
        Validate all entries in a session before deployment.

        Args:
            session_id: Edit session ID

        Returns:
            Validation result
        """
        from ..models import SitemapEntry, SitemapEditSession

        try:
            session = SitemapEditSession.objects.get(id=session_id)

            # Get all entries
            entries = SitemapEntry.objects.filter(domain=session.domain).exclude(
                status='pending_remove'
            )

            issues = []
            warnings = []

            # Check total count
            entry_count = entries.count()
            if entry_count > self.MAX_URLS_PER_SITEMAP:
                issues.append(f"Too many URLs ({entry_count}). Maximum is {self.MAX_URLS_PER_SITEMAP}")
            elif entry_count == 0:
                issues.append("No URLs in sitemap")

            # Check for invalid entries
            invalid_entries = entries.filter(is_valid=False)
            for entry in invalid_entries[:10]:  # Show first 10
                issues.append(f"Invalid entry: {entry.loc} - {entry.validation_errors}")

            # Check for duplicates
            from django.db.models import Count
            duplicates = entries.values('loc').annotate(
                count=Count('id')
            ).filter(count__gt=1)
            for dup in duplicates[:5]:
                warnings.append(f"Duplicate URL: {dup['loc']}")

            # Update session status
            session.status = 'validating'
            session.save(update_fields=['status', 'updated_at'])

            valid = len(issues) == 0

            return {
                'error': False,
                'valid': valid,
                'entry_count': entry_count,
                'invalid_count': invalid_entries.count(),
                'issues': issues,
                'warnings': warnings,
            }

        except SitemapEditSession.DoesNotExist:
            return {'error': True, 'message': 'Session not found'}
        except Exception as e:
            self.log_error(f"Failed to validate session: {e}")
            return {'error': True, 'message': str(e)}

    # =========================================================================
    # Deployment
    # =========================================================================

    def deploy_session(self, session_id: int, commit_message: str = None) -> Dict:
        """
        Deploy sitemap changes via Git.

        Args:
            session_id: Edit session ID
            commit_message: Optional commit message

        Returns:
            Deployment result
        """
        from ..models import SitemapEntry, SitemapEditSession
        from .git_deployer import GitDeployer

        try:
            with transaction.atomic():
                session = SitemapEditSession.objects.select_for_update().get(id=session_id)
                domain = session.domain

                # Validate before deployment
                validation = self.validate_session(session_id)
                if validation.get('error') or not validation.get('valid'):
                    session.status = 'failed'
                    session.deployment_error = 'Validation failed: ' + str(validation.get('issues', []))
                    session.save(update_fields=['status', 'deployment_error', 'updated_at'])
                    return {
                        'error': True,
                        'message': 'Validation failed',
                        'issues': validation.get('issues', []),
                    }

                # Generate final XML
                preview_result = self.generate_preview_xml(domain, session_id)
                if preview_result.get('error'):
                    return preview_result

                xml_content = preview_result['xml_content']

                # Update session status
                session.status = 'deploying'
                session.save(update_fields=['status', 'updated_at'])

                # Deploy via Git
                if not domain.git_enabled:
                    return {
                        'error': True,
                        'message': 'Git deployment not enabled for this domain'
                    }

                deployer = GitDeployer(domain)
                deploy_result = deployer.deploy_sitemap(
                    xml_content,
                    commit_message or f"Update sitemap - {session.name}"
                )

                if deploy_result.get('error'):
                    session.status = 'failed'
                    session.deployment_error = deploy_result.get('message', 'Unknown error')
                    session.save(update_fields=['status', 'deployment_error', 'updated_at'])
                    return deploy_result

                # Apply changes to database
                self._apply_session_changes(session)

                # Update session
                session.status = 'deployed'
                session.deployment_commit_hash = deploy_result.get('commit_hash')
                session.deployed_at = timezone.now()
                session.deployment_message = commit_message
                session.save(update_fields=[
                    'status', 'deployment_commit_hash', 'deployed_at',
                    'deployment_message', 'updated_at'
                ])

                return {
                    'error': False,
                    'message': 'Sitemap deployed successfully',
                    'commit_hash': deploy_result.get('commit_hash'),
                    'deployed_at': session.deployed_at.isoformat(),
                }

        except SitemapEditSession.DoesNotExist:
            return {'error': True, 'message': 'Session not found'}
        except Exception as e:
            self.log_error(f"Failed to deploy session: {e}")
            return {'error': True, 'message': str(e)}

    def _apply_session_changes(self, session):
        """Apply session changes to entries (mark as active, remove deleted)"""
        from ..models import SitemapEntry

        # Delete entries marked for removal
        SitemapEntry.objects.filter(
            domain=session.domain,
            status='pending_remove'
        ).delete()

        # Mark pending entries as active
        SitemapEntry.objects.filter(
            domain=session.domain,
            status__in=['pending_add', 'pending_modify']
        ).update(status='active')

    # =========================================================================
    # Diff & Changes
    # =========================================================================

    def get_session_diff(self, session_id: int) -> Dict:
        """
        Get diff of changes in a session.

        Args:
            session_id: Edit session ID

        Returns:
            Diff data
        """
        from ..models import SitemapEditSession, SitemapEntryChange

        try:
            session = SitemapEditSession.objects.get(id=session_id)

            changes = SitemapEntryChange.objects.filter(
                session=session
            ).select_related('entry', 'changed_by').order_by('-created_at')

            diff = {
                'added': [],
                'removed': [],
                'modified': [],
            }

            for change in changes:
                change_data = {
                    'url': change.url,
                    'old_values': change.old_values,
                    'new_values': change.new_values,
                    'source': change.source,
                    'changed_by': change.changed_by.username if change.changed_by else None,
                    'created_at': change.created_at.isoformat(),
                }

                if change.change_type == 'add':
                    diff['added'].append(change_data)
                elif change.change_type == 'remove':
                    diff['removed'].append(change_data)
                elif change.change_type == 'modify':
                    diff['modified'].append(change_data)

            return {
                'error': False,
                'session_id': session_id,
                'session_name': session.name,
                'diff': diff,
                'summary': {
                    'added': len(diff['added']),
                    'removed': len(diff['removed']),
                    'modified': len(diff['modified']),
                },
            }

        except SitemapEditSession.DoesNotExist:
            return {'error': True, 'message': 'Session not found'}
        except Exception as e:
            self.log_error(f"Failed to get session diff: {e}")
            return {'error': True, 'message': str(e)}

    # =========================================================================
    # URL Status Check
    # =========================================================================

    def check_entry_status(self, entry_id: int) -> Dict:
        """
        Check HTTP status of a sitemap entry URL.

        Args:
            entry_id: Entry ID

        Returns:
            Status check result
        """
        from ..models import SitemapEntry

        try:
            entry = SitemapEntry.objects.get(id=entry_id)

            response = self.session.head(entry.loc, timeout=10, allow_redirects=True)

            entry.http_status_code = response.status_code
            if response.url != entry.loc:
                entry.redirect_url = response.url
            entry.last_checked_at = timezone.now()
            entry.save(update_fields=['http_status_code', 'redirect_url', 'last_checked_at'])

            return {
                'error': False,
                'entry_id': entry_id,
                'url': entry.loc,
                'status_code': response.status_code,
                'redirect_url': entry.redirect_url,
                'is_ok': response.status_code < 400,
            }

        except SitemapEntry.DoesNotExist:
            return {'error': True, 'message': 'Entry not found'}
        except requests.RequestException as e:
            return {
                'error': True,
                'message': f"Request failed: {str(e)}"
            }
