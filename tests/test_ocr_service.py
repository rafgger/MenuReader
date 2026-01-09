"""
Tests for OCR Service functionality.

This module tests the OCRService class including text extraction,
caching, error handling, and API integration.
"""

import pytest
import hashlib
from unittest.mock import Mock, patch, MagicMock
import requests

from app.services.ocr_service import OCRService
from app.models.data_models import OCRResult, RequestCache


class TestOCRService:
    """Test cases for OCRService class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.api_key = "test_api_key"
        self.cache = RequestCache()
        self.service = OCRService(api_key=self.api_key, cache=self.cache)
        
        # Sample image data (small PNG)
        self.test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
    
    def test_service_initialization(self):
        """Test OCRService initialization with different parameters."""
        # Test default initialization
        service = OCRService(api_key="test_key")
        assert service.api_key == "test_key"
        assert service.provider == "google_vision"
        assert service.timeout == 30
        assert isinstance(service.cache, RequestCache)
        
        # Test custom initialization
        custom_cache = RequestCache()
        service = OCRService(
            api_key="custom_key",
            cache=custom_cache,
            provider="azure",
            timeout=60
        )
        assert service.api_key == "custom_key"
        assert service.cache is custom_cache
        assert service.provider == "azure"
        assert service.timeout == 60
    
    def test_cache_functionality(self):
        """Test OCR result caching."""
        image_hash = hashlib.md5(self.test_image).hexdigest()
        
        # Create mock result
        mock_result = OCRResult(
            text="Test menu text",
            confidence=0.85,
            language="en",
            bounding_boxes=[]
        )
        
        # Test cache miss
        assert self.cache.get_ocr_result(image_hash) is None
        
        # Cache the result
        self.cache.set_ocr_result(image_hash, mock_result)
        
        # Test cache hit
        cached_result = self.cache.get_ocr_result(image_hash)
        assert cached_result is not None
        assert cached_result.text == "Test menu text"
        assert cached_result.confidence == 0.85
        assert cached_result.language == "en"
    
    @patch('app.services.ocr_service.requests.Session.post')
    def test_google_vision_extraction(self, mock_post):
        """Test text extraction using Google Vision API."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "responses": [{
                "textAnnotations": [
                    {
                        "description": "MENU\nPasta Carbonara $15\nMargherita Pizza $12",
                        "boundingPoly": {
                            "vertices": [{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 50}, {"x": 0, "y": 50}]
                        }
                    },
                    {
                        "description": "MENU",
                        "boundingPoly": {
                            "vertices": [{"x": 0, "y": 0}, {"x": 50, "y": 0}, {"x": 50, "y": 20}, {"x": 0, "y": 20}]
                        }
                    }
                ],
                "fullTextAnnotation": {
                    "pages": [{
                        "property": {
                            "detectedLanguages": [{"languageCode": "en"}]
                        }
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response
        
        # Test extraction
        service = OCRService(api_key="test_key", provider="google_vision")
        result = service.extract_text(self.test_image)
        
        assert isinstance(result, OCRResult)
        assert "MENU" in result.text
        assert "Pasta Carbonara" in result.text
        assert result.confidence > 0
        assert result.language == "en"
        assert len(result.bounding_boxes) > 0
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        # URL is the first positional argument
        assert "vision.googleapis.com" in call_args[0][0]
    
    @patch('app.services.ocr_service.requests.Session.post')
    def test_azure_extraction(self, mock_post):
        """Test text extraction using Azure Computer Vision API."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "language": "en",
            "regions": [{
                "lines": [{
                    "words": [
                        {"text": "MENU", "boundingBox": "0,0,50,20"},
                        {"text": "ITEMS", "boundingBox": "60,0,100,20"}
                    ],
                    "boundingBox": "0,0,100,20"
                }, {
                    "words": [
                        {"text": "Pasta", "boundingBox": "0,25,40,45"},
                        {"text": "$15", "boundingBox": "80,25,100,45"}
                    ],
                    "boundingBox": "0,25,100,45"
                }]
            }]
        }
        mock_post.return_value = mock_response
        
        # Test extraction
        service = OCRService(api_key="test_key", provider="azure")
        result = service.extract_text(self.test_image)
        
        assert isinstance(result, OCRResult)
        assert "MENU ITEMS" in result.text
        assert "Pasta $15" in result.text
        assert result.confidence > 0
        assert result.language == "en"
        assert len(result.bounding_boxes) > 0
    
    @patch('app.services.ocr_service.requests.Session.post')
    def test_api_error_handling(self, mock_post):
        """Test handling of API errors."""
        # Mock API error response
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("API Error")
        mock_post.return_value = mock_response
        
        service = OCRService(api_key="test_key")
        
        with pytest.raises(Exception) as exc_info:
            service.extract_text(self.test_image)
        
        assert "OCR API request failed" in str(exc_info.value)
    
    @patch('app.services.ocr_service.requests.Session.post')
    def test_empty_response_handling(self, mock_post):
        """Test handling of empty OCR responses."""
        # Mock empty API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "responses": [{}]  # Empty response
        }
        mock_post.return_value = mock_response
        
        service = OCRService(api_key="test_key", provider="google_vision")
        result = service.extract_text(self.test_image)
        
        assert isinstance(result, OCRResult)
        assert result.text == ""
        assert result.confidence == 0.0
        assert result.language == "unknown"
    
    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        service = OCRService(api_key="test_key")
        service.min_request_interval = 0.1  # 100ms
        
        import time
        start_time = time.time()
        
        # Simulate multiple rapid requests
        service._enforce_rate_limit()
        service._enforce_rate_limit()
        
        elapsed_time = time.time() - start_time
        assert elapsed_time >= 0.1  # Should have been rate limited
    
    def test_language_support(self):
        """Test language support functionality."""
        # Test Google Vision language support
        service = OCRService(api_key="test_key", provider="google_vision")
        languages = service.get_supported_languages()
        assert "en" in languages
        assert "es" in languages
        assert "fr" in languages
        assert len(languages) > 10
        
        # Test Azure language support
        service = OCRService(api_key="test_key", provider="azure")
        languages = service.get_supported_languages()
        assert "en" in languages
        assert len(languages) > 10
        
        # Test AWS Textract language support (limited)
        service = OCRService(api_key="test_key", provider="aws_textract")
        languages = service.get_supported_languages()
        assert "en" in languages
        assert len(languages) <= 10  # More limited support
    
    def test_cache_integration(self):
        """Test OCR service integration with caching."""
        service = OCRService(api_key="test_key", cache=self.cache)
        
        # Mock a successful extraction
        mock_result = OCRResult(
            text="Cached menu text",
            confidence=0.9,
            language="en",
            bounding_boxes=[]
        )
        
        image_hash = hashlib.md5(self.test_image).hexdigest()
        self.cache.set_ocr_result(image_hash, mock_result)
        
        # This should return cached result without making API call
        with patch('app.services.ocr_service.requests.Session.post') as mock_post:
            result = service.extract_text(self.test_image)
            
            # Verify no API call was made
            mock_post.assert_not_called()
            
            # Verify cached result was returned
            assert result.text == "Cached menu text"
            assert result.confidence == 0.9
    
    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # Add some data to cache
        mock_result = OCRResult(text="test", confidence=0.8)
        image_hash = "test_hash"
        self.cache.set_ocr_result(image_hash, mock_result)
        
        # Verify data is in cache
        assert self.cache.get_ocr_result(image_hash) is not None
        
        # Clear cache through service
        service = OCRService(api_key="test_key", cache=self.cache)
        service.clear_cache()
        
        # Verify cache is cleared
        assert self.cache.get_ocr_result(image_hash) is None
    
    def test_unsupported_provider(self):
        """Test handling of unsupported OCR provider."""
        service = OCRService(api_key="test_key", provider="unsupported_provider")
        
        with pytest.raises(Exception) as exc_info:
            service.extract_text(self.test_image)
        
        assert "Unsupported OCR provider" in str(exc_info.value)
    
    @patch('app.services.ocr_service.requests.Session.post')
    def test_language_hints(self, mock_post):
        """Test OCR with language hints."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "responses": [{
                "textAnnotations": [{
                    "description": "Menu en español",
                    "boundingPoly": {"vertices": []}
                }],
                "fullTextAnnotation": {
                    "pages": [{
                        "property": {
                            "detectedLanguages": [{"languageCode": "es"}]
                        }
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response
        
        service = OCRService(api_key="test_key", provider="google_vision")
        result = service.extract_text(self.test_image, language_hints=["es", "en"])
        
        assert result.language == "es"
        
        # Verify language hints were passed in request
        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        image_context = request_data["requests"][0]["imageContext"]
        assert image_context["languageHints"] == ["es", "en"]


class TestOCRServiceIntegration:
    """Integration tests for OCR service with real-world scenarios."""
    
    def test_multilingual_menu_processing(self):
        """Test processing of multilingual menu content."""
        # This would be an integration test with actual API calls
        # For now, we'll mock the behavior
        service = OCRService(api_key="test_key")
        
        # Mock multilingual result
        with patch.object(service, '_extract_with_google_vision') as mock_extract:
            mock_extract.return_value = OCRResult(
                text="MENU\nPasta Carbonara €15\nPizza Margherita €12\nMenu del día €8",
                confidence=0.85,
                language="es",
                bounding_boxes=[]
            )
            
            result = service.extract_text(b"fake_image_data", language_hints=["es", "en"])
            
            assert "Pasta Carbonara" in result.text
            assert "€" in result.text  # European currency
            assert result.language == "es"
    
    def test_low_quality_image_handling(self):
        """Test handling of low-quality images with poor OCR results."""
        service = OCRService(api_key="test_key")
        
        # Mock low-confidence result
        with patch.object(service, '_extract_with_google_vision') as mock_extract:
            mock_extract.return_value = OCRResult(
                text="M3NU\nP4st4 C4rb0n4r4 $1S\nP1zz4 M4rgh3r1t4 $12",
                confidence=0.3,  # Low confidence
                language="en",
                bounding_boxes=[]
            )
            
            result = service.extract_text(b"low_quality_image")
            
            assert result.confidence < 0.5
            assert len(result.text) > 0  # Should still return something
    
    def test_no_text_detected(self):
        """Test handling when no text is detected in image."""
        service = OCRService(api_key="test_key")
        
        # Mock no-text result
        with patch.object(service, '_extract_with_google_vision') as mock_extract:
            mock_extract.return_value = OCRResult(
                text="",
                confidence=0.0,
                language="unknown",
                bounding_boxes=[]
            )
            
            result = service.extract_text(b"image_with_no_text")
            
            assert result.text == ""
            assert result.confidence == 0.0
            assert result.language == "unknown"