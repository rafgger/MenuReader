"""
Image Search Service for Menu Image Analyzer.

This module provides food image search functionality using Google Custom Search API
with quality filtering, metadata extraction, caching, and comprehensive error handling.
"""

import hashlib
import time
import logging
from typing import List, Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import quote_plus

from app.models.data_models import FoodImage, ProcessingError, ErrorType, RequestCache


logger = logging.getLogger(__name__)


class ImageSearchService:
    """
    Service for searching food images using Google Custom Search API.
    
    Provides high-quality food image retrieval with filtering, caching,
    rate limiting, and comprehensive error handling with fallback mechanisms.
    """
    
    def __init__(self, api_key: str, search_engine_id: str, 
                 cache: Optional[RequestCache] = None, timeout: int = 30):
        """
        Initialize image search service.
        
        Args:
            api_key: Google Custom Search API key
            search_engine_id: Google Custom Search Engine ID
            cache: Optional cache instance for storing results
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.cache = cache or RequestCache()
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
        
        # Rate limiting - Google Custom Search allows 100 queries per day for free
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests to be safe
        self.daily_quota_used = 0
        self.max_daily_quota = 100
        
        # Base URL for Google Custom Search API
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
        # Quality filtering parameters
        self.min_image_size = 200  # Minimum width/height in pixels
        self.preferred_formats = ['jpg', 'jpeg', 'png', 'webp']
        self.max_results_per_search = 10
        
        # Placeholder image URLs for fallback
        self.placeholder_images = [
            {
                "url": "https://via.placeholder.com/400x300/f0f0f0/666666?text=Food+Image",
                "thumbnail_url": "https://via.placeholder.com/150x150/f0f0f0/666666?text=Food",
                "title": "Food placeholder image",
                "source": "placeholder",
                "width": 400,
                "height": 300
            }
        ]
    
    def search_food_images(self, dish_name: str, max_results: int = 5) -> List[FoodImage]:
        """
        Search for food images related to the given dish name.
        
        Args:
            dish_name: Name of the dish to search for
            max_results: Maximum number of images to return
            
        Returns:
            List of FoodImage objects with metadata
        """
        if not dish_name or not dish_name.strip():
            logger.warning("Empty dish name provided for image search")
            return self._get_placeholder_images()
        
        # Normalize dish name for caching
        normalized_name = dish_name.strip().lower()
        
        # Check cache first
        cached_result = self.cache.get_image_search_result(normalized_name)
        if cached_result:
            logger.info(f"Image search result found in cache for: {dish_name}")
            return cached_result[:max_results]
        
        # Check rate limiting and quota
        if not self._can_make_request():
            logger.warning("Rate limit or quota exceeded, returning placeholder images")
            return self._get_placeholder_images()
        
        try:
            # Perform the search
            images = self._perform_search(dish_name, max_results)
            
            # Filter and validate images
            filtered_images = self._filter_and_validate_images(images)
            
            # If no good images found, add placeholder
            if not filtered_images:
                logger.info(f"No quality images found for '{dish_name}', using placeholder")
                filtered_images = self._get_placeholder_images()
            
            # Cache the result
            self.cache.set_image_search_result(normalized_name, filtered_images)
            
            logger.info(f"Image search successful for '{dish_name}': {len(filtered_images)} images")
            return filtered_images[:max_results]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Image search API request failed for '{dish_name}': {str(e)}")
            return self._get_placeholder_images()
        except Exception as e:
            logger.error(f"Image search failed for '{dish_name}': {str(e)}")
            return self._get_placeholder_images()
    
    def _perform_search(self, dish_name: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Perform the actual Google Custom Search API request.
        
        Args:
            dish_name: Dish name to search for
            max_results: Maximum results to retrieve
            
        Returns:
            Raw search results from API
        """
        # Enforce rate limiting
        self._enforce_rate_limit()
        
        # Prepare search query with food-specific terms
        search_query = f"{dish_name} food dish recipe"
        
        # API parameters
        params = {
            'key': self.api_key,
            'cx': self.search_engine_id,
            'q': search_query,
            'searchType': 'image',
            'num': min(max_results, self.max_results_per_search),
            'imgSize': 'medium',  # Prefer medium-sized images
            'imgType': 'photo',   # Prefer photos over clipart
            'safe': 'active',     # Safe search
            'fileType': 'jpg,png,webp',  # Preferred formats
            'rights': 'cc_publicdomain,cc_attribute,cc_sharealike'  # Prefer open licenses
        }
        
        # Make the API request
        response = self.session.get(
            self.base_url,
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()
        
        # Update quota tracking
        self.daily_quota_used += 1
        
        # Parse response
        data = response.json()
        
        if 'error' in data:
            error_msg = data['error'].get('message', 'Unknown API error')
            raise Exception(f"Google Custom Search API error: {error_msg}")
        
        # Extract image items
        items = data.get('items', [])
        logger.debug(f"Retrieved {len(items)} raw image results for '{dish_name}'")
        
        return items
    
    def _filter_and_validate_images(self, raw_results: List[Dict[str, Any]]) -> List[FoodImage]:
        """
        Filter and validate image search results for quality.
        
        Args:
            raw_results: Raw results from Google Custom Search API
            
        Returns:
            List of validated FoodImage objects
        """
        validated_images = []
        
        for item in raw_results:
            try:
                # Extract image metadata
                image_url = item.get('link', '')
                thumbnail_url = item.get('image', {}).get('thumbnailLink', '')
                title = item.get('title', '')
                source = item.get('displayLink', '')
                
                # Get image dimensions
                image_meta = item.get('image', {})
                width = int(image_meta.get('width', 0))
                height = int(image_meta.get('height', 0))
                
                # Quality filtering
                if not self._passes_quality_filter(image_url, width, height, title):
                    continue
                
                # Create FoodImage object
                food_image = FoodImage(
                    url=image_url,
                    thumbnail_url=thumbnail_url or image_url,
                    title=title,
                    source=source,
                    width=width,
                    height=height,
                    load_status='loading'
                )
                
                validated_images.append(food_image)
                
            except (ValueError, KeyError) as e:
                logger.debug(f"Skipping invalid image result: {str(e)}")
                continue
        
        # Sort by quality score (larger images first, then by source reliability)
        validated_images.sort(key=self._calculate_quality_score, reverse=True)
        
        logger.debug(f"Filtered to {len(validated_images)} quality images")
        return validated_images
    
    def _passes_quality_filter(self, url: str, width: int, height: int, title: str) -> bool:
        """
        Check if an image passes quality filtering criteria.
        
        Args:
            url: Image URL
            width: Image width in pixels
            height: Image height in pixels
            title: Image title/description
            
        Returns:
            True if image passes quality filters
        """
        # Check URL validity
        if not url or not url.startswith(('http://', 'https://')):
            return False
        
        # Very lenient filtering - accept almost all images
        # Only filter out obvious logos
        title_lower = title.lower() if title else ""
        url_lower = url.lower()
        
        # Only reject obvious non-food content
        if 'logo' in title_lower:
            return False
        
        return True
    
    def _calculate_quality_score(self, image: FoodImage) -> float:
        """
        Calculate a quality score for ranking images.
        
        Args:
            image: FoodImage to score
            
        Returns:
            Quality score (higher is better)
        """
        score = 0.0
        
        # Size score (prefer larger images, up to a point)
        if image.width > 0 and image.height > 0:
            size_score = min(image.width * image.height, 1000000) / 1000000
            score += size_score * 0.4
        
        # Source reliability score
        reliable_sources = [
            'wikipedia.org', 'wikimedia.org', 'foodnetwork.com',
            'allrecipes.com', 'epicurious.com', 'bonappetit.com',
            'seriouseats.com', 'tasteofhome.com'
        ]
        
        if any(source in image.source.lower() for source in reliable_sources):
            score += 0.3
        
        # Title relevance score
        food_terms = ['recipe', 'dish', 'food', 'cuisine', 'cooking', 'meal']
        title_lower = image.title.lower()
        relevance_score = sum(0.05 for term in food_terms if term in title_lower)
        score += min(relevance_score, 0.3)
        
        return score
    
    def _get_placeholder_images(self) -> List[FoodImage]:
        """
        Get placeholder images for when search fails or returns no results.
        
        Returns:
            List of placeholder FoodImage objects
        """
        placeholder_images = []
        
        for placeholder in self.placeholder_images:
            food_image = FoodImage(
                url=placeholder['url'],
                thumbnail_url=placeholder['thumbnail_url'],
                title=placeholder['title'],
                source=placeholder['source'],
                width=placeholder['width'],
                height=placeholder['height'],
                load_status='loaded'
            )
            placeholder_images.append(food_image)
        
        return placeholder_images
    
    def _can_make_request(self) -> bool:
        """
        Check if we can make another API request based on rate limits and quotas.
        
        Returns:
            True if request can be made
        """
        # Check daily quota
        if self.daily_quota_used >= self.max_daily_quota:
            logger.warning(f"Daily quota exceeded: {self.daily_quota_used}/{self.max_daily_quota}")
            return False
        
        return True
    
    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between API requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def validate_api_credentials(self) -> bool:
        """
        Validate that the API credentials are working.
        
        Returns:
            True if credentials are valid, False otherwise
        """
        if not self.api_key or not self.search_engine_id:
            logger.error("Missing API key or search engine ID")
            return False
        
        try:
            # Test with a simple search
            test_results = self._perform_search("pizza", 1)
            return len(test_results) >= 0  # Even 0 results means API is working
            
        except Exception as e:
            logger.error(f"API credential validation failed: {str(e)}")
            return False
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about search usage.
        
        Returns:
            Dictionary with usage statistics
        """
        return {
            'daily_quota_used': self.daily_quota_used,
            'daily_quota_remaining': self.max_daily_quota - self.daily_quota_used,
            'cache_size': len(self.cache.image_search_results),
            'min_request_interval': self.min_request_interval
        }
    
    def clear_cache(self) -> None:
        """Clear the image search cache."""
        if self.cache:
            # Only clear image search results, not other cache types
            self.cache.image_search_results.clear()
            logger.info("Image search cache cleared")
    
    def reset_quota_tracking(self) -> None:
        """Reset daily quota tracking (call this daily)."""
        self.daily_quota_used = 0
        logger.info("Daily quota tracking reset")
    
    def add_custom_placeholder(self, url: str, thumbnail_url: str, title: str, 
                             width: int = 400, height: int = 300) -> None:
        """
        Add a custom placeholder image.
        
        Args:
            url: Full-size image URL
            thumbnail_url: Thumbnail image URL
            title: Image title
            width: Image width
            height: Image height
        """
        placeholder = {
            "url": url,
            "thumbnail_url": thumbnail_url,
            "title": title,
            "source": "custom_placeholder",
            "width": width,
            "height": height
        }
        
        self.placeholder_images.append(placeholder)
        logger.info(f"Added custom placeholder image: {title}")