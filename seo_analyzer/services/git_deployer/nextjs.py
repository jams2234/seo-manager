"""
Next.js Project Handler
"""
import re
import logging
from pathlib import Path
from .base import ProjectDetector, MetadataUpdater
from .exceptions import FileNotFoundError as GitFileNotFoundError, MetadataUpdateError

logger = logging.getLogger(__name__)


class NextJSDetector(ProjectDetector):
    """Detector for Next.js projects"""

    CONFIG_FILES = [
        'next.config.ts',
        'next.config.js',
        'next.config.mjs',
    ]

    def can_handle(self, repo_path: Path) -> bool:
        """Check if repository is a Next.js project"""
        return any((repo_path / config).exists() for config in self.CONFIG_FILES)

    def get_name(self) -> str:
        return "Next.js"

    def get_priority(self) -> int:
        return 10  # High priority


class NextJSMetadataUpdater(MetadataUpdater):
    """Update metadata in Next.js projects"""

    LAYOUT_FILES = [
        'src/app/layout.tsx',
        'src/app/layout.js',
        'app/layout.tsx',
        'app/layout.js',
        'src/app/page.tsx',
        'src/app/page.js',
    ]

    # Enhanced regex patterns for matching metadata fields
    # Supports:
    # - Single quotes with escaped quotes
    # - Double quotes with escaped quotes
    # - Template literals (backticks)
    # - Multiline strings
    # - Escaped characters (\n, \t, \\, etc.)
    PATTERNS = {
        'title': {
            # Match: title: 'any text with \'escaped\' quotes'
            # The pattern [^'\\\\]* matches any character except ' and \
            # (?:\\\\.[^'\\\\]*)* matches \-escaped characters followed by more text
            'single': r"(title:\s*')((?:[^'\\]|\\.)*)(')",

            # Match: title: "any text with \"escaped\" quotes"
            'double': r'(title:\s*")((?:[^"\\]|\\.)*)(")',

            # Match: title: `any text with ${variables} and newlines`
            'template': r'(title:\s*`)((?:[^`\\]|\\.)*?)(`)',
        },
        'description': {
            'single': r"(description:\s*')((?:[^'\\]|\\.)*)(')",
            'double': r'(description:\s*")((?:[^"\\]|\\.)*)(")',
            'template': r'(description:\s*`)((?:[^`\\]|\\.)*?)(`)',
        },
    }

    def update_metadata(self, repo_path: Path, fixes: list) -> int:
        """Update Next.js metadata in layout or page files"""

        # Group fixes by field
        fixes_by_field = self._group_fixes_by_field(fixes)

        if not fixes_by_field['title'] and not fixes_by_field['description']:
            logger.warning("No title or description fixes provided")
            return 0

        # Find layout file
        layout_file = self._find_layout_file(repo_path)

        if not layout_file:
            error_msg = "Could not find Next.js layout or page file. Searched: " + ", ".join(self.LAYOUT_FILES)
            logger.warning(error_msg)
            raise GitFileNotFoundError(error_msg)

        try:
            # Read file
            with open(layout_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            modified = False

            # Update title
            if fixes_by_field['title']:
                new_title = fixes_by_field['title'].get('new_value', '')
                content, title_updated = self._update_field(content, 'title', new_title)
                if title_updated:
                    modified = True
                    logger.info(f"Updated title in {layout_file.name}")

            # Update description
            if fixes_by_field['description']:
                new_desc = fixes_by_field['description'].get('new_value', '')
                content, desc_updated = self._update_field(content, 'description', new_desc)
                if desc_updated:
                    modified = True
                    logger.info(f"Updated description in {layout_file.name}")

            # Write back if modified
            if modified:
                with open(layout_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                logger.info(f"Successfully updated Next.js file: {layout_file.relative_to(repo_path)}")
                return 1

            return 0

        except (IOError, OSError) as e:
            error_msg = f"Failed to read/write Next.js file {layout_file}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise MetadataUpdateError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error updating Next.js file {layout_file}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise MetadataUpdateError(error_msg)

    def _find_layout_file(self, repo_path: Path) -> Path:
        """Find the Next.js layout or page file"""
        for layout_file in self.LAYOUT_FILES:
            candidate = repo_path / layout_file
            if candidate.exists():
                logger.info(f"Found Next.js metadata file: {layout_file}")
                return candidate

        return None

    def _update_field(self, content: str, field: str, new_value: str) -> tuple:
        """
        Update a metadata field in the content

        Args:
            content: File content
            field: Field name ('title' or 'description')
            new_value: New value to set

        Returns:
            Tuple of (updated_content, was_modified)
        """
        # Escape special characters in the new value
        # Handle backslashes and quotes
        escaped_value = new_value.replace('\\', '\\\\')

        patterns = self.PATTERNS.get(field, {})

        # Try each pattern type (single, double, template)
        for quote_type, pattern in patterns.items():
            if re.search(pattern, content, re.DOTALL):
                # For single quotes, escape single quotes in value
                if quote_type == 'single':
                    escaped_value_final = escaped_value.replace("'", "\\'")
                # For double quotes, escape double quotes in value
                elif quote_type == 'double':
                    escaped_value_final = escaped_value.replace('"', '\\"')
                else:  # template literal
                    escaped_value_final = escaped_value

                # Replace the content
                updated_content = re.sub(
                    pattern,
                    rf"\1{escaped_value_final}\3",
                    content,
                    flags=re.DOTALL
                )

                logger.debug(f"Updated {field} using {quote_type} quote pattern")
                return updated_content, True

        logger.warning(f"Could not find {field} field in metadata")
        return content, False
