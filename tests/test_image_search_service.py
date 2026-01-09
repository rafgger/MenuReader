"""
Tests for ImageSearchService.

This module contains unit tests for the image search functionality,
including API integration, quality filtering, caching, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from app.services.image_search_service import ImageSearchService
from app.models.data_models import FoodImage, RequestCache


class TestImageSearchService:
    """Test cases for ImageSearchService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.api_key = "test_api_key"
        self.search_engine_id = "test_engine_id"
        self.cache = RequestCache()
        self.service = ImageSearchService(
            api_key=self.api_key,
            search_engine_id=self.search_engine_id,
            cache=self.cache
        )
    
    def test_initialization(self):
        """Test service initialization."""
        assert self.service.api_key == self.api_key
        assert self.service.search_engine_id == self.search_engine_id
        assert self.service.cache is not None
        assert self.service.timeout == 30
        assert self.service.min_request_interval == 1.0
    
    def test_empty_dish_name_returns_placeholder(self):
        """Test that empty dish name returns placeholder images."""
        # Test empty string
        result = self.service.search_food_images("")
        assert len(result) > 0
        assert result[0].source == "placeholder"
        
        # Test None
        result = self.service.search_food_images(None)
        assert len(result) > 0
        assert result[0].source == "placeholder"
        
        # Test whitespace only
        result = self.service.search_food_images("   ")
        assert len(result) > 0
        assert result[0].source == "placeholder"
    
    def test_cache_hit_returns_cached_result(self):
        """Test that cached results are returned when available."""
        dish_name = "pizza"
        cached_images = [
            FoodImage(
                url="https://example.com/pizza.jpg",
                thumbnail_url="https://example.com/pizza_thumb.jpg",
                title="Delicious Pizza",
                source="example.com",
                width=400,
                height=300
            )
        ]
        
        # Set cache
        self.cache.set_image_search_result(dish_name.lower(), cached_images)
        
        # Should return cached result without making API call
        result = self.service.search_food_images(dish_name)
        assert len(result) == 1
        assert result[0].url == cached_images[0].url
        assert result[0].title == cached_images[0].title
    
    @patch('app.services.image_search_service.requests.Session.get')
    def test_successful_api_search(self, mock_get):
        """Test successful API search with quality filtering."""
        # Mock API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'items': [
                {
                    'link': 'https://example.com/pizza1.jpg',
                    'title': 'Delicious Pizza Recipe',
                    'displayLink': 'example.com',
                    'image': {
                        'thumbnailLink': 'https://example.com/pizza1_thumb.jpg',
                        'width': '500',
                        'height': '400'
                    }
                },
                {
                    'link': 'https://example.com/pizza2.jpg',
                    'title': 'Pizza Logo',  # Should be filtered out
                    'displayLink': 'example.com',
                    'image': {
                        'thumbnailLink': 'https://example.com/pizza2_thumb.jpg',
                        'width': '100',  # Too small, should be filtered out
                        'height': '100'
                    }
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Perform search
        result = self.service.search_food_images("pizza")
        
        # Should return filtered results
        assert len(result) == 1  # Only one should pass quality filter
        assert result[0].url == 'https://example.com/pizza1.jpg'
        assert result[0].title == 'Delicious Pizza Recipe'
        assert result[0].width == 500
        assert result[0].height == 400
    
    @patch('app.services.image_search_service.requests.Session.get')
    def test_api_error_returns_placeholder(self, mock_get):
        """Test that API errors return placeholder images."""
        # Mock API error
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        result = self.service.search_food_images("pizza")
        
        # Should return placeholder images
        assert len(result) > 0
        assert result[0].source == "placeholder"
    
    @patch('app.services.image_search_service.requests.Session.get')
    def test_api_error_response_returns_placeholder(self, mock_get):
        """Test that API error responses return placeholder images."""
        # Mock API error response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'error': {
                'message': 'Invalid API key'
            }
        }
        mock_get.return_value = mock_response
        
        result = self.service.search_food_images("pizza")
        
        # Should return placeholder images
        assert len(result) > 0
        assert result[0].source == "placeholder"
    
    def test_quality_filter_rejects_unwanted_content(self):
        """Test that quality filter rejects unwanted content."""
        # Test cases that should be rejected
        test_cases = [
            ("", 400, 300, "Pizza"),  # Empty URL
            ("http://example.com/logo.jpg", 400, 300, "Pizza Logo"),  # Logo in title
            ("http://example.com/pizza.jpg", 100, 100, "Pizza"),  # Too small
            ("http://example.com/pizza.gif", 400, 300, "Pizza"),  # Wrong format
            ("ftp://example.com/pizza.jpg", 400, 300, "Pizza"),  # Wrong protocol
        ]
        
        for url, width, height, title in test_cases:
            assert not self.service._passes_quality_filter(url, width, height, title)
        
        # Test case that should pass
        assert self.service._passes_quality_filter(
            "https://example.com/pizza.jpg", 400, 300, "Delicious Pizza Recipe"
        )
    
    def test_quality_score_calculation(self):
        """Test quality score calculation for image ranking."""
        # High quality image
        high_quality = FoodImage(
            url="https://foodnetwork.com/pizza.jpg",
            thumbnail_url="https://foodnetwork.com/pizza_thumb.jpg",
            title="Pizza Recipe Food Dish",
            source="foodnetwork.com",
            width=800,
            height=600
        )
        
        # Lower quality image
        low_quality = FoodImage(
            url="https://unknown.com/pizza.jpg",
            thumbnail_url="https://unknown.com/pizza_thumb.jpg",
            title="Pizza",
            source="unknown.com",
            width=200,
            height=200
        )
        
        high_score = self.service._calculate_quality_score(high_quality)
        low_score = self.service._calculate_quality_score(low_quality)
        
        assert high_score > low_score
    
    def test_rate_limiting_prevents_rapid_requests(self):
        """Test that rate limiting prevents rapid consecutive requests."""
        # Set a short interval for testing
        self.service.min_request_interval = 0.1
        
        with patch('time.sleep') as mock_sleep:
            with patch('app.services.image_search_service.requests.Session.get') as mock_get:
                # Mock successful API response
                mock_response = Mock()
                mock_response.raise_for_status.return_value = None
                mock_response.json.return_value = {'items': []}
                mock_get.return_value = mock_response
                
                # Make two rapid requests
                self.service.search_food_images("pizza")
                self.service.search_food_images("pasta")
                
                # Should have called sleep for rate limiting on second request
                mock_sleep.assert_called()
    
    def test_quota_tracking(self):
        """Test daily quota tracking."""
        initial_quota = self.service.daily_quota_used
        
        with patch('app.services.image_search_service.requests.Session.get') as mock_get:
            # Mock successful API response
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {'items': []}
            mock_get.return_value = mock_response
            
            self.service.search_food_images("pizza")
            
            # Quota should be incremented
            assert self.service.daily_quota_used == initial_quota + 1
    
    def test_quota_exceeded_returns_placeholder(self):
        """Test that exceeding quota returns placeholder images."""
        # Set quota to exceeded
        self.service.daily_quota_used = self.service.max_daily_quota
        
        result = self.service.search_food_images("pizza")
        
        # Should return placeholder images
        assert len(result) > 0
        assert result[0].source == "placeholder"
    
    def test_get_search_statistics(self):
        """Test search statistics retrieval."""
        stats = self.service.get_search_statistics()
        
        assert 'daily_quota_used' in stats
        assert 'daily_quota_remaining' in stats
        assert 'cache_size' in stats
        assert 'min_request_interval' in stats
        
        assert stats['daily_quota_remaining'] >= 0
        assert stats['cache_size'] >= 0
    
    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # Add something to cache
        self.cache.set_image_search_result("pizza", [])
        assert len(self.cache.image_search_results) > 0
        
        # Clear cache
        self.service.clear_cache()
        
        # Cache should be empty
        assert len(self.cache.image_search_results) == 0
    
    def test_reset_quota_tracking(self):
        """Test quota tracking reset."""
        # Set some quota usage
        self.service.daily_quota_used = 50
        
        # Reset quota
        self.service.reset_quota_tracking()
        
        # Should be reset to 0
        assert self.service.daily_quota_used == 0
    
    def test_add_custom_placeholder(self):
        """Test adding custom placeholder images."""
        initial_count = len(self.service.placeholder_images)
        
        self.service.add_custom_placeholder(
            url="https://example.com/custom.jpg",
            thumbnail_url="https://example.com/custom_thumb.jpg",
            title="Custom Placeholder",
            width=400,
            height=300
        )
        
        assert len(self.service.placeholder_images) == initial_count + 1
        
        # Check the added placeholder
        new_placeholder = self.service.placeholder_images[-1]
        assert new_placeholder['url'] == "https://example.com/custom.jpg"
        assert new_placeholder['title'] == "Custom Placeholder"
    
    @patch('app.services.image_search_service.requests.Session.get')
    def test_validate_api_credentials_success(self, mock_get):
        """Test successful API credential validation."""
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'items': []}
        mock_get.return_value = mock_response
        
        assert self.service.validate_api_credentials() is True
    
    @patch('app.services.image_search_service.requests.Session.get')
    def test_validate_api_credentials_failure(self, mock_get):
        """Test failed API credential validation."""
        # Mock API error
        mock_get.side_effect = requests.exceptions.RequestException("Invalid credentials")
        
        assert self.service.validate_api_credentials() is False
    
    def test_validate_api_credentials_missing_keys(self):
        """Test credential validation with missing keys."""
        # Test with missing API key
        service_no_key = ImageSearchService("", "engine_id")
        assert service_no_key.validate_api_credentials() is False
        
        # Test with missing engine ID
        service_no_engine = ImageSearchService("api_key", "")
        assert service_no_engine.validate_api_credentials() is False