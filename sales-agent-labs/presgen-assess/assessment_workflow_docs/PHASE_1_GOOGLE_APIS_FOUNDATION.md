# Phase 1: Google APIs Foundation
*Core Google Cloud and Workspace API Integration*

## Overview
Establishes foundational Google API integrations required for the certification assessment platform. Implements authentication, service initialization, and core API wrappers for Google Cloud Platform services, Google Workspace APIs, and supporting infrastructure.

## 1.1 Authentication and Authorization

### 1.1.1 Service Account Configuration
```python
# /presgen-assess/src/integrations/google/auth_manager.py
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.auth import default
import json
import os
from typing import Dict, Optional, List

class GoogleAuthManager:
    """
    Centralized authentication manager for all Google services.
    Handles service account credentials, OAuth flows, and scope management.
    """

    # Required scopes for different Google services
    SCOPES = {
        'sheets': [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ],
        'forms': [
            'https://www.googleapis.com/auth/forms.body',
            'https://www.googleapis.com/auth/forms.responses.readonly',
            'https://www.googleapis.com/auth/drive.file'
        ],
        'drive': [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/drive.metadata'
        ],
        'slides': [
            'https://www.googleapis.com/auth/presentations',
            'https://www.googleapis.com/auth/drive.file'
        ],
        'gmail': [
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.readonly'
        ],
        'cloud_storage': [
            'https://www.googleapis.com/auth/cloud-platform',
            'https://www.googleapis.com/auth/devstorage.read_write'
        ],
        'vertex_ai': [
            'https://www.googleapis.com/auth/cloud-platform'
        ]
    }

    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        self._credentials_cache = {}

    def get_service_credentials(self, service_type: str) -> service_account.Credentials:
        """
        Get authenticated credentials for a specific Google service.
        Implements caching to avoid repeated credential creation.
        """
        if service_type not in self.SCOPES:
            raise ValueError(f"Unknown service type: {service_type}")

        cache_key = f"{service_type}_{self.credentials_path}"

        if cache_key in self._credentials_cache:
            credentials = self._credentials_cache[cache_key]
            if credentials.expired:
                credentials.refresh(Request())
            return credentials

        # Load service account credentials
        if self.credentials_path and os.path.exists(self.credentials_path):
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=self.SCOPES[service_type]
            )
        else:
            # Fallback to default credentials (useful for Cloud environments)
            credentials, _ = default(scopes=self.SCOPES[service_type])

        self._credentials_cache[cache_key] = credentials
        return credentials

    def get_oauth_flow_url(self, service_type: str, redirect_uri: str) -> str:
        """
        Generate OAuth authorization URL for services requiring user consent.
        Used for Google Workspace APIs that need user authorization.
        """
        from google_auth_oauthlib.flow import Flow

        # Load OAuth client configuration
        oauth_config_path = os.getenv('GOOGLE_OAUTH_CLIENT_CONFIG', 'oauth_client_config.json')

        flow = Flow.from_client_secrets_file(
            oauth_config_path,
            scopes=self.SCOPES[service_type]
        )
        flow.redirect_uri = redirect_uri

        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )

        return authorization_url

    def exchange_oauth_code(self, service_type: str, code: str, redirect_uri: str):
        """
        Exchange OAuth authorization code for credentials.
        Stores credentials for future use.
        """
        from google_auth_oauthlib.flow import Flow

        oauth_config_path = os.getenv('GOOGLE_OAUTH_CLIENT_CONFIG', 'oauth_client_config.json')

        flow = Flow.from_client_secrets_file(
            oauth_config_path,
            scopes=self.SCOPES[service_type]
        )
        flow.redirect_uri = redirect_uri

        flow.fetch_token(code=code)

        # Store credentials securely
        credentials_data = {
            'token': flow.credentials.token,
            'refresh_token': flow.credentials.refresh_token,
            'token_uri': flow.credentials.token_uri,
            'client_id': flow.credentials.client_id,
            'client_secret': flow.credentials.client_secret,
            'scopes': flow.credentials.scopes
        }

        # Save to secure storage (implement based on your security requirements)
        self._store_oauth_credentials(service_type, credentials_data)

        return flow.credentials

    def _store_oauth_credentials(self, service_type: str, credentials_data: Dict):
        """
        Store OAuth credentials securely.
        Implement based on your security and compliance requirements.
        """
        # This is a simplified implementation - in production, use secure storage
        credentials_dir = os.path.expanduser('~/.presgen_credentials')
        os.makedirs(credentials_dir, exist_ok=True)

        credentials_file = os.path.join(credentials_dir, f'{service_type}_oauth.json')
        with open(credentials_file, 'w') as f:
            json.dump(credentials_data, f, indent=2)

        # Set restrictive file permissions
        os.chmod(credentials_file, 0o600)
```

### 1.1.2 API Client Factory
```python
# /presgen-assess/src/integrations/google/client_factory.py
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.cloud import storage, secretmanager
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class GoogleClientFactory:
    """
    Factory for creating authenticated Google API clients.
    Centralizes client creation and configuration.
    """

    def __init__(self, auth_manager: GoogleAuthManager):
        self.auth_manager = auth_manager
        self._client_cache = {}

    def get_sheets_client(self):
        """Get authenticated Google Sheets API client."""
        return self._get_or_create_client('sheets', 'sheets', 'v4')

    def get_forms_client(self):
        """Get authenticated Google Forms API client."""
        return self._get_or_create_client('forms', 'forms', 'v1')

    def get_drive_client(self):
        """Get authenticated Google Drive API client."""
        return self._get_or_create_client('drive', 'drive', 'v3')

    def get_slides_client(self):
        """Get authenticated Google Slides API client."""
        return self._get_or_create_client('slides', 'slides', 'v1')

    def get_gmail_client(self):
        """Get authenticated Gmail API client."""
        return self._get_or_create_client('gmail', 'gmail', 'v1')

    def get_storage_client(self):
        """Get authenticated Google Cloud Storage client."""
        cache_key = 'cloud_storage'

        if cache_key not in self._client_cache:
            credentials = self.auth_manager.get_service_credentials('cloud_storage')
            self._client_cache[cache_key] = storage.Client(credentials=credentials)

        return self._client_cache[cache_key]

    def get_secret_manager_client(self):
        """Get authenticated Secret Manager client."""
        cache_key = 'secret_manager'

        if cache_key not in self._client_cache:
            credentials = self.auth_manager.get_service_credentials('cloud_storage')
            self._client_cache[cache_key] = secretmanager.SecretManagerServiceClient(
                credentials=credentials
            )

        return self._client_cache[cache_key]

    def _get_or_create_client(self, service_type: str, service_name: str, version: str):
        """
        Create or retrieve cached API client.
        Implements connection pooling and error handling.
        """
        cache_key = f"{service_name}_{version}"

        if cache_key not in self._client_cache:
            try:
                credentials = self.auth_manager.get_service_credentials(service_type)

                client = build(
                    service_name,
                    version,
                    credentials=credentials,
                    cache_discovery=False  # Avoid caching issues in production
                )

                self._client_cache[cache_key] = client
                logger.info(f"Created {service_name} {version} API client")

            except Exception as e:
                logger.error(f"Failed to create {service_name} client: {str(e)}")
                raise

        return self._client_cache[cache_key]

    def clear_cache(self):
        """Clear client cache. Useful for credential refresh scenarios."""
        self._client_cache.clear()
        logger.info("Cleared Google API client cache")
```

## 1.2 Google Cloud Platform Integration

### 1.2.1 Cloud Storage Service
```python
# /presgen-assess/src/integrations/google/storage_service.py
from google.cloud import storage
from google.cloud.exceptions import NotFound, GoogleCloudError
from typing import Optional, List, Dict, BinaryIO
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CloudStorageService:
    """
    Service for managing Google Cloud Storage operations.
    Handles file uploads, downloads, and metadata management.
    """

    def __init__(self, client_factory: GoogleClientFactory, default_bucket: str):
        self.client_factory = client_factory
        self.default_bucket = default_bucket
        self.client = None

    @property
    def storage_client(self):
        """Lazy initialization of storage client."""
        if self.client is None:
            self.client = self.client_factory.get_storage_client()
        return self.client

    async def upload_file(
        self,
        file_content: BinaryIO,
        destination_path: str,
        bucket_name: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Upload file to Google Cloud Storage.
        Returns file information including public URL.
        """
        bucket_name = bucket_name or self.default_bucket

        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(destination_path)

            # Set metadata if provided
            if metadata:
                blob.metadata = metadata

            # Upload file
            blob.upload_from_file(
                file_content,
                content_type=content_type,
                rewind=True
            )

            logger.info(f"Uploaded file to gs://{bucket_name}/{destination_path}")

            return {
                'bucket': bucket_name,
                'path': destination_path,
                'public_url': blob.public_url,
                'media_link': blob.media_link,
                'size_bytes': blob.size,
                'content_type': blob.content_type,
                'created': blob.time_created.isoformat() if blob.time_created else None
            }

        except GoogleCloudError as e:
            logger.error(f"Failed to upload file: {str(e)}")
            raise

    async def download_file(
        self,
        source_path: str,
        bucket_name: Optional[str] = None
    ) -> bytes:
        """Download file from Google Cloud Storage."""
        bucket_name = bucket_name or self.default_bucket

        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(source_path)

            if not blob.exists():
                raise NotFound(f"File not found: gs://{bucket_name}/{source_path}")

            content = blob.download_as_bytes()
            logger.info(f"Downloaded file from gs://{bucket_name}/{source_path}")

            return content

        except GoogleCloudError as e:
            logger.error(f"Failed to download file: {str(e)}")
            raise

    async def generate_signed_url(
        self,
        blob_path: str,
        bucket_name: Optional[str] = None,
        expiration_hours: int = 24,
        method: str = 'GET'
    ) -> str:
        """
        Generate signed URL for temporary access to private files.
        Useful for secure file sharing and downloads.
        """
        bucket_name = bucket_name or self.default_bucket

        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)

            expiration = datetime.utcnow() + timedelta(hours=expiration_hours)

            signed_url = blob.generate_signed_url(
                expiration=expiration,
                method=method,
                version='v4'
            )

            logger.info(f"Generated signed URL for gs://{bucket_name}/{blob_path}")
            return signed_url

        except GoogleCloudError as e:
            logger.error(f"Failed to generate signed URL: {str(e)}")
            raise

    async def list_files(
        self,
        prefix: Optional[str] = None,
        bucket_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """List files in bucket with optional prefix filter."""
        bucket_name = bucket_name or self.default_bucket

        try:
            bucket = self.storage_client.bucket(bucket_name)
            blobs = bucket.list_blobs(prefix=prefix, max_results=limit)

            files = []
            for blob in blobs:
                files.append({
                    'name': blob.name,
                    'size_bytes': blob.size,
                    'content_type': blob.content_type,
                    'created': blob.time_created.isoformat() if blob.time_created else None,
                    'updated': blob.updated.isoformat() if blob.updated else None,
                    'public_url': blob.public_url,
                    'metadata': blob.metadata or {}
                })

            logger.info(f"Listed {len(files)} files from gs://{bucket_name}")
            return files

        except GoogleCloudError as e:
            logger.error(f"Failed to list files: {str(e)}")
            raise

    async def delete_file(
        self,
        file_path: str,
        bucket_name: Optional[str] = None
    ) -> bool:
        """Delete file from Google Cloud Storage."""
        bucket_name = bucket_name or self.default_bucket

        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(file_path)

            if blob.exists():
                blob.delete()
                logger.info(f"Deleted file gs://{bucket_name}/{file_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: gs://{bucket_name}/{file_path}")
                return False

        except GoogleCloudError as e:
            logger.error(f"Failed to delete file: {str(e)}")
            raise

    async def copy_file(
        self,
        source_path: str,
        destination_path: str,
        source_bucket: Optional[str] = None,
        destination_bucket: Optional[str] = None
    ) -> Dict[str, str]:
        """Copy file within or between buckets."""
        source_bucket = source_bucket or self.default_bucket
        destination_bucket = destination_bucket or self.default_bucket

        try:
            source_bucket_obj = self.storage_client.bucket(source_bucket)
            source_blob = source_bucket_obj.blob(source_path)

            destination_bucket_obj = self.storage_client.bucket(destination_bucket)

            copied_blob = source_bucket_obj.copy_blob(
                source_blob, destination_bucket_obj, destination_path
            )

            logger.info(
                f"Copied file from gs://{source_bucket}/{source_path} "
                f"to gs://{destination_bucket}/{destination_path}"
            )

            return {
                'source_bucket': source_bucket,
                'source_path': source_path,
                'destination_bucket': destination_bucket,
                'destination_path': destination_path,
                'copied_blob_url': copied_blob.public_url
            }

        except GoogleCloudError as e:
            logger.error(f"Failed to copy file: {str(e)}")
            raise
```

### 1.2.2 Secret Management
```python
# /presgen-assess/src/integrations/google/secrets_service.py
from google.cloud import secretmanager
from google.cloud.exceptions import NotFound
from typing import Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)

class SecretsService:
    """
    Service for managing Google Secret Manager operations.
    Handles secure storage and retrieval of API keys, tokens, and configuration.
    """

    def __init__(self, client_factory: GoogleClientFactory, project_id: str):
        self.client_factory = client_factory
        self.project_id = project_id
        self.client = None

    @property
    def secrets_client(self):
        """Lazy initialization of secrets client."""
        if self.client is None:
            self.client = self.client_factory.get_secret_manager_client()
        return self.client

    async def get_secret(self, secret_name: str, version: str = "latest") -> str:
        """
        Retrieve secret value from Google Secret Manager.
        Returns the secret as a string.
        """
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"

            response = self.secrets_client.access_secret_version(
                request={"name": name}
            )

            secret_value = response.payload.data.decode("UTF-8")
            logger.info(f"Retrieved secret: {secret_name}")

            return secret_value

        except NotFound:
            logger.error(f"Secret not found: {secret_name}")
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {str(e)}")
            raise

    async def get_secret_json(self, secret_name: str, version: str = "latest") -> Dict:
        """
        Retrieve secret value and parse as JSON.
        Useful for storing configuration objects.
        """
        try:
            secret_value = await self.get_secret(secret_name, version)
            return json.loads(secret_value)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse secret {secret_name} as JSON: {str(e)}")
            raise

    async def create_secret(self, secret_name: str, secret_value: str) -> str:
        """
        Create a new secret in Google Secret Manager.
        Returns the secret resource name.
        """
        try:
            parent = f"projects/{self.project_id}"

            # Create the secret
            secret = self.secrets_client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_name,
                    "secret": {"replication": {"automatic": {}}},
                }
            )

            # Add the secret version
            version_response = self.secrets_client.add_secret_version(
                request={
                    "parent": secret.name,
                    "payload": {"data": secret_value.encode("UTF-8")},
                }
            )

            logger.info(f"Created secret: {secret_name}")
            return version_response.name

        except Exception as e:
            logger.error(f"Failed to create secret {secret_name}: {str(e)}")
            raise

    async def update_secret(self, secret_name: str, secret_value: str) -> str:
        """
        Update existing secret with new value.
        Creates a new version of the secret.
        """
        try:
            parent = f"projects/{self.project_id}/secrets/{secret_name}"

            response = self.secrets_client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": secret_value.encode("UTF-8")},
                }
            )

            logger.info(f"Updated secret: {secret_name}")
            return response.name

        except Exception as e:
            logger.error(f"Failed to update secret {secret_name}: {str(e)}")
            raise

    async def delete_secret(self, secret_name: str) -> bool:
        """Delete secret from Google Secret Manager."""
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}"

            self.secrets_client.delete_secret(request={"name": name})
            logger.info(f"Deleted secret: {secret_name}")

            return True

        except NotFound:
            logger.warning(f"Secret not found for deletion: {secret_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete secret {secret_name}: {str(e)}")
            raise
```

## 1.3 Error Handling and Retry Logic

### 1.3.1 API Error Handler
```python
# /presgen-assess/src/integrations/google/error_handler.py
from googleapiclient.errors import HttpError
from google.cloud.exceptions import GoogleCloudError
from google.auth.exceptions import RefreshError
import time
import random
import logging
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

class GoogleAPIErrorHandler:
    """
    Centralized error handling and retry logic for Google API operations.
    Implements exponential backoff and rate limit handling.
    """

    # HTTP status codes that should trigger retries
    RETRY_STATUS_CODES = {
        429,  # Too Many Requests
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504   # Gateway Timeout
    }

    # Default retry configuration
    DEFAULT_RETRY_CONFIG = {
        'max_retries': 3,
        'base_delay': 1.0,
        'max_delay': 60.0,
        'exponential_base': 2.0,
        'jitter': True
    }

    @staticmethod
    def with_retry(
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """
        Decorator for adding retry logic to Google API calls.
        Implements exponential backoff with optional jitter.
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                last_exception = None

                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)

                    except HttpError as e:
                        last_exception = e

                        if not GoogleAPIErrorHandler._should_retry(e, attempt, max_retries):
                            logger.error(f"HTTP error in {func.__name__}: {e}")
                            raise

                        delay = GoogleAPIErrorHandler._calculate_delay(
                            attempt, base_delay, max_delay, exponential_base, jitter
                        )

                        logger.warning(
                            f"Retrying {func.__name__} after {delay:.2f}s "
                            f"(attempt {attempt + 1}/{max_retries + 1}). Error: {e}"
                        )

                        await asyncio.sleep(delay)

                    except GoogleCloudError as e:
                        last_exception = e

                        if not GoogleAPIErrorHandler._should_retry_cloud_error(e, attempt, max_retries):
                            logger.error(f"Google Cloud error in {func.__name__}: {e}")
                            raise

                        delay = GoogleAPIErrorHandler._calculate_delay(
                            attempt, base_delay, max_delay, exponential_base, jitter
                        )

                        logger.warning(
                            f"Retrying {func.__name__} after {delay:.2f}s "
                            f"(attempt {attempt + 1}/{max_retries + 1}). Error: {e}"
                        )

                        await asyncio.sleep(delay)

                    except RefreshError as e:
                        logger.error(f"Authentication error in {func.__name__}: {e}")
                        raise  # Don't retry auth errors

                    except Exception as e:
                        logger.error(f"Unexpected error in {func.__name__}: {e}")
                        raise

                # If we get here, all retries failed
                logger.error(f"All retries failed for {func.__name__}")
                raise last_exception

            return wrapper
        return decorator

    @staticmethod
    def _should_retry(error: HttpError, attempt: int, max_retries: int) -> bool:
        """Determine if an HTTP error should trigger a retry."""
        if attempt >= max_retries:
            return False

        status_code = error.resp.status

        # Always retry on rate limits and server errors
        if status_code in GoogleAPIErrorHandler.RETRY_STATUS_CODES:
            return True

        # Check for specific error conditions
        error_content = error.content.decode('utf-8') if error.content else ''

        # Retry on quota exceeded errors
        if 'quotaExceeded' in error_content or 'rateLimitExceeded' in error_content:
            return True

        return False

    @staticmethod
    def _should_retry_cloud_error(error: GoogleCloudError, attempt: int, max_retries: int) -> bool:
        """Determine if a Google Cloud error should trigger a retry."""
        if attempt >= max_retries:
            return False

        # Retry on transient errors
        if hasattr(error, 'code'):
            if error.code in [429, 500, 502, 503, 504]:
                return True

        return False

    @staticmethod
    def _calculate_delay(
        attempt: int,
        base_delay: float,
        max_delay: float,
        exponential_base: float,
        jitter: bool
    ) -> float:
        """Calculate delay for exponential backoff with optional jitter."""
        delay = base_delay * (exponential_base ** attempt)
        delay = min(delay, max_delay)

        if jitter:
            # Add random jitter to avoid thundering herd
            jitter_range = delay * 0.1
            delay += random.uniform(-jitter_range, jitter_range)

        return max(delay, 0)

class RateLimiter:
    """
    Rate limiter for Google API calls.
    Prevents exceeding API quotas and rate limits.
    """

    def __init__(self, calls_per_second: float = 10):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0

    async def acquire(self):
        """Acquire permission to make an API call."""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time

        if time_since_last_call < self.min_interval:
            sleep_time = self.min_interval - time_since_last_call
            await asyncio.sleep(sleep_time)

        self.last_call_time = time.time()

# Example usage with rate limiting
sheets_rate_limiter = RateLimiter(calls_per_second=100)  # Google Sheets API limit
drive_rate_limiter = RateLimiter(calls_per_second=1000)  # Google Drive API limit
```

## 1.4 Configuration and Environment Setup

### 1.4.1 Google Services Configuration
```python
# /presgen-assess/src/config/google_config.py
from pydantic import BaseSettings, Field
from typing import Dict, List, Optional
import os

class GoogleAPIConfig(BaseSettings):
    """Configuration for Google API integrations."""

    # Authentication
    service_account_file: str = Field(
        default_factory=lambda: os.getenv('GOOGLE_APPLICATION_CREDENTIALS', ''),
        description="Path to Google service account JSON file"
    )
    oauth_client_config_file: str = Field(
        default='oauth_client_config.json',
        description="Path to OAuth client configuration file"
    )

    # Google Cloud Platform
    project_id: str = Field(
        default_factory=lambda: os.getenv('GOOGLE_CLOUD_PROJECT', ''),
        description="Google Cloud Project ID"
    )
    region: str = Field(
        default='us-central1',
        description="Google Cloud region"
    )

    # Cloud Storage
    storage_bucket: str = Field(
        default_factory=lambda: os.getenv('GOOGLE_STORAGE_BUCKET', ''),
        description="Default Google Cloud Storage bucket"
    )
    storage_prefix: str = Field(
        default='presgen-assess',
        description="Storage path prefix"
    )

    # API Rate Limits (requests per second)
    rate_limits: Dict[str, float] = {
        'sheets': 100,
        'forms': 60,
        'drive': 1000,
        'slides': 100,
        'gmail': 250,
        'storage': 1000
    }

    # Retry Configuration
    retry_config: Dict[str, int] = {
        'max_retries': 3,
        'base_delay_seconds': 1,
        'max_delay_seconds': 60
    }

    # API Timeouts (seconds)
    api_timeouts: Dict[str, int] = {
        'sheets': 30,
        'forms': 30,
        'drive': 60,
        'slides': 45,
        'gmail': 30,
        'storage': 120
    }

    # Feature Flags
    enable_caching: bool = True
    enable_metrics: bool = True
    enable_debug_logging: bool = False

    class Config:
        env_prefix = "GOOGLE_"
        case_sensitive = False

class GoogleWorkspaceConfig(BaseSettings):
    """Configuration specific to Google Workspace APIs."""

    # Domain and organization settings
    workspace_domain: Optional[str] = Field(
        default=None,
        description="Google Workspace domain for organization-wide operations"
    )
    admin_email: Optional[str] = Field(
        default=None,
        description="Admin email for domain-wide delegation"
    )

    # Default sharing settings
    default_sharing_settings: Dict[str, str] = {
        'sheets': 'restricted',  # restricted, organization, public
        'forms': 'restricted',
        'slides': 'restricted'
    }

    # Folder organization
    root_folder_name: str = 'PresGen Assessment'
    auto_create_folders: bool = True
    folder_permissions: Dict[str, List[str]] = {
        'admin': ['owner'],
        'instructor': ['writer'],
        'student': ['reader']
    }

    class Config:
        env_prefix = "WORKSPACE_"
        case_sensitive = False
```

### 1.4.2 Service Initialization
```python
# /presgen-assess/src/integrations/google/__init__.py
"""
Google API integrations package.
Provides centralized access to all Google services.
"""

from .auth_manager import GoogleAuthManager
from .client_factory import GoogleClientFactory
from .storage_service import CloudStorageService
from .secrets_service import SecretsService
from .error_handler import GoogleAPIErrorHandler, RateLimiter

class GoogleServices:
    """
    Main entry point for Google API services.
    Initializes and provides access to all Google integrations.
    """

    def __init__(self, config: GoogleAPIConfig):
        self.config = config

        # Initialize core components
        self.auth_manager = GoogleAuthManager(config.service_account_file)
        self.client_factory = GoogleClientFactory(self.auth_manager)

        # Initialize services
        self.storage = CloudStorageService(
            self.client_factory,
            config.storage_bucket
        )
        self.secrets = SecretsService(
            self.client_factory,
            config.project_id
        )

        # Initialize rate limiters
        self.rate_limiters = {
            service: RateLimiter(limit)
            for service, limit in config.rate_limits.items()
        }

    def get_sheets_client(self):
        """Get Google Sheets API client with rate limiting."""
        return RateLimitedClient(
            self.client_factory.get_sheets_client(),
            self.rate_limiters['sheets']
        )

    def get_forms_client(self):
        """Get Google Forms API client with rate limiting."""
        return RateLimitedClient(
            self.client_factory.get_forms_client(),
            self.rate_limiters['forms']
        )

    def get_drive_client(self):
        """Get Google Drive API client with rate limiting."""
        return RateLimitedClient(
            self.client_factory.get_drive_client(),
            self.rate_limiters['drive']
        )

    def get_slides_client(self):
        """Get Google Slides API client with rate limiting."""
        return RateLimitedClient(
            self.client_factory.get_slides_client(),
            self.rate_limiters['slides']
        )

class RateLimitedClient:
    """Wrapper that adds rate limiting to Google API clients."""

    def __init__(self, client, rate_limiter: RateLimiter):
        self.client = client
        self.rate_limiter = rate_limiter

    def __getattr__(self, name):
        """Proxy all attribute access to the underlying client."""
        attr = getattr(self.client, name)

        if callable(attr):
            return self._wrap_method(attr)
        return attr

    def _wrap_method(self, method):
        """Wrap API methods with rate limiting."""
        async def wrapper(*args, **kwargs):
            await self.rate_limiter.acquire()
            return method(*args, **kwargs)
        return wrapper

# Global instance - initialized in main application
google_services: Optional[GoogleServices] = None

def initialize_google_services(config: GoogleAPIConfig) -> GoogleServices:
    """Initialize global Google services instance."""
    global google_services
    google_services = GoogleServices(config)
    return google_services

def get_google_services() -> GoogleServices:
    """Get global Google services instance."""
    if google_services is None:
        raise RuntimeError("Google services not initialized. Call initialize_google_services() first.")
    return google_services
```

## 1.5 Testing Infrastructure

### 1.5.1 Integration Test Framework
```python
# /presgen-assess/tests/test_google_integration.py
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.integrations.google import GoogleServices, GoogleAPIConfig
from src.integrations.google.auth_manager import GoogleAuthManager

class TestGoogleIntegration:
    """Integration tests for Google API services."""

    @pytest.fixture
    def google_config(self):
        """Test configuration for Google services."""
        return GoogleAPIConfig(
            project_id="test-project",
            storage_bucket="test-bucket",
            service_account_file="test-credentials.json"
        )

    @pytest.fixture
    def google_services(self, google_config):
        """Google services instance for testing."""
        return GoogleServices(google_config)

    @pytest.mark.asyncio
    async def test_authentication_flow(self, google_services):
        """Test Google API authentication."""
        auth_manager = google_services.auth_manager

        # Test service account authentication
        with patch('google.oauth2.service_account.Credentials.from_service_account_file') as mock_creds:
            mock_creds.return_value = Mock()

            credentials = auth_manager.get_service_credentials('sheets')
            assert credentials is not None
            mock_creds.assert_called_once()

    @pytest.mark.asyncio
    async def test_storage_operations(self, google_services):
        """Test Google Cloud Storage operations."""
        storage_service = google_services.storage

        # Mock storage client
        with patch.object(storage_service, 'storage_client') as mock_client:
            mock_bucket = Mock()
            mock_blob = Mock()
            mock_bucket.blob.return_value = mock_blob
            mock_client.bucket.return_value = mock_bucket

            # Test file upload
            test_content = b"test file content"
            result = await storage_service.upload_file(
                file_content=BytesIO(test_content),
                destination_path="test/file.txt",
                content_type="text/plain"
            )

            assert 'bucket' in result
            assert 'path' in result
            mock_blob.upload_from_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_and_retry(self, google_services):
        """Test error handling and retry logic."""
        from googleapiclient.errors import HttpError
        from src.integrations.google.error_handler import GoogleAPIErrorHandler

        @GoogleAPIErrorHandler.with_retry(max_retries=2)
        async def failing_api_call():
            # Simulate API failure
            raise HttpError(
                resp=Mock(status=429),
                content=b'Rate limit exceeded'
            )

        # Test that retries are attempted
        with pytest.raises(HttpError):
            await failing_api_call()

    @pytest.mark.asyncio
    async def test_rate_limiting(self, google_services):
        """Test API rate limiting functionality."""
        import time

        rate_limiter = google_services.rate_limiters['sheets']

        # Test that rate limiter enforces delays
        start_time = time.time()

        await rate_limiter.acquire()
        await rate_limiter.acquire()

        elapsed = time.time() - start_time

        # Should have some delay between calls
        assert elapsed >= rate_limiter.min_interval

    @pytest.mark.integration
    async def test_live_api_calls(self, google_config):
        """
        Live integration tests with real Google APIs.
        Only run when GOOGLE_INTEGRATION_TEST=true environment variable is set.
        """
        import os
        if not os.getenv('GOOGLE_INTEGRATION_TEST'):
            pytest.skip("Live integration tests disabled")

        services = GoogleServices(google_config)

        # Test Google Drive API
        drive_client = services.get_drive_client()

        # List files in Drive (should not raise errors)
        try:
            response = drive_client.files().list(pageSize=1).execute()
            assert 'files' in response
        except Exception as e:
            pytest.fail(f"Live Google Drive API test failed: {e}")

        # Test Google Cloud Storage
        try:
            files = await services.storage.list_files(limit=1)
            assert isinstance(files, list)
        except Exception as e:
            pytest.fail(f"Live Cloud Storage test failed: {e}")

# Performance benchmarks
class TestGoogleAPIPerformance:
    """Performance tests for Google API operations."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_api_calls(self, google_services):
        """Test performance under concurrent load."""
        import asyncio
        import time

        async def make_api_call(client, call_id):
            """Simulate API call."""
            await asyncio.sleep(0.1)  # Simulate API latency
            return f"result_{call_id}"

        # Test concurrent calls with rate limiting
        start_time = time.time()

        tasks = [
            make_api_call(google_services.get_sheets_client(), i)
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time

        assert len(results) == 10
        assert all('result_' in result for result in results)

        # Should complete within reasonable time considering rate limits
        assert elapsed < 5.0  # Adjust based on actual rate limits
```

This completes Phase 1 - Google APIs Foundation, providing the core infrastructure needed for all Google service integrations in the certification assessment platform.

## Implementation Roadmap (Detailed)

1. **Credential & Scope Management**
   - Harden `GoogleAuthManager` to reconcile scopes per service and emit warnings when mandatory scopes are absent.
   - Build automated key rotation scripts plus Secret Manager integration for production deployments.
2. **Service Wrapper Build-Out**
   - Templatize Sheets, Forms, Drive, Storage, and Admin SDK wrappers with consistent retry/backoff decorators and structured error translation.
   - Expose interface protocols so higher layers can mock Google clients in unit tests.
3. **Configuration Governance**
   - Document config precedence (`env`, YAML, Secret Manager) and validate on startup.
   - Provide CLI utilities for seeding shared drives, forms templates, and default storage buckets.
4. **Quota & Rate-Limit Protection**
   - Implement adaptive rate control (token bucket) with metrics-backed thresholds.
   - Add caching for read-heavy endpoints (e.g., Drive metadata) to reduce API consumption.
5. **Integration Hooks for Downstream Phases**
   - Publish helper functions for Drive folder provisioning, Sheets tab creation, and Form duplication to be invoked by workflow orchestrator phases.

## Test-Driven Development Strategy

1. **Auth Flow Tests**
   - TDD service-account loading, OAuth refresh, and error propagation (e.g., missing key file) using fixtures.
   - Validate scope merging with explicit tests asserting correct `SCOPES` union.
2. **Client Wrapper Tests**
   - Mock Google APIs via `pytest-httpx`/`responses` to ensure retries, pagination, and error translation behave as expected.
   - Confirm that Drive uploads honor MIME types and backup storage path rules.
3. **Rate Limiting & Backoff**
   - Simulate HTTP 429/5xx responses and assert exponential backoff with jitter plus logging occurs.
4. **Integration Smoke Tests**
   - `pytest -m google_live` optional tests to hit sandbox projects verifying credentials, necessary for release gates.

## Logging & Observability Enhancements

1. **Structured API Logging**
   - Log each Google API call with service/method, latency, quota cost, correlation ID, and retry attempts.
   - Append audit entries to workflow `step_execution_log` when operations are part of a workflow.
2. **Metrics & Alerts**
   - Record Prometheus counters (`google.forms.requests_total`) and histograms for latency; set alerts when error ratios exceed thresholds.
3. **Credential Health Monitoring**
   - Emit warnings when tokens approach expiration or keys are older than rotation SLA.
4. **Debug Artefacts**
   - Provide optional verbose logging (guarded by env flag) to dump sanitized request/response bodies during development.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create detailed Phase 1 document - Google APIs Foundation", "status": "completed", "activeForm": "Creating detailed Phase 1 document - Google APIs Foundation"}, {"content": "Create detailed Phase 2 document - Google Forms Automation", "status": "in_progress", "activeForm": "Creating detailed Phase 2 document - Google Forms Automation"}, {"content": "Create detailed Phase 3 document - Response Collection Pipeline", "status": "pending", "activeForm": "Creating detailed Phase 3 document - Response Collection Pipeline"}, {"content": "Create detailed Phase 4 document - PresGen-Core Integration", "status": "pending", "activeForm": "Creating detailed Phase 4 document - PresGen-Core Integration"}, {"content": "Create detailed Phase 5 document - PresGen-Avatar Integration", "status": "pending", "activeForm": "Creating detailed Phase 5 document - PresGen-Avatar Integration"}, {"content": "Fix UUID serialization issue in enhanced logging", "status": "completed", "activeForm": "Fixing UUID serialization issue in enhanced logging"}]
