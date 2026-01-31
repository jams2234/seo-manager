"""
Base Google API Client with Service Account Authentication
"""
import os
import logging
from typing import List, Optional
from google.oauth2 import service_account
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings
import httplib2

logger = logging.getLogger(__name__)

# Configure httplib2 internal retry behavior
# Set to 1 to minimize internal retries and rely on our own retry logic
httplib2.RETRIES = 1


class GoogleAPIClient:
    """
    Base client for Google API services using Service Account authentication
    """

    def __init__(self, scopes: Optional[List[str]] = None):
        """
        Initialize Google API client with service account credentials

        Args:
            scopes: List of OAuth2 scopes required for the API
        """
        self.scopes = scopes or settings.GOOGLE_API_SCOPES
        self.credentials = None
        self.service_account_file = settings.GOOGLE_SERVICE_ACCOUNT_FILE

        self._authenticate()

    def _authenticate(self):
        """Authenticate using service account JSON file"""
        try:
            if not os.path.exists(self.service_account_file):
                raise FileNotFoundError(
                    f"Service account file not found: {self.service_account_file}"
                )

            self.credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=self.scopes
            )

            logger.info("Successfully authenticated with Google service account")

        except Exception as e:
            logger.error(f"Failed to authenticate with Google API: {e}")
            raise

    def build_service(self, service_name: str, version: str, timeout: int = 30):
        """
        Build a Google API service client with custom timeout

        Args:
            service_name: Name of the Google service (e.g., 'searchconsole', 'analytics')
            version: API version (e.g., 'v1', 'v3')
            timeout: HTTP timeout in seconds (default: 30s, balanced for URL Inspection API)

        Returns:
            Service client object
        """
        try:
            # Create fresh HTTP client for each service build
            # IMPORTANT: Do not reuse Http instances - they are not thread-safe
            # Connection caching in httplib2 causes SSL errors to persist
            # Each request gets a fresh instance to avoid SSL/connection issues
            http_client = httplib2.Http(
                timeout=timeout,
                disable_ssl_certificate_validation=False  # Keep SSL validation enabled
            )
            authorized_http = AuthorizedHttp(self.credentials, http=http_client)

            service = build(
                service_name,
                version,
                http=authorized_http,
                cache_discovery=False
            )
            logger.info(f"Built {service_name} {version} service with {timeout}s timeout")
            return service

        except HttpError as e:
            logger.error(f"HTTP error building service {service_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error building service {service_name}: {e}")
            raise

    @staticmethod
    def handle_api_error(error: Exception, context: str = "") -> dict:
        """
        Handle API errors and return standardized error response

        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred

        Returns:
            Dictionary with error details
        """
        if isinstance(error, HttpError):
            status_code = error.resp.status
            error_message = f"Google API HTTP {status_code} error"

            if status_code == 403:
                error_message = "Permission denied. Check API access and service account permissions."
            elif status_code == 404:
                error_message = "Resource not found. Verify the domain/property is added to Search Console."
            elif status_code == 429:
                error_message = "API quota exceeded. Try again later."
            elif status_code >= 500:
                error_message = "Google API server error. Try again later."

            logger.error(f"{context}: {error_message} - {error}")

            return {
                'error': True,
                'status_code': status_code,
                'message': error_message,
                'details': str(error)
            }
        else:
            logger.error(f"{context}: Unexpected error - {error}")
            return {
                'error': True,
                'status_code': 500,
                'message': str(error),
                'details': str(error)
            }
