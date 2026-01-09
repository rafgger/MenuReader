#!/usr/bin/env python3
"""
Simple test script to test Google Vision OCR directly with the 1.jpg image.
"""

import os
import sys
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.google_vision_ocr_service import GoogleVisionOCRService
from app.models.data_models import RequestCache


def main():
    """Test Google Vision OCR directly."""
    print("Testing Google Vision OCR with 1.jpg")
    
    # Set up service account credentials
    service_account_path = 'google-vision-service-account.json'
    if os.path.exists(service_account_path):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = service_account_path
        print(f"Using service account: {service_account_path}")
    else:
        print("Error: Service account file not found")
        return
    
    # Load test image
    image_path = "examples/images/1.jpg"
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        print(f"Loaded image: {len(image_data)} bytes")
    except FileNotFoundError:
        print(f"Error: Image file not found at {image_path}")
        return
    
    # Initialize OCR service
    print("\nInitializing Google Vision OCR service...")
    cache = RequestCache()
    ocr_service = GoogleVisionOCRService(cache=cache)
    
    # Check configuration
    if not ocr_service.validate_configuration():
        print("Error: OCR service configuration is invalid")
        return
    
    print(f"Service account mode: {ocr_service.use_service_account}")
    print(f"Vision client available: {ocr_service.vision_client is not None}")
    
    # Extract text
    print("\nExtracting text from image...")
    try:
        result = ocr_service.extract_text(image_data)
        
        print("\n" + "="*60)
        print("OCR RESULTS")
        print("="*60)
        print(f"Text length: {len(result.text)}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Language: {result.language}")
        print(f"Bounding boxes: {len(result.bounding_boxes)}")
        
        print("\nExtracted Text:")
        print("-" * 40)
        print(result.text)
        print("-" * 40)
        
        # Save to file
        with open("ocr_result.txt", "w", encoding="utf-8") as f:
            f.write(result.text)
        print("\nText saved to: ocr_result.txt")
        
    except Exception as e:
        print(f"OCR extraction failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()