"""
Results Service for Menu Image Analyzer

This module handles the display and formatting of menu analysis results.
"""

from typing import List, Dict, Any, Optional
from app.models.data_models import EnrichedDish, ProcessingError, FoodImage, DishDescription
import logging

logger = logging.getLogger(__name__)


class ResultsService:
    """Service for handling results display and formatting."""
    
    def __init__(self):
        """Initialize the results service."""
        self.placeholder_image_url = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2Y4ZjlmYSIvPgogIDx0ZXh0IHg9IjE1MCIgeT0iMTAwIiBmb250LWZhbWlseT0iQXJpYWwsIHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM2Yzc1N2QiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5ObyBpbWFnZSBhdmFpbGFibGU8L3RleHQ+Cjwvc3ZnPgo="
    
    def format_results_for_display(self, dishes: List[EnrichedDish], 
                                  processing_errors: List[ProcessingError] = None) -> Dict[str, Any]:
        """
        Format enriched dishes for display in templates.
        
        Args:
            dishes: List of enriched dishes to format
            processing_errors: Optional list of processing errors
            
        Returns:
            Dictionary containing formatted results data
        """
        try:
            formatted_dishes = []
            
            for enriched_dish in dishes:
                formatted_dish = self._format_single_dish(enriched_dish)
                formatted_dishes.append(formatted_dish)
            
            return {
                'dishes': formatted_dishes,
                'total_count': len(formatted_dishes),
                'errors': processing_errors or [],
                'has_errors': bool(processing_errors),
                'success': len(formatted_dishes) > 0
            }
            
        except Exception as e:
            logger.error(f"Error formatting results for display: {e}")
            return {
                'dishes': [],
                'total_count': 0,
                'errors': [ProcessingError(
                    type='display',
                    message='Error formatting results for display',
                    recoverable=False
                )],
                'has_errors': True,
                'success': False
            }
    
    def _format_single_dish(self, enriched_dish: EnrichedDish) -> Dict[str, Any]:
        """
        Format a single enriched dish for display.
        
        Args:
            enriched_dish: The enriched dish to format
            
        Returns:
            Dictionary containing formatted dish data
        """
        dish = enriched_dish.dish
        images = enriched_dish.images or {}
        description = enriched_dish.description
        
        # Format images
        formatted_images = self._format_images(images)
        
        # Format description
        formatted_description = self._format_description(description) if description else None
        
        # Format price with preservation of original formatting
        formatted_price = self._format_price(dish.price)
        
        return {
            'dish': {
                'id': dish.id,
                'name': dish.name,
                'original_name': dish.original_name,
                'price': formatted_price,
                'confidence': dish.confidence
            },
            'images': formatted_images,
            'description': formatted_description,
            'processing_status': enriched_dish.processing_status
        }
    
    def _format_images(self, images: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format image data for display with fallback handling.
        
        Args:
            images: Dictionary containing image data
            
        Returns:
            Formatted images dictionary
        """
        formatted = {
            'primary': None,
            'secondary': [],
            'has_images': False
        }
        
        # Handle primary image
        if images.get('primary'):
            primary = images['primary']
            if isinstance(primary, dict):
                formatted['primary'] = {
                    'url': primary.get('url', self.placeholder_image_url),
                    'thumbnail_url': primary.get('thumbnail_url', primary.get('url', self.placeholder_image_url)),
                    'title': primary.get('title', ''),
                    'load_status': primary.get('load_status', 'loading')
                }
                formatted['has_images'] = True
            elif isinstance(primary, FoodImage):
                formatted['primary'] = {
                    'url': primary.url,
                    'thumbnail_url': primary.thumbnail_url or primary.url,
                    'title': primary.title,
                    'load_status': primary.load_status
                }
                formatted['has_images'] = True
        
        # Handle secondary images
        if images.get('secondary'):
            secondary_images = images['secondary']
            if isinstance(secondary_images, list):
                for img in secondary_images:
                    if isinstance(img, dict):
                        formatted['secondary'].append({
                            'url': img.get('url', ''),
                            'thumbnail_url': img.get('thumbnail_url', img.get('url', '')),
                            'title': img.get('title', ''),
                            'load_status': img.get('load_status', 'loading')
                        })
                    elif isinstance(img, FoodImage):
                        formatted['secondary'].append({
                            'url': img.url,
                            'thumbnail_url': img.thumbnail_url or img.url,
                            'title': img.title,
                            'load_status': img.load_status
                        })
        
        return formatted
    
    def _format_description(self, description: DishDescription) -> Dict[str, Any]:
        """
        Format description data for display.
        
        Args:
            description: The dish description to format
            
        Returns:
            Formatted description dictionary
        """
        return {
            'text': description.text,
            'ingredients': description.ingredients,
            'dietary_restrictions': description.dietary_restrictions,
            'cuisine_type': description.cuisine_type,
            'spice_level': description.spice_level,
            'preparation_method': description.preparation_method,
            'confidence': description.confidence,
            'has_details': bool(
                description.ingredients or 
                description.dietary_restrictions or 
                description.cuisine_type or 
                description.spice_level or 
                description.preparation_method
            )
        }
    
    def _format_price(self, price: str) -> Dict[str, Any]:
        """
        Format price with preservation of original formatting.
        
        Args:
            price: Original price string from menu
            
        Returns:
            Formatted price dictionary
        """
        if not price or price.strip() == '':
            return {
                'display': 'Price not available',
                'original': '',
                'has_price': False,
                'formatted': 'N/A'
            }
        
        # Preserve original formatting
        return {
            'display': price.strip(),
            'original': price,
            'has_price': True,
            'formatted': price.strip()
        }
    
    def create_error_summary(self, errors: List[ProcessingError]) -> Dict[str, Any]:
        """
        Create a summary of processing errors for display.
        
        Args:
            errors: List of processing errors
            
        Returns:
            Error summary dictionary
        """
        if not errors:
            return {
                'has_errors': False, 
                'summary': '', 
                'details': [],
                'total_count': 0,
                'recoverable_count': 0
            }
        
        error_counts = {}
        recoverable_count = 0
        
        for error in errors:
            error_type = error.type.value if hasattr(error.type, 'value') else str(error.type)
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
            if error.recoverable:
                recoverable_count += 1
        
        summary_parts = []
        for error_type, count in error_counts.items():
            if count == 1:
                summary_parts.append(f"1 {error_type} error")
            else:
                summary_parts.append(f"{count} {error_type} errors")
        
        summary = ", ".join(summary_parts)
        if recoverable_count > 0:
            summary += f" ({recoverable_count} recoverable)"
        
        return {
            'has_errors': True,
            'summary': summary,
            'details': [{'message': error.message, 'recoverable': error.recoverable} for error in errors],
            'total_count': len(errors),
            'recoverable_count': recoverable_count
        }
    
    def validate_results_data(self, results_data: Dict[str, Any]) -> bool:
        """
        Validate that results data is properly formatted for display.
        
        Args:
            results_data: Results data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        try:
            # Check required fields
            required_fields = ['dishes', 'total_count', 'errors', 'has_errors', 'success']
            for field in required_fields:
                if field not in results_data:
                    logger.warning(f"Missing required field in results data: {field}")
                    return False
            
            # Validate dishes structure
            dishes = results_data['dishes']
            if not isinstance(dishes, list):
                logger.warning("Dishes field must be a list")
                return False
            
            for dish in dishes:
                if not isinstance(dish, dict):
                    logger.warning("Each dish must be a dictionary")
                    return False
                
                # Check required dish fields
                dish_required = ['dish', 'images']
                for field in dish_required:
                    if field not in dish:
                        logger.warning(f"Missing required dish field: {field}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating results data: {e}")
            return False