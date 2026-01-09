"""
Example usage of the Google Vision OCR Service for Menu Image Analyzer.

This example demonstrates how to use the GoogleVisionOCRService class
with both service account authentication and API key authentication.
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.google_vision_ocr_service import GoogleVisionOCRService
from app.models.data_models import RequestCache


def main():
    """Demonstrate Google Vision OCR service usage."""
    
    # Initialize cache
    cache = RequestCache()
    
    print("🔍 Initializing Google Vision OCR Service...")
    
    # Initialize the service (it will auto-detect authentication method)
    ocr_service = GoogleVisionOCRService(cache=cache, timeout=30)
    
    # Display service configuration
    print(f"   Using service account: {ocr_service.use_service_account}")
    print(f"   Configuration valid: {ocr_service.validate_configuration()}")
    print(f"   Supported languages: {len(ocr_service.get_supported_languages())} languages")
    print(f"   Cache enabled: {ocr_service.cache is not None}")
    
    if not ocr_service.validate_configuration():
        print("❌ OCR service is not properly configured!")
        print("   Please ensure either:")
        print("   1. GOOGLE_APPLICATION_CREDENTIALS points to your service account JSON file")
        print("   2. OCR_API_KEY is set with your Google Cloud API key")
        return
    
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
        if "authentication" in str(e).lower() or "credentials" in str(e).lower():
            print("   This appears to be an authentication issue.")
            print("   Please check your Google Cloud credentials.")
    
    # Test with a more realistic menu image scenario
    print("\n🍽️  Testing with menu-like text...")
    
    # Create a simple text image simulation (in real usage, this would be actual image bytes)
    menu_text_simulation = "Sample Menu Text"
    
    try:
        # In a real scenario, you would load actual image bytes here
        # For demonstration, we'll use the same sample image
        result = ocr_service.extract_text(sample_image, language_hints=["en"])
        
        print(f"   Menu processing result: {len(result.text)} characters extracted")
        print(f"   Language detected: {result.language}")
        
    except Exception as e:
        print(f"   Menu processing failed: {str(e)}")
    
    print("\n🎉 Google Vision OCR Service example completed!")
    print("\nNext steps:")
    print("1. Test with real menu images")
    print("2. Integrate with the Flask application")
    print("3. Configure for production deployment")
    
    # Show current environment configuration
    print("\n🔧 Current Configuration:")
    print(f"   GOOGLE_APPLICATION_CREDENTIALS: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'Not set')}")
    print(f"   OCR_API_KEY: {'Set' if os.environ.get('OCR_API_KEY') else 'Not set'}")


if __name__ == "__main__":
    main()