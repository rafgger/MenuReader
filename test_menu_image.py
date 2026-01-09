#!/usr/bin/env python3
"""
Test script to process the 1.jpg menu image using the Menu Image Analyzer.

This script demonstrates how to use the MenuProcessor to analyze a menu image
and display the results.
"""

import os
import sys
import json
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.menu_processor import MenuProcessor
from app.models.data_models import RequestCache


def load_test_image(image_path: str) -> bytes:
    """Load the test image file."""
    try:
        with open(image_path, 'rb') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Image file not found at {image_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading image: {e}")
        sys.exit(1)


def print_results(result):
    """Print the menu analysis results in a readable format."""
    print("\n" + "="*60)
    print("MENU ANALYSIS RESULTS")
    print("="*60)
    
    print(f"Success: {result.success}")
    print(f"Processing Time: {result.processing_time:.2f} seconds")
    print(f"Dishes Found: {len(result.dishes)}")
    
    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for i, error in enumerate(result.errors, 1):
            print(f"  {i}. [{error.type.value}] {error.message}")
            if error.dish_id:
                print(f"     Dish: {error.dish_id}")
    
    if result.dishes:
        print(f"\nDISHES FOUND:")
        print("-" * 40)
        
        for i, enriched_dish in enumerate(result.dishes, 1):
            dish = enriched_dish.dish
            print(f"\n{i}. {dish.name}")
            print(f"   Price: {dish.price if dish.price else 'Not specified'}")
            print(f"   Confidence: {dish.confidence:.2f}")
            
            # Show images info
            if enriched_dish.images:
                if 'placeholder' in enriched_dish.images:
                    print("   Images: Placeholder (no images found)")
                else:
                    primary_count = 1 if 'primary' in enriched_dish.images else 0
                    secondary_count = len(enriched_dish.images.get('secondary', []))
                    total_images = primary_count + secondary_count
                    print(f"   Images: {total_images} found")
            
            # Show description info
            if enriched_dish.description:
                desc = enriched_dish.description
                print(f"   Description: {desc.text[:100]}...")
                if desc.ingredients:
                    print(f"   Ingredients: {', '.join(desc.ingredients[:3])}...")
                if desc.dietary_restrictions:
                    print(f"   Dietary: {', '.join(desc.dietary_restrictions)}")
                if desc.cuisine_type:
                    print(f"   Cuisine: {desc.cuisine_type}")
                if desc.spice_level:
                    print(f"   Spice Level: {desc.spice_level}")
            else:
                print("   Description: Not available")
    
    print("\n" + "="*60)


def main():
    """Main test function."""
    print("Menu Image Analyzer - Test Script")
    print("Processing: examples/images/1.jpg")
    
    # Set up environment variables for Google Vision
    service_account_path = 'google-vision-service-account.json'
    if os.path.exists(service_account_path):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = service_account_path
        print(f"Using service account: {service_account_path}")
    else:
        print("Warning: Service account file not found")
    
    # Load test image
    image_path = "examples/images/1.jpg"
    print(f"Loading image: {image_path}")
    image_data = load_test_image(image_path)
    print(f"Image loaded: {len(image_data)} bytes")
    
    # Initialize menu processor
    print("\nInitializing Menu Processor...")
    
    # Create a shared cache
    cache = RequestCache()
    
    # Initialize with minimal configuration (no API keys needed for Google Vision with service account)
    processor = MenuProcessor(
        ocr_api_key=None,  # Will use GoogleVisionOCRService with service account
        image_search_api_key=os.getenv('GOOGLE_SEARCH_API_KEY'),
        image_search_engine_id=os.getenv('GOOGLE_SEARCH_ENGINE_ID'),
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        cache=cache
    )
    
    # Check service status
    status = processor.get_service_status()
    print("\nService Status:")
    for service, info in status.items():
        if isinstance(info, dict) and 'available' in info:
            available = info['available']
            print(f"  {service}: {'✓' if available else '✗'}")
        else:
            print(f"  {service}: {info}")
    
    # Process the menu
    print(f"\nProcessing menu image...")
    
    def progress_callback(state):
        """Print progress updates."""
        print(f"Progress: {state.current_step.value} - {state.progress}%")
    
    try:
        result = processor.process_menu(
            image_data=image_data,
            processing_id="test-1jpg",
            progress_callback=progress_callback
        )
        
        # Display results
        print_results(result)
        
        # Save results to JSON file for inspection
        results_file = "test_results.json"
        print(f"\nSaving detailed results to: {results_file}")
        
        # Convert result to JSON-serializable format
        json_result = {
            'success': result.success,
            'processing_time': result.processing_time,
            'dishes': [],
            'errors': []
        }
        
        for enriched_dish in result.dishes:
            dish_data = {
                'name': enriched_dish.dish.name,
                'price': enriched_dish.dish.price,
                'confidence': enriched_dish.dish.confidence,
                'images': enriched_dish.images,
                'description': None,
                'processing_status': enriched_dish.processing_status
            }
            
            if enriched_dish.description:
                dish_data['description'] = {
                    'text': enriched_dish.description.text,
                    'ingredients': enriched_dish.description.ingredients,
                    'dietary_restrictions': enriched_dish.description.dietary_restrictions,
                    'cuisine_type': enriched_dish.description.cuisine_type,
                    'spice_level': enriched_dish.description.spice_level,
                    'preparation_method': enriched_dish.description.preparation_method,
                    'confidence': enriched_dish.description.confidence
                }
            
            json_result['dishes'].append(dish_data)
        
        for error in result.errors:
            json_result['errors'].append({
                'type': error.type.value,
                'message': error.message,
                'recoverable': error.recoverable,
                'dish_id': error.dish_id
            })
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(json_result, f, indent=2, ensure_ascii=False)
        
        print(f"Results saved successfully!")
        
    except Exception as e:
        print(f"\nError during processing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()