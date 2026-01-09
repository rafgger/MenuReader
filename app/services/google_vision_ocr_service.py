"""
Enhanced Google Vision OCR Service for Menu Image Analyzer.

This module provides OCR functionality using Google Cloud Vision API
with support for both service account authentication and API key authentication.
"""

import os
import hashlib
import time
import logging
from typing import Optional, List
import base64

from app.models.data_models import OCRResult, RequestCache

logger = logging.getLogger(__name__)


class GoogleVisionOCRService:
    """
    Enhanced OCR service using Google Cloud Vision API.
    
    Supports both service account authentication (recommended) and API key authentication.
    """
    
    def __init__(self, cache: Optional[RequestCache] = None, timeout: int = 30):
        """
        Initialize Google Vision OCR service.
        
        Args:
            cache: Optional cache instance for storing results
            timeout: Request timeout in seconds
        """
        self.cache = cache or RequestCache()
        self.timeout = timeout
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
        # Try to initialize Google Cloud Vision client
        self.vision_client = None
        self.use_service_account = False
        
        try:
            # Check if service account credentials are available
            credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path and os.path.exists(credentials_path):
                from google.cloud import vision
                self.vision_client = vision.ImageAnnotatorClient()
                self.use_service_account = True
                logger.info("Initialized Google Vision with service account authentication")
            else:
                logger.info("Service account not found, will use REST API with API key")
        except ImportError:
            logger.warning("google-cloud-vision not installed, falling back to REST API")
        except Exception as e:
            logger.warning(f"Failed to initialize Google Vision client: {e}")
    
    def extract_text(self, image_data: bytes, language_hints: Optional[List[str]] = None) -> OCRResult:
        """
        Extract text from image using Google Vision API.
        
        Args:
            image_data: Raw image bytes
            language_hints: Optional list of language codes to help OCR
            
        Returns:
            OCRResult with extracted text and metadata
        """
        # Generate cache key from image data
        image_hash = hashlib.md5(image_data).hexdigest()
        
        # Check cache first
        if self.cache:
            cached_result = self.cache.get_ocr_result(image_hash)
            if cached_result:
                logger.info(f"OCR result found in cache for image hash: {image_hash[:8]}...")
                return cached_result
        
        # Rate limiting
        self._enforce_rate_limit()
        
        try:
            if self.use_service_account and self.vision_client:
                result = self._extract_with_client_library(image_data, language_hints)
            else:
                result = self._extract_with_rest_api(image_data, language_hints)
            
            # Cache the result
            if self.cache:
                self.cache.set_ocr_result(image_hash, result)
            
            logger.info(f"OCR extraction successful. Text length: {len(result.text)}, "
                       f"Confidence: {result.confidence:.2f}, Language: {result.language}")
            
            return result
            
        except Exception as e:
            error_msg = f"Google Vision OCR processing failed: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def _extract_with_client_library(self, image_data: bytes, language_hints: Optional[List[str]] = None) -> OCRResult:
        """Extract text using Google Cloud Vision client library."""
        from google.cloud import vision
        
        # Create image object
        image = vision.Image(content=image_data)
        
        # Configure image context with language hints
        image_context = None
        if language_hints:
            image_context = vision.ImageContext(language_hints=language_hints)
        
        # Perform text detection
        response = self.vision_client.text_detection(
            image=image,
            image_context=image_context,
            timeout=self.timeout
        )
        
        # Check for errors
        if response.error.message:
            raise Exception(f"Google Vision API error: {response.error.message}")
        
        # Extract text annotations
        texts = response.text_annotations
        if not texts:
            return OCRResult(text="", confidence=0.0, language="unknown")
        
        # First annotation contains full text
        full_text = texts[0].description
        
        # Extract bounding boxes from individual text annotations
        bounding_boxes = []
        for text in texts[1:]:  # Skip first (full text)
            vertices = []
            for vertex in text.bounding_poly.vertices:
                vertices.append({"x": vertex.x, "y": vertex.y})
            
            bounding_boxes.append({
                "text": text.description,
                "vertices": vertices
            })
        
        # Detect language from full text annotation
        language = "unknown"
        if hasattr(response, 'full_text_annotation') and response.full_text_annotation:
            pages = response.full_text_annotation.pages
            if pages:
                properties = pages[0].property
                if properties and properties.detected_languages:
                    language = properties.detected_languages[0].language_code
        
        # Use a default confidence if we can't calculate it
        confidence = 0.8 if full_text.strip() else 0.0
        
        return OCRResult(
            text=full_text,
            confidence=confidence,
            language=language,
            bounding_boxes=bounding_boxes
        )
    
    def _extract_with_rest_api(self, image_data: bytes, language_hints: Optional[List[str]] = None) -> OCRResult:
        """Extract text using Google Vision REST API."""
        import requests
        
        # Get API key from environment
        api_key = os.environ.get('OCR_API_KEY')
        if not api_key:
            raise Exception("OCR_API_KEY environment variable not set")
        
        # Prepare request payload
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        features = [{"type": "TEXT_DETECTION"}]
        
        payload = {
            "requests": [{
                "image": {"content": image_b64},
                "features": features,
                "imageContext": {
                    "languageHints": language_hints or []
                }
            }]
        }
        
        # Make API request
        url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=self.timeout
        )
        response.raise_for_status()
        
        # Parse response
        result_data = response.json()
        
        if "error" in result_data:
            raise Exception(f"Google Vision API error: {result_data['error']}")
        
        responses = result_data.get("responses", [])
        if not responses:
            return OCRResult(text="", confidence=0.0, language="unknown")
        
        response_data = responses[0]
        
        # Extract text annotations
        text_annotations = response_data.get("textAnnotations", [])
        if not text_annotations:
            return OCRResult(text="", confidence=0.0, language="unknown")
        
        # First annotation contains full text
        full_text = text_annotations[0].get("description", "")
        
        # Extract bounding boxes
        bounding_boxes = []
        for annotation in text_annotations[1:]:  # Skip first (full text)
            if "boundingPoly" in annotation:
                vertices = annotation["boundingPoly"].get("vertices", [])
                if vertices:
                    bounding_boxes.append({
                        "text": annotation.get("description", ""),
                        "vertices": vertices
                    })
        
        # Detect language from full document detection if available
        language = "unknown"
        full_text_annotation = response_data.get("fullTextAnnotation")
        if full_text_annotation:
            pages = full_text_annotation.get("pages", [])
            if pages:
                properties = pages[0].get("property", {})
                detected_languages = properties.get("detectedLanguages", [])
                if detected_languages:
                    language = detected_languages[0].get("languageCode", "unknown")
        
        # Use a default confidence if we can't calculate it
        confidence = 0.8 if full_text.strip() else 0.0
        
        return OCRResult(
            text=full_text,
            confidence=confidence,
            language=language,
            bounding_boxes=bounding_boxes
        )
    
    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between API requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def validate_configuration(self) -> bool:
        """
        Validate that the OCR service is properly configured.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        if self.use_service_account and self.vision_client:
            return True
        
        # Check for API key
        api_key = os.environ.get('OCR_API_KEY')
        return bool(api_key)
    
    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported languages for Google Vision API.
        
        Returns:
            List of language codes supported by Google Vision
        """
        return [
            "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh", 
            "ar", "hi", "th", "vi", "tr", "pl", "nl", "sv", "da", "no",
            "fi", "cs", "hu", "ro", "bg", "hr", "sk", "sl", "et", "lv", "lt"
        ]
    
    def clear_cache(self) -> None:
        """Clear the OCR results cache."""
        if self.cache:
            self.cache.clear()
            logger.info("OCR cache cleared")