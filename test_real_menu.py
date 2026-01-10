"""
Test AI Menu Analyzer with real menu image.

Tests the AI menu analyzer using examples/images/1.jpg to verify it works with actual menu photos.
"""

import os
import json
from dotenv import load_dotenv
from app.services.ai_menu_analyzer import AIMenuAnalyzer
from app.models.data_models import RequestCache

# Load environment variables
load_dotenv()


def test_real_menu_image():
    """Test AI menu analyzer with real menu image from examples/images/1.jpg."""
    print("Testing AI Menu Analyzer with Real Menu Image")
    print("=" * 50)
    
    # Check if API key is configured
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ FAIL: OPENROUTER_API_KEY not configured")
        print("Please set your OpenRouter API key in .env file")
        return False
    
    # Check if image exists
    image_path = "examples/images/1.jpg"
    if not os.path.exists(image_path):
        print(f"❌ FAIL: Image not found at {image_path}")
        return False
    
    try:
        # Read the image
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        print(f"📸 Image loaded: {len(image_data)} bytes")
        
        # Initialize AI analyzer
        cache = RequestCache()
        analyzer = AIMenuAnalyzer(cache=cache)
        
        print("🤖 Analyzing menu with AI model...")
        print("⏳ This may take a few seconds...")
        
        # Analyze the menu
        dishes = analyzer.analyze_menu(image_data)
        
        # Display results
        print(f"\n🍽️  Analysis Results:")
        print(f"Found {len(dishes)} dishes on the menu\n")
        
        if dishes:
            for i, dish in enumerate(dishes, 1):
                print(f"{i}. {dish.name}")
                if dish.price:
                    print(f"   Price: {dish.price}")
                else:
                    print("   Price: Not visible")
                print(f"   Confidence: {dish.confidence:.1%}")
                print()
        else:
            print("No dishes found in the menu image.")
        
        # Show JSON format
        print("📋 JSON Format:")
        result_json = {
            "dishes": [
                {
                    "dish_name": dish.name,
                    "price": dish.price
                }
                for dish in dishes
            ]
        }
        print(json.dumps(result_json, indent=2, ensure_ascii=False))
        
        print(f"\n✅ PASS: Successfully analyzed real menu image")
        print(f"Found {len(dishes)} dishes with AI model")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Analysis failed - {e}")
        return False


def test_api_validation():
    """Test API key validation (edge case)."""
    print("\nTesting API Key Validation")
    print("-" * 30)
    
    try:
        cache = RequestCache()
        analyzer = AIMenuAnalyzer(cache=cache)
        
        # Test API key validation
        is_valid = analyzer.validate_api_key()
        
        if is_valid:
            print("✅ PASS: API key validation successful")
            return True
        else:
            print("❌ FAIL: API key validation failed")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: API validation error - {e}")
        return False


def run_real_menu_test():
    """Run real menu image test."""
    print("🍽️  AI Menu Analyzer - Real Image Test")
    print("=" * 60)
    
    results = []
    
    # Test with real image
    results.append(test_real_menu_image())
    
    # Test API validation
    results.append(test_api_validation())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 60)
    print(f"Test Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests PASSED!")
        print("The AI menu analyzer is working correctly with real images!")
    else:
        print("⚠️  Some tests FAILED!")
        if not os.getenv("OPENROUTER_API_KEY"):
            print("💡 Tip: Make sure to set OPENROUTER_API_KEY in your .env file")
    
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    run_real_menu_test()