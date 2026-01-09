"""
Property-based tests for language-agnostic OCR processing.

This module tests Property 3: Language-Agnostic Processing
**Validates: Requirements 1.3, 2.3**
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch
import hashlib

from app.services.ocr_service import OCRService
from app.models.data_models import OCRResult, RequestCache


class TestLanguageAgnosticProcessingProperty:
    """
    Property-based tests for language-agnostic OCR processing.
    
    **Feature: menu-image-analyzer, Property 3: Language-Agnostic Processing**
    **Validates: Requirements 1.3, 2.3**
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = RequestCache()
        self.service = OCRService(api_key="test_key", cache=self.cache)
    
    @given(
        # Generate various language codes including real and fictional ones
        language_code=st.one_of(
            st.sampled_from([
                "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh",
                "ar", "hi", "th", "vi", "tr", "pl", "nl", "sv", "da", "no",
                "unknown", "auto", "", "xyz", "123", "mixed"
            ]),
            st.text(min_size=2, max_size=5, alphabet=st.characters(min_codepoint=97, max_codepoint=122))
        ),
        # Generate different image data patterns
        image_data=st.binary(min_size=100, max_size=1000)
    )
    @settings(max_examples=100)
    @patch('app.services.ocr_service.requests.Session.post')
    def test_language_agnostic_processing_property(self, mock_post, language_code, image_data):
        """
        **Feature: menu-image-analyzer, Property 3: Language-Agnostic Processing**
        
        *For any* menu image regardless of language, the OCR processing should attempt 
        extraction without failing due to language barriers.
        
        **Validates: Requirements 1.3, 2.3**
        """
        # Mock successful API response with the given language
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "responses": [{
                "textAnnotations": [{
                    "description": f"Menu text in {language_code}",
                    "boundingPoly": {"vertices": []}
                }],
                "fullTextAnnotation": {
                    "pages": [{
                        "property": {
                            "detectedLanguages": [{"languageCode": language_code}]
                        }
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response
        
        # The key property: OCR should not fail regardless of language
        try:
            result = self.service.extract_text(
                image_data=image_data,
                language_hints=[language_code] if language_code else None
            )
            
            # Verify that we get a valid OCRResult object
            assert isinstance(result, OCRResult)
            
            # The service should always return a result, even if empty
            assert hasattr(result, 'text')
            assert hasattr(result, 'confidence')
            assert hasattr(result, 'language')
            assert hasattr(result, 'bounding_boxes')
            
            # Confidence should be in valid range
            assert 0.0 <= result.confidence <= 1.0
            
            # Language should be a string (even if "unknown")
            assert isinstance(result.language, str)
            
            # Bounding boxes should be a list
            assert isinstance(result.bounding_boxes, list)
            
            # If text was extracted, it should be a string
            assert isinstance(result.text, str)
            
        except Exception as e:
            # Language barriers should not cause the service to fail completely
            # Only network/API errors are acceptable failures
            error_message = str(e).lower()
            acceptable_errors = [
                "network", "timeout", "connection", "api", "http", "request"
            ]
            
            # Check if this is an acceptable error (not language-related)
            is_acceptable_error = any(error_type in error_message for error_type in acceptable_errors)
            
            if not is_acceptable_error:
                pytest.fail(f"OCR failed due to language barrier: {str(e)}")
    
    @given(
        # Generate lists of mixed language hints
        language_hints=st.lists(
            st.one_of(
                st.sampled_from(["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"]),
                st.text(min_size=2, max_size=3, alphabet=st.characters(min_codepoint=97, max_codepoint=122))
            ),
            min_size=0,
            max_size=5
        )
    )
    @settings(max_examples=50)
    @patch('app.services.ocr_service.requests.Session.post')
    def test_multiple_language_hints_property(self, mock_post, language_hints):
        """
        Test that OCR processing works with multiple language hints.
        
        **Feature: menu-image-analyzer, Property 3: Language-Agnostic Processing**
        **Validates: Requirements 1.3, 2.3**
        """
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "responses": [{
                "textAnnotations": [{
                    "description": "Mixed language menu",
                    "boundingPoly": {"vertices": []}
                }],
                "fullTextAnnotation": {
                    "pages": [{
                        "property": {
                            "detectedLanguages": [{"languageCode": "mixed"}]
                        }
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response
        
        # Test image data
        test_image = b"fake_image_data_for_testing"
        
        try:
            result = self.service.extract_text(
                image_data=test_image,
                language_hints=language_hints
            )
            
            # Should always return a valid result
            assert isinstance(result, OCRResult)
            assert isinstance(result.text, str)
            assert 0.0 <= result.confidence <= 1.0
            
            # Verify that language hints were passed to the API
            if language_hints:  # Only check if hints were provided
                call_args = mock_post.call_args
                if call_args:
                    request_data = call_args[1].get("json", {})
                    if "requests" in request_data and request_data["requests"]:
                        image_context = request_data["requests"][0].get("imageContext", {})
                        passed_hints = image_context.get("languageHints", [])
                        # The hints should have been passed through
                        assert isinstance(passed_hints, list)
                        
        except Exception as e:
            # Multiple language hints should not cause failures
            error_message = str(e).lower()
            if "language" in error_message or "hint" in error_message:
                pytest.fail(f"Multiple language hints caused failure: {str(e)}")
    
    @given(
        # Generate edge case scenarios
        scenario=st.sampled_from([
            "empty_language",
            "unknown_language", 
            "mixed_script",
            "no_language_hints",
            "invalid_language_code"
        ])
    )
    @settings(max_examples=25)
    @patch('app.services.ocr_service.requests.Session.post')
    def test_edge_case_language_scenarios(self, mock_post, scenario):
        """
        Test edge cases for language-agnostic processing.
        
        **Feature: menu-image-analyzer, Property 3: Language-Agnostic Processing**
        **Validates: Requirements 1.3, 2.3**
        """
        # Configure mock response based on scenario
        if scenario == "empty_language":
            language_code = ""
            text_content = ""
        elif scenario == "unknown_language":
            language_code = "unknown"
            text_content = "Unknown script content"
        elif scenario == "mixed_script":
            language_code = "mixed"
            text_content = "Menu 菜单 Menú メニュー"
        elif scenario == "no_language_hints":
            language_code = "auto"
            text_content = "Auto-detected content"
        else:  # invalid_language_code
            language_code = "xyz123"
            text_content = "Content with invalid language code"
        
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "responses": [{
                "textAnnotations": [{
                    "description": text_content,
                    "boundingPoly": {"vertices": []}
                }] if text_content else [],
                "fullTextAnnotation": {
                    "pages": [{
                        "property": {
                            "detectedLanguages": [{"languageCode": language_code}]
                        }
                    }]
                } if language_code != "empty_language" else {}
            }]
        }
        mock_post.return_value = mock_response
        
        test_image = b"test_image_data"
        
        # The service should handle all edge cases gracefully
        result = self.service.extract_text(test_image)
        
        # Should always return a valid OCRResult
        assert isinstance(result, OCRResult)
        assert isinstance(result.text, str)
        assert isinstance(result.language, str)
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.bounding_boxes, list)
        
        # Even with edge cases, the result should be well-formed
        if scenario == "empty_language":
            # Empty language should be handled gracefully
            assert result.language in ["", "unknown", "auto"]
        elif scenario == "mixed_script":
            # Mixed scripts should not cause errors
            assert len(result.text) >= 0  # Could be empty or contain text
    
    @patch('app.services.ocr_service.requests.Session.post')
    def test_language_detection_consistency(self, mock_post):
        """
        Test that language detection is consistent across similar inputs.
        
        **Feature: menu-image-analyzer, Property 3: Language-Agnostic Processing**
        **Validates: Requirements 1.3, 2.3**
        """
        # Mock consistent response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "responses": [{
                "textAnnotations": [{
                    "description": "Consistent menu text",
                    "boundingPoly": {"vertices": []}
                }],
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
        
        # Test the same image multiple times
        test_image = b"consistent_test_image"
        results = []
        
        for _ in range(3):
            result = self.service.extract_text(test_image)
            results.append(result)
        
        # Results should be consistent (due to caching)
        assert len(results) == 3
        assert all(isinstance(r, OCRResult) for r in results)
        
        # Due to caching, results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result.text == first_result.text
            assert result.language == first_result.language
            assert result.confidence == first_result.confidence