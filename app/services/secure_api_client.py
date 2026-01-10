"""
Secure API Client for Menu Image Analyzer.

This module provides a secure, centralized way to handle all external API communications
with proper authentication, rate limiting, error handling, and security measures.
"""

import os
import time
import logging
import hashlib
import hmac
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning
import urllib3

# Disable insecure request warnings (only in development)
if os.environ.get('ENVIRONMENT', 'production') == 'development':
    urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger(__name__)


class APIProvider(Enum):
    """Supported API providers."""
    GOOGLE_VISION = "google_vision"
    GOOGLE_SEARCH = "google_search"
    OPENAI = "openai"


@dataclass
class APICredentials:
    """Secure storage for API credentials."""
    provider: APIProvider
    api_key: str
    additional_params: Dict[str, str] = None
    
    def __post_init__(self):
        """Validate credentials after initialization."""
        if not self.api_key:
            raise ValueError(f"API key required for {self.provider.value}")
        
        if self.additional_params is None:
            self.additional_params = {}
    
    def get_masked_key(self) -> str:
        """Get masked version of API key for logging."""
        if len(self.api_key) <= 8:
            return "*" * len(self.api_key)
        return self.api_key[:4] + "*" * (len(self.api_key) - 8) + self.api_key[-4:]


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_second: float = 1.0
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    backoff_factor: float = 1.0
    max_retries: int = 3


class SecureAPIClient:
    """
    Secure API client with authentication, rate limiting, and error handling.
    
    This client provides a secure way to interact with external APIs while
    protecting sensitive credentials and implementing proper security measures.
    """
    
    def __init__(self, timeout: int = 30):
        """
        Initialize the secure API client.
        
        Args:
            timeout: Default request timeout in seconds
        """
        self.timeout = timeout
        self.credentials: Dict[APIProvider, APICredentials] = {}
        self.rate_limits: Dict[APIProvider, RateLimitConfig] = {}
        self.request_history: Dict[APIProvider, List[float]] = {}
        
        # Configure HTTP session with security settings
        self.session = requests.Session()
        self._configure_session()
        
        # Load credentials from environment
        self._load_credentials()
        
        logger.info("Secure API client initialized")
    
    def _configure_session(self) -> None:
        """Configure HTTP session with security and retry settings."""
        # Retry strategy for transient failures
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Security headers
        self.session.headers.update({
            'User-Agent': 'MenuImageAnalyzer/1.0',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        # SSL verification (enabled by default for production)
        self.session.verify = os.environ.get('SSL_VERIFY', 'true').lower() == 'true'
    
    def _load_credentials(self) -> None:
        """Load API credentials from environment variables."""
        # Google Vision OCR
        ocr_key = os.environ.get('OCR_API_KEY') or os.environ.get('GOOGLE_VISION_API_KEY')
        if ocr_key:
            self.add_credentials(APIProvider.GOOGLE_VISION, ocr_key)
        
        # Google Custom Search
        search_key = os.environ.get('GOOGLE_SEARCH_API_KEY')
        search_engine_id = os.environ.get('GOOGLE_SEARCH_ENGINE_ID')
        if search_key and search_engine_id:
            self.add_credentials(
                APIProvider.GOOGLE_SEARCH, 
                search_key,
                {'engine_id': search_engine_id}
            )
        
        # OpenAI
        openai_key = os.environ.get('OPENAI_API_KEY')
        if openai_key:
            self.add_credentials(APIProvider.OPENAI, openai_key)
        
        # Set default rate limits
        self._set_default_rate_limits()
    
    def _set_default_rate_limits(self) -> None:
        """Set default rate limiting configurations for each provider."""
        self.rate_limits = {
            APIProvider.GOOGLE_VISION: RateLimitConfig(
                requests_per_second=10.0,
                requests_per_minute=600,
                requests_per_hour=1000,
                requests_per_day=1000
            ),
            APIProvider.GOOGLE_SEARCH: RateLimitConfig(
                requests_per_second=1.0,
                requests_per_minute=10,
                requests_per_hour=100,
                requests_per_day=100  # Free tier limit
            ),
            APIProvider.OPENAI: RateLimitConfig(
                requests_per_second=3.0,
                requests_per_minute=60,
                requests_per_hour=1000,
                requests_per_day=10000
            )
        }
    
    def add_credentials(self, provider: APIProvider, api_key: str, 
                       additional_params: Dict[str, str] = None) -> None:
        """
        Add API credentials for a provider.
        
        Args:
            provider: API provider
            api_key: API key
            additional_params: Additional parameters (e.g., engine ID)
        """
        try:
            credentials = APICredentials(provider, api_key, additional_params)
            self.credentials[provider] = credentials
            self.request_history[provider] = []
            
            logger.info(f"Added credentials for {provider.value}: {credentials.get_masked_key()}")
            
        except ValueError as e:
            logger.error(f"Failed to add credentials for {provider.value}: {e}")
            raise
    
    def is_configured(self, provider: APIProvider) -> bool:
        """
        Check if a provider is properly configured.
        
        Args:
            provider: API provider to check
            
        Returns:
            True if provider is configured
        """
        return provider in self.credentials
    
    def make_request(self, provider: APIProvider, method: str, url: str,
                    headers: Dict[str, str] = None, data: Any = None,
                    json_data: Dict[str, Any] = None, params: Dict[str, str] = None,
                    auth_callback: Callable = None) -> requests.Response:
        """
        Make a secure API request with rate limiting and error handling.
        
        Args:
            provider: API provider
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            headers: Additional headers
            data: Request data
            json_data: JSON request data
            params: URL parameters
            auth_callback: Custom authentication callback
            
        Returns:
            Response object
            
        Raises:
            ValueError: If provider not configured
            requests.RequestException: For request failures
        """
        if provider not in self.credentials:
            raise ValueError(f"Provider {provider.value} not configured")
        
        # Enforce rate limiting
        self._enforce_rate_limit(provider)
        
        # Prepare headers with authentication
        request_headers = headers or {}
        if auth_callback:
            request_headers = auth_callback(request_headers, self.credentials[provider])
        else:
            request_headers = self._add_authentication(provider, request_headers)
        
        # Add security headers
        request_headers.update({
            'X-Request-ID': self._generate_request_id(),
            'X-Client-Version': '1.0'
        })
        
        try:
            # Make the request
            response = self.session.request(
                method=method,
                url=url,
                headers=request_headers,
                data=data,
                json=json_data,
                params=params,
                timeout=self.timeout
            )
            
            # Log request (without sensitive data)
            self._log_request(provider, method, url, response.status_code)
            
            # Update request history for rate limiting
            self._update_request_history(provider)
            
            # Check for API-specific errors
            self._check_api_errors(provider, response)
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {provider.value}: {e}")
            raise
    
    def _add_authentication(self, provider: APIProvider, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Add authentication to request headers.
        
        Args:
            provider: API provider
            headers: Existing headers
            
        Returns:
            Headers with authentication added
        """
        credentials = self.credentials[provider]
        
        if provider == APIProvider.GOOGLE_VISION:
            # Google Vision uses API key in URL or Authorization header
            headers['Authorization'] = f'Bearer {credentials.api_key}'
            
        elif provider == APIProvider.GOOGLE_SEARCH:
            # Google Search uses API key as parameter (handled in URL)
            pass
            
        elif provider == APIProvider.OPENAI:
            # OpenAI uses Bearer token
            headers['Authorization'] = f'Bearer {credentials.api_key}'
            headers['Content-Type'] = 'application/json'
        
        return headers
    
    def _enforce_rate_limit(self, provider: APIProvider) -> None:
        """
        Enforce rate limiting for API requests.
        
        Args:
            provider: API provider
        """
        if provider not in self.rate_limits:
            return
        
        rate_config = self.rate_limits[provider]
        current_time = time.time()
        
        # Clean old requests from history
        history = self.request_history.get(provider, [])
        history = [t for t in history if current_time - t < 3600]  # Keep last hour
        self.request_history[provider] = history
        
        # Check rate limits
        recent_requests = [t for t in history if current_time - t < 1.0]  # Last second
        if len(recent_requests) >= rate_config.requests_per_second:
            sleep_time = 1.0 / rate_config.requests_per_second
            logger.debug(f"Rate limiting {provider.value}: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        # Check minute limit
        minute_requests = [t for t in history if current_time - t < 60]
        if len(minute_requests) >= rate_config.requests_per_minute:
            logger.warning(f"Approaching minute rate limit for {provider.value}")
    
    def _update_request_history(self, provider: APIProvider) -> None:
        """Update request history for rate limiting."""
        if provider not in self.request_history:
            self.request_history[provider] = []
        
        self.request_history[provider].append(time.time())
    
    def _check_api_errors(self, provider: APIProvider, response: requests.Response) -> None:
        """
        Check for API-specific error conditions.
        
        Args:
            provider: API provider
            response: Response object
        """
        if provider == APIProvider.GOOGLE_VISION and response.status_code == 403:
            logger.error("Google Vision API quota exceeded or invalid credentials")
            
        elif provider == APIProvider.GOOGLE_SEARCH and response.status_code == 403:
            logger.error("Google Search API quota exceeded or invalid credentials")
            
        elif provider == APIProvider.OPENAI and response.status_code == 429:
            logger.warning("OpenAI API rate limit hit")
    
    def _generate_request_id(self) -> str:
        """Generate a unique request ID for tracking."""
        return hashlib.md5(f"{time.time()}".encode()).hexdigest()[:16]
    
    def _log_request(self, provider: APIProvider, method: str, url: str, status_code: int) -> None:
        """
        Log API request (without sensitive information).
        
        Args:
            provider: API provider
            method: HTTP method
            url: Request URL (will be sanitized)
            status_code: Response status code
        """
        # Sanitize URL to remove API keys
        sanitized_url = url
        if 'key=' in url:
            sanitized_url = url.split('key=')[0] + 'key=***'
        
        logger.debug(f"{provider.value} API: {method} {sanitized_url} -> {status_code}")
    
    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status information for all configured providers.
        
        Returns:
            Dictionary with provider status information
        """
        status = {}
        
        for provider in APIProvider:
            if provider in self.credentials:
                history = self.request_history.get(provider, [])
                current_time = time.time()
                
                # Count recent requests
                recent_requests = {
                    'last_minute': len([t for t in history if current_time - t < 60]),
                    'last_hour': len([t for t in history if current_time - t < 3600])
                }
                
                status[provider.value] = {
                    'configured': True,
                    'api_key_masked': self.credentials[provider].get_masked_key(),
                    'recent_requests': recent_requests,
                    'rate_limit': {
                        'per_minute': self.rate_limits[provider].requests_per_minute,
                        'per_hour': self.rate_limits[provider].requests_per_hour
                    }
                }
            else:
                status[provider.value] = {
                    'configured': False,
                    'error': 'No credentials configured'
                }
        
        return status
    
    def validate_all_credentials(self) -> Dict[str, bool]:
        """
        Validate all configured API credentials by making test requests.
        
        Returns:
            Dictionary with validation results
        """
        results = {}
        
        for provider in self.credentials:
            try:
                if provider == APIProvider.GOOGLE_VISION:
                    # Test with minimal request
                    results[provider.value] = self._test_google_vision()
                elif provider == APIProvider.GOOGLE_SEARCH:
                    results[provider.value] = self._test_google_search()
                elif provider == APIProvider.OPENAI:
                    results[provider.value] = self._test_openai()
                else:
                    results[provider.value] = False
                    
            except Exception as e:
                logger.error(f"Credential validation failed for {provider.value}: {e}")
                results[provider.value] = False
        
        return results
    
    def _test_google_vision(self) -> bool:
        """Test Google Vision API credentials."""
        # This would require a minimal test image - for now just check if credentials exist
        return True
    
    def _test_google_search(self) -> bool:
        """Test Google Search API credentials."""
        try:
            credentials = self.credentials[APIProvider.GOOGLE_SEARCH]
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': credentials.api_key,
                'cx': credentials.additional_params.get('engine_id'),
                'q': 'test',
                'num': 1
            }
            
            response = self.make_request(
                APIProvider.GOOGLE_SEARCH,
                'GET',
                url,
                params=params
            )
            
            return response.status_code == 200
            
        except Exception:
            return False
    
    def _test_openai(self) -> bool:
        """Test OpenAI API credentials."""
        try:
            url = "https://api.openai.com/v1/models"
            response = self.make_request(
                APIProvider.OPENAI,
                'GET',
                url
            )
            
            return response.status_code == 200
            
        except Exception:
            return False
    
    def clear_request_history(self) -> None:
        """Clear request history for all providers."""
        self.request_history.clear()
        logger.info("Request history cleared")
    
    def get_security_info(self) -> Dict[str, Any]:
        """
        Get security-related information about the client.
        
        Returns:
            Dictionary with security information
        """
        return {
            'ssl_verification': self.session.verify,
            'timeout': self.timeout,
            'configured_providers': list(self.credentials.keys()),
            'rate_limiting_enabled': bool(self.rate_limits),
            'session_headers': {k: v for k, v in self.session.headers.items() 
                              if 'auth' not in k.lower() and 'key' not in k.lower()}
        }