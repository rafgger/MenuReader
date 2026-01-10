"""
Test final image search fix.

Simple test to verify images now work with minimal filtering.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_minimal_filtering():
    """Test image search with minimal filtering (happy path)."""
    print("Testing image search with minimal filtering")
    
    try:
        from app.services.image_search_service import ImageSearchService
        from app.models.data_models import RequestCache
        
        api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
        engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        
        # Initialize with fresh cache
        cache = RequestCache()
        service = ImageSearchService(api_key, engine_id, cache)
        
        # Test with simple dish name
        print("🔍 Searching for 'burger'...")
        images = service.search_food_images("burger", max_results=2)
        
        if images:
            real_images = [img for img in images if 'placeholder' not in img.url]
            placeholder_images = [img for img in images if 'placeholder' in img.url]
            
            print(f"Total images: {len(images)}")
            print(f"Real images: {len(real_images)}")
            print(f"Placeholders: {len(placeholder_images)}")
            
            if real_images:
                print("✅ PASS: Real images found!")
                for i, img in enumerate(real_images[:2], 1):
                    print(f"  {i}. {img.url[:60]}...")
                return True
            else:
                print("❌ FAIL: Still only placeholders")
                return False
        else:
            print("❌ FAIL: No images returned")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Test failed - {e}")
        return False


def test_quality_filter_direct():
    """Test quality filter directly (edge case)."""
    print("Testing quality filter directly")
    
    try:
        from app.services.image_search_service import ImageSearchService
        from app.models.data_models import RequestCache
        
        api_key = os.getenv('GOOGLE_SEARCH_API_KEY', 'test')
        engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID', 'test')
        
        cache = RequestCache()
        service = ImageSearchService(api_key, engine_id, cache)
        
        # Test various URLs
        test_cases = [
            ("https://example.com/food.jpg", "Food image", True),
            ("https://example.com/burger.png", "Delicious burger", True),
            ("https://example.com/company-logo.jpg", "Company logo", False),
            ("invalid-url", "Food", False),
        ]
        
        passed = 0
        for url, title, should_pass in test_cases:
            result = service._passes_quality_filter(url, 300, 300, title)
            if result == should_pass:
                passed += 1
                status = "PASS" if should_pass else "FILTERED"
                print(f"✅ {url}: {status} (correct)")
            else:
                expected = "PASS" if should_pass else "FILTERED"
                actual = "PASS" if result else "FILTERED"
                print(f"❌ {url}: Expected {expected}, got {actual}")
        
        if passed == len(test_cases):
            print("✅ PASS: Quality filter working correctly")
            return True
        else:
            print(f"❌ FAIL: {passed}/{len(test_cases)} filter tests passed")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Filter test failed - {e}")
        return False


def run_final_test():
    """Run final fix test."""
    print("🔧 Final Image Search Fix Test")
    print("=" * 35)
    
    results = []
    results.append(test_minimal_filtering())
    results.append(test_quality_filter_direct())
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nTest Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests PASSED!")
        print("Images should now display in browser!")
    else:
        print("⚠️  Some tests FAILED!")
    
    return passed == total


if __name__ == "__main__":
    run_final_test()