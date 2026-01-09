"""
Example usage of ImageSearchService.

This script demonstrates how to use the ImageSearchService to search for food images
with proper error handling and caching.
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.image_search_service import ImageSearchService
from app.models.data_models import RequestCache


def main():
    """Demonstrate ImageSearchService usage."""
    
    # Get API credentials from environment variables
    api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
    search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
    
    if not api_key or not search_engine_id:
        print("Error: Missing required environment variables:")
        print("- GOOGLE_SEARCH_API_KEY")
        print("- GOOGLE_SEARCH_ENGINE_ID")
        print("\nPlease set these in your .env file.")
        return
    
    # Create cache and service
    cache = RequestCache()
    service = ImageSearchService(
        api_key=api_key,
        search_engine_id=search_engine_id,
        cache=cache
    )
    
    print("Image Search Service Example")
    print("=" * 40)
    
    # Validate API credentials
    print("Validating API credentials...")
    if service.validate_api_credentials():
        print("✓ API credentials are valid")
    else:
        print("✗ API credentials are invalid")
        return
    
    # Example dishes to search for
    dishes = [
        "margherita pizza",
        "chicken tikka masala",
        "beef ramen",
        "chocolate cake",
        "caesar salad"
    ]
    
    print(f"\nSearching for images of {len(dishes)} dishes...")
    print("-" * 40)
    
    for dish in dishes:
        print(f"\nSearching for: {dish}")
        
        try:
            # Search for images
            images = service.search_food_images(dish, max_results=3)
            
            print(f"Found {len(images)} images:")
            
            for i, image in enumerate(images, 1):
                print(f"  {i}. {image.title}")
                print(f"     URL: {image.url}")
                print(f"     Source: {image.source}")
                print(f"     Size: {image.width}x{image.height}")
                print(f"     Status: {image.load_status}")
                
                if image.source == "placeholder":
                    print("     (This is a placeholder image)")
                
                print()
        
        except Exception as e:
            print(f"Error searching for {dish}: {str(e)}")
    
    # Show search statistics
    print("\nSearch Statistics:")
    print("-" * 20)
    stats = service.get_search_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Demonstrate caching
    print("\nDemonstrating cache functionality...")
    print("Searching for 'margherita pizza' again (should use cache):")
    
    cached_images = service.search_food_images("margherita pizza", max_results=1)
    if cached_images:
        print(f"✓ Retrieved from cache: {cached_images[0].title}")
    
    # Show cache statistics
    print(f"Cache contains {len(cache.image_search_results)} entries")
    
    print("\nExample completed successfully!")


if __name__ == "__main__":
    main()