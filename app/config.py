"""
Configuration settings for the Menu Image Analyzer application.
"""

import os
import secrets
from typing import Dict, Any, Optional
import logging

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip loading .env file
    pass

logger = logging.getLogger(__name__)


class SecurityConfig:
    """Security-focused configuration management."""
    
    @staticmethod
    def get_secret_key() -> str:
        """
        Get or generate a secure secret key.
        
        Returns:
            Secure secret key for Flask sessions
        """
        secret_key = os.environ.get('SECRET_KEY')
        
        if not secret_key:
            # Generate a secure random key for development
            secret_key = secrets.token_urlsafe(32)
            logger.warning("No SECRET_KEY found in environment. Generated temporary key for this session.")
            logger.warning("For production, set SECRET_KEY environment variable to a secure random value.")
        
        return secret_key
    
    @staticmethod
    def validate_api_key(key_name: str, api_key: Optional[str]) -> bool:
        """
        Validate that an API key is present and has minimum security requirements.
        
        Args:
            key_name: Name of the API key for logging
            api_key: The API key to validate
            
        Returns:
            True if key is valid, False otherwise
        """
        if not api_key:
            logger.warning(f"{key_name} not configured")
            return False
        
        # Basic validation - API keys should be reasonably long
        if len(api_key) < 10:
            logger.error(f"{key_name} appears to be too short or invalid")
            return False
        
        # Check for placeholder values
        placeholder_values = ['your-api-key-here', 'change-me', 'placeholder', 'test']
        if any(placeholder in api_key.lower() for placeholder in placeholder_values):
            logger.error(f"{key_name} appears to be a placeholder value")
            return False
        
        return True
    
    @staticmethod
    def get_cors_origins() -> list:
        """
        Get allowed CORS origins from environment.
        
        Returns:
            List of allowed origins
        """
        cors_origins = os.environ.get('CORS_ORIGINS', '')
        
        if cors_origins:
            # Split by comma and strip whitespace
            origins = [origin.strip() for origin in cors_origins.split(',')]
            return [origin for origin in origins if origin]  # Filter empty strings
        
        # Default CORS settings based on environment
        flask_env = os.environ.get('FLASK_ENV', 'development')
        
        if flask_env == 'development':
            return ['http://localhost:3000', 'http://localhost:5000', 'http://127.0.0.1:5000']
        elif flask_env == 'production':
            # In production, be more restrictive
            return []  # Must be explicitly configured
        else:
            return ['*']  # Testing environment


class Config:
    """Base configuration class with enhanced security."""
    
    def __init__(self):
        """Initialize configuration with security validation."""
        self._validate_environment()
    
    # Flask settings
    SECRET_KEY = SecurityConfig.get_secret_key()
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Security settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # CORS settings
    CORS_ORIGINS = SecurityConfig.get_cors_origins()
    
    # Upload settings
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    
    # API settings - with validation
    OCR_API_KEY = os.environ.get('OCR_API_KEY', '')
    GOOGLE_SEARCH_API_KEY = os.environ.get('GOOGLE_SEARCH_API_KEY', '')
    GOOGLE_SEARCH_ENGINE_ID = os.environ.get('GOOGLE_SEARCH_ENGINE_ID', '')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    
    # Alternative API key names for flexibility
    GOOGLE_VISION_API_KEY = os.environ.get('GOOGLE_VISION_API_KEY', '') or OCR_API_KEY
    
    # Processing settings
    MAX_DISHES_PER_MENU = 50
    MAX_IMAGES_PER_DISH = 5
    REQUEST_TIMEOUT = 30  # seconds
    
    # Rate limiting settings
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_DEFAULT = "100 per hour"
    
    # Cache settings
    ENABLE_CACHING = True
    CACHE_TTL = 3600  # 1 hour in seconds
    
    def _validate_environment(self) -> None:
        """Validate environment configuration and log warnings."""
        # Validate API keys
        api_keys = {
            'OCR_API_KEY': self.OCR_API_KEY,
            'GOOGLE_SEARCH_API_KEY': self.GOOGLE_SEARCH_API_KEY,
            'OPENAI_API_KEY': self.OPENAI_API_KEY
        }
        
        for key_name, key_value in api_keys.items():
            SecurityConfig.validate_api_key(key_name, key_value)
        
        # Validate required settings
        if not self.GOOGLE_SEARCH_ENGINE_ID:
            logger.warning("GOOGLE_SEARCH_ENGINE_ID not configured - image search will not work")
    
    def get_api_config(self) -> Dict[str, Any]:
        """
        Get API configuration without exposing sensitive keys.
        
        Returns:
            Dictionary with API configuration status
        """
        return {
            'ocr_configured': bool(self.OCR_API_KEY or self.GOOGLE_VISION_API_KEY),
            'image_search_configured': bool(self.GOOGLE_SEARCH_API_KEY and self.GOOGLE_SEARCH_ENGINE_ID),
            'ai_description_configured': bool(self.OPENAI_API_KEY),
            'cors_origins': self.CORS_ORIGINS
        }
    
    def mask_sensitive_config(self) -> Dict[str, Any]:
        """
        Get configuration with sensitive values masked for logging/debugging.
        
        Returns:
            Dictionary with masked sensitive values
        """
        def mask_key(key: str) -> str:
            if not key:
                return "Not configured"
            if len(key) <= 8:
                return "*" * len(key)
            return key[:4] + "*" * (len(key) - 8) + key[-4:]
        
        return {
            'SECRET_KEY': mask_key(self.SECRET_KEY),
            'OCR_API_KEY': mask_key(self.OCR_API_KEY),
            'GOOGLE_SEARCH_API_KEY': mask_key(self.GOOGLE_SEARCH_API_KEY),
            'GOOGLE_SEARCH_ENGINE_ID': mask_key(self.GOOGLE_SEARCH_ENGINE_ID),
            'OPENAI_API_KEY': mask_key(self.OPENAI_API_KEY),
            'CORS_ORIGINS': self.CORS_ORIGINS,
            'MAX_CONTENT_LENGTH': self.MAX_CONTENT_LENGTH,
            'REQUEST_TIMEOUT': self.REQUEST_TIMEOUT
        }


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    
    # More permissive CORS for development
    CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:5000', 'http://127.0.0.1:5000']
    
    # Disable secure cookies for development
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production configuration with enhanced security."""
    DEBUG = False
    TESTING = False
    
    def __init__(self):
        super().__init__()
        self._validate_production_requirements()
    
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_ENABLED = True
    
    def _validate_production_requirements(self) -> None:
        """Validate that all required settings are configured for production."""
        required_env_vars = [
            'SECRET_KEY',
            'OCR_API_KEY',
            'GOOGLE_SEARCH_API_KEY',
            'GOOGLE_SEARCH_ENGINE_ID',
            'OPENAI_API_KEY'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            error_msg = f"Missing required environment variables for production: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Validate CORS origins are explicitly set for production
        if not os.environ.get('CORS_ORIGINS'):
            logger.warning("CORS_ORIGINS not explicitly set for production. Using empty list (no CORS).")
            self.CORS_ORIGINS = []


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    
    # Use in-memory storage for testing
    UPLOAD_FOLDER = '/tmp/test_uploads'
    ENABLE_CACHING = False
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Use test API keys or mock services
    OCR_API_KEY = os.environ.get('TEST_OCR_API_KEY', 'test-key')
    GOOGLE_SEARCH_API_KEY = os.environ.get('TEST_GOOGLE_SEARCH_API_KEY', 'test-key')
    GOOGLE_SEARCH_ENGINE_ID = os.environ.get('TEST_GOOGLE_SEARCH_ENGINE_ID', 'test-engine')
    OPENAI_API_KEY = os.environ.get('TEST_OPENAI_API_KEY', 'test-key')


# Configuration mapping
config_map: Dict[str, Any] = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: str = None) -> Config:
    """
    Get configuration class based on environment.
    
    Args:
        config_name: Configuration name ('development', 'production', 'testing')
        
    Returns:
        Configuration class instance
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    config_class = config_map.get(config_name, DevelopmentConfig)
    return config_class()


def validate_api_credentials() -> Dict[str, bool]:
    """
    Validate all API credentials are properly configured.
    
    Returns:
        Dictionary with validation results for each service
    """
    config = get_config()
    
    return {
        'ocr_service': SecurityConfig.validate_api_key('OCR_API_KEY', config.OCR_API_KEY),
        'image_search': SecurityConfig.validate_api_key('GOOGLE_SEARCH_API_KEY', config.GOOGLE_SEARCH_API_KEY) and bool(config.GOOGLE_SEARCH_ENGINE_ID),
        'ai_description': SecurityConfig.validate_api_key('OPENAI_API_KEY', config.OPENAI_API_KEY)
    }