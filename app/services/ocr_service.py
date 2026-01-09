"""
OCR Service for Menu Image Analyzer.

This module provides OCR (Optical Character Recognition) functionality using external APIs
to extract text from menu images with confidence scoring, language detection, and error handling.
"""

import hashlib
import time
import logging
from typing import Optional, Dict, Any, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.models.data_models import OCRResult, ProcessingError, ErrorType, RequestCache


logger = logging.getLogger(__name__)


class OCRService:
    """
    Service for extracting text from images using external OCR APIs.
    
    Supports multiple OCR providers with fallback mechanisms, caching,
    rate limiting, and comprehensive error handling.
    """
    
    def __init__(self, api_key: str, cache: Optional[RequestCache] = None, 
                 provider: str = "google_vision", timeout: int = 30):
        """
        Initialize OCR service.
        
        Args:
            api_key: API key for the OCR service
            cache: Optional cache instance for storing results
            provider: OCR provider ('google_vision', 'azure', 'aws_textract')
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.cache = cache or RequestCache()
        self.provider = provider
        self.timeout = timeout
        
        # Configure HTTP session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
        # Provider configurations
        self.provider_configs = {
            "google_vision": {
                "url": "https://vision.googleapis.com/v1/images:annotate",
                "headers": {"Content-Type": "application/json"},
                "supports_language_detection": True
            },
            "azure": {
                "url": "https://api.cognitive.microsoft.com/vision/v3.2/ocr",
                "headers": {"Ocp-Apim-Subscription-Key": api_key, "Content-Type": "application/octet-stream"},
                "supports_language_detection": True
            },
            "aws_textract": {
                "url": "https://textract.us-east-1.amazonaws.com/",
                "headers": {"Content-Type": "application/x-amz-json-1.1"},
                "supports_language_detection": False
            }
        }
    
    def extract_text(self, image_data: bytes, language_hints: Optional[List[str]] = None) -> OCRResult:
        """
        Extract text from image using OCR API.
        
        Args:
            image_data: Raw image bytes
            language_hints: Optional list of language codes to help OCR
            
        Returns:
            OCRResult with extracted text and metadata
            
        Raises:
            Exception: If OCR processing fails after all retries
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
            # Perform OCR based on provider
            if self.provider == "google_vision":
                result = self._extract_with_google_vision(image_data, language_hints)
            elif self.provider == "azure":
                result = self._extract_with_azure(image_data, language_hints)
            elif self.provider == "aws_textract":
                result = self._extract_with_aws_textract(image_data)
            else:
                raise ValueError(f"Unsupported OCR provider: {self.provider}")
            
            # Cache the result
            if self.cache:
                self.cache.set_ocr_result(image_hash, result)
            
            logger.info(f"OCR extraction successful. Text length: {len(result.text)}, "
                       f"Confidence: {result.confidence:.2f}, Language: {result.language}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            error_msg = f"OCR API request failed: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"OCR processing failed: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def _extract_with_google_vision(self, image_data: bytes, language_hints: Optional[List[str]] = None) -> OCRResult:
        """Extract text using Google Vision API."""
        import base64
        
        # Prepare request payload
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        features = [{"type": "TEXT_DETECTION"}]
        if language_hints:
            features.append({"type": "DOCUMENT_TEXT_DETECTION"})
        
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
        config = self.provider_configs["google_vision"]
        url = f"{config['url']}?key={self.api_key}"
        
        response = self.session.post(
            url,
            json=payload,
            headers=config["headers"],
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
        
        # Calculate average confidence from all annotations
        confidences = []
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
    
    def _extract_with_azure(self, image_data: bytes, language_hints: Optional[List[str]] = None) -> OCRResult:
        """Extract text using Azure Computer Vision API."""
        config = self.provider_configs["azure"]
        
        # Determine language parameter
        language = "unk"  # Auto-detect
        if language_hints and language_hints[0] in ["en", "es", "fr", "de", "it", "pt", "zh", "ja", "ko"]:
            language = language_hints[0]
        
        params = {"language": language, "detectOrientation": "true"}
        
        response = self.session.post(
            config["url"],
            data=image_data,
            headers=config["headers"],
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()
        
        result_data = response.json()
        
        # Parse Azure OCR response
        regions = result_data.get("regions", [])
        full_text = ""
        bounding_boxes = []
        
        for region in regions:
            lines = region.get("lines", [])
            for line in lines:
                words = line.get("words", [])
                line_text = " ".join([word.get("text", "") for word in words])
                full_text += line_text + "\n"
                
                # Add bounding box info
                if words:
                    bounding_boxes.append({
                        "text": line_text,
                        "boundingBox": line.get("boundingBox", "")
                    })
        
        # Azure doesn't provide confidence scores, use heuristic
        confidence = 0.8 if full_text.strip() else 0.0
        detected_language = result_data.get("language", "unknown")
        
        return OCRResult(
            text=full_text.strip(),
            confidence=confidence,
            language=detected_language,
            bounding_boxes=bounding_boxes
        )
    
    def _extract_with_aws_textract(self, image_data: bytes) -> OCRResult:
        """Extract text using AWS Textract."""
        # Note: This is a simplified implementation
        # In production, you'd use boto3 and proper AWS authentication
        
        import json
        
        config = self.provider_configs["aws_textract"]
        
        payload = {
            "Document": {
                "Bytes": image_data
            }
        }
        
        headers = config["headers"].copy()
        headers["X-Amz-Target"] = "Textract.DetectDocumentText"
        
        response = self.session.post(
            config["url"],
            data=json.dumps(payload),
            headers=headers,
            timeout=self.timeout
        )
        response.raise_for_status()
        
        result_data = response.json()
        
        # Parse Textract response
        blocks = result_data.get("Blocks", [])
        full_text = ""
        confidences = []
        bounding_boxes = []
        
        for block in blocks:
            if block.get("BlockType") == "LINE":
                text = block.get("Text", "")
                confidence = block.get("Confidence", 0) / 100.0  # Convert to 0-1 range
                
                full_text += text + "\n"
                confidences.append(confidence)
                
                geometry = block.get("Geometry", {})
                if geometry:
                    bounding_boxes.append({
                        "text": text,
                        "geometry": geometry
                    })
        
        # Calculate average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return OCRResult(
            text=full_text.strip(),
            confidence=avg_confidence,
            language="unknown",  # Textract doesn't detect language
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
    
    def validate_api_key(self) -> bool:
        """
        Validate that the API key is working.
        
        Returns:
            True if API key is valid, False otherwise
        """
        if not self.api_key:
            return False
        
        try:
            # Create a small test image (1x1 pixel PNG)
            test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
            
            # Try to extract text (should return empty but not error)
            result = self.extract_text(test_image)
            return True
            
        except Exception as e:
            logger.error(f"API key validation failed: {str(e)}")
            return False
    
    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported languages for the current provider.
        
        Returns:
            List of language codes supported by the OCR provider
        """
        language_support = {
            "google_vision": [
                "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh", 
                "ar", "hi", "th", "vi", "tr", "pl", "nl", "sv", "da", "no"
            ],
            "azure": [
                "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh",
                "ar", "hi", "th", "tr", "pl", "nl", "sv", "da", "no", "fi"
            ],
            "aws_textract": [
                "en", "es", "fr", "de", "it", "pt"  # Limited language support
            ]
        }
        
        return language_support.get(self.provider, ["en"])
    
    def clear_cache(self) -> None:
        """Clear the OCR results cache."""
        if self.cache:
            self.cache.clear()
            logger.info("OCR cache cleared")