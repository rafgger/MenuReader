"""
Configuration settings for the Menu Image Analyzer application.
"""

import os
from typing import Dict, Any


class Config:
    """Base configuration class."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Upload settings
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    
    # API settings
    OCR_API_KEY = os.environ.get('OCR_API_KEY', '')
    GOOGLE_SEARCH_API_KEY = os.environ.get('GOOGLE_SEARCH_API_KEY', '')
    GOOGLE_SEARCH_ENGINE_ID = os.environ.get('GOOGLE_SEARCH_ENGINE_ID', '')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    
    # Processing settings
    MAX_DISHES_PER_MENU = 50
    MAX_IMAGES_PER_DISH = 5
    REQUEST_TIMEOUT = 30  # seconds
    
    # Cache settings
    ENABLE_CACHING = True
    CACHE_TTL = 3600  # 1 hour in seconds


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    
    def __init__(self):
        super().__init__()
        # Override with more secure settings for production
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key:
            raise ValueError("SECRET_KEY environment variable must be set in production")
        self.SECRET_KEY = secret_key


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    
    # Use in-memory storage for testing
    UPLOAD_FOLDER = '/tmp/test_uploads'
    ENABLE_CACHING = False


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