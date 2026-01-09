"""
Example usage of the OCR Service for Menu Image Analyzer.

This example demonstrates how to use the OCRService class to extract text
from menu images with different providers and configurations.
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ocr_service import OCRService
from app.models.data_models import RequestCache


def main():
    """Demonstrate OCR service usage."""
    
    # Initialize cache
    cache = RequestCache()
    
    # Get API key from environment (you would set this in production)
    api_key = os.environ.get('OCR_API_KEY', 'your-api-key-here')
    
    if api_key == 'your-api-key-here':
        print("⚠️  Please set OCR_API_KEY environment variable with your actual API key")
        print("   This example will show the service structure without making real API calls")
    
    # Initialize OCR service with Google Vision (default)
    print("🔍 Initializing OCR Service with Google Vision API...")
    ocr_service = OCRService(
        api_key=api_key,
        cache=cache,
        provider="google_vision",
        timeout=30
    )
    
    # Display service configuration
    print(f"   Provider: {ocr_service.provider}")
    print(f"   Timeout: {ocr_service.timeout}s")
    print(f"   Supported languages: {len(ocr_service.get_supported_languages())} languages")
    print(f"   Cache enabled: {ocr_service.cache is not None}")
    
    # Create a sample image (1x1 pixel PNG for testing)
    sample_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
    
    print("\n📸 Processing sample image...")
    
    try:
        # Extract text from image
        result = ocr_service.extract_text(
            image_data=sample_image,
            language_hints=["en", "es"]  # English and Spanish hints
        )
        
        print("✅ OCR extraction completed!")
        print(f"   Extracted text: '{result.text}' (length: {len(result.text)})")
        print(f"   Confidence: {result.confidence:.2f}")
        print(f"   Detected language: {result.language}")
        print(f"   Bounding boxes: {len(result.bounding_boxes)}")
        
        # Demonstrate caching
        print("\n💾 Testing cache functionality...")
        
        # This should use cached result
        cached_result = ocr_service.extract_text(sample_image)
        print(f"   Cache hit: {cached_result.text == result.text}")
        
        # Clear cache
        ocr_service.clear_cache()
        print("   Cache cleared")
        
    except Exception as e:
        print(f"❌ OCR extraction failed: {str(e)}")
        print("   This is expected if no valid API key is provided")
    
    # Demonstrate different providers
    print("\n🔄 Testing different OCR providers...")
    
    providers = ["google_vision", "azure", "aws_textract"]
    for provider in providers:
        try:
            service = OCRService(api_key=api_key, provider=provider)
            languages = service.get_supported_languages()
            print(f"   {provider}: {len(languages)} supported languages")
        except Exception as e:
            print(f"   {provider}: Configuration error - {str(e)}")
    
    # Demonstrate error handling
    print("\n⚠️  Testing error handling...")
    
    try:
        # Test with invalid API key
        invalid_service = OCRService(api_key="invalid-key")
        result = invalid_service.extract_text(sample_image)
    except Exception as e:
        print(f"   Invalid API key handled: {type(e).__name__}")
    
    try:
        # Test with unsupported provider
        unsupported_service = OCRService(api_key=api_key, provider="unsupported")
        result = unsupported_service.extract_text(sample_image)
    except Exception as e:
        print(f"   Unsupported provider handled: {type(e).__name__}")
    
    print("\n🎉 OCR Service example completed!")
    print("\nNext steps:")
    print("1. Set up your OCR API key (Google Vision, Azure, or AWS)")
    print("2. Test with real menu images")
    print("3. Integrate with the Flask application")
    print("4. Configure caching and rate limiting for production")


if __name__ == "__main__":
    main()