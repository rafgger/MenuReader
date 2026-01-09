"""
Tests for the Results Service module.

This module tests the results display and formatting functionality.
"""

import pytest
from app.services.results_service import ResultsService
from app.models.data_models import (
    Dish, EnrichedDish, FoodImage, DishDescription, ProcessingError, ErrorType
)


class TestResultsService:
    """Test cases for the ResultsService class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.results_service = ResultsService()
    
    def test_initialization(self):
        """Test that ResultsService initializes correctly."""
        assert self.results_service is not None
        assert hasattr(self.results_service, 'placeholder_image_url')
        assert self.results_service.placeholder_image_url.startswith('data:image/svg+xml')
    
    def test_format_empty_results(self):
        """Test formatting empty results."""
        result = self.results_service.format_results_for_display([])
        
        assert result['dishes'] == []
        assert result['total_count'] == 0
        assert result['errors'] == []
        assert result['has_errors'] is False
        assert result['success'] is False
    
    def test_format_single_dish_basic(self):
        """Test formatting a single dish with basic information."""
        dish = Dish(
            name="Pasta Carbonara",
            original_name="Pasta Carbonara",
            price="$15.99",
            confidence=0.9
        )
        
        enriched_dish = EnrichedDish(
            dish=dish,
            images={},
            description=None,
            processing_status="complete"
        )
        
        result = self.results_service.format_results_for_display([enriched_dish])
        
        assert result['total_count'] == 1
        assert result['success'] is True
        assert len(result['dishes']) == 1
        
        formatted_dish = result['dishes'][0]
        assert formatted_dish['dish']['name'] == "Pasta Carbonara"
        assert formatted_dish['dish']['price']['display'] == "$15.99"
        assert formatted_dish['dish']['price']['has_price'] is True
    
    def test_format_dish_with_images(self):
        """Test formatting a dish with primary and secondary images."""
        dish = Dish(
            name="Sushi Roll",
            original_name="Sushi Roll",
            price="¥1200",
            confidence=0.85
        )
        
        primary_image = FoodImage(
            url="https://example.com/sushi.jpg",
            thumbnail_url="https://example.com/sushi_thumb.jpg",
            title="Delicious Sushi Roll",
            source="example.com",
            width=800,
            height=600
        )
        
        secondary_images = [
            FoodImage(
                url="https://example.com/sushi2.jpg",
                thumbnail_url="https://example.com/sushi2_thumb.jpg",
                title="Another Sushi View",
                source="example.com",
                width=400,
                height=300
            )
        ]
        
        enriched_dish = EnrichedDish(
            dish=dish,
            images={
                'primary': primary_image,
                'secondary': secondary_images
            },
            processing_status="complete"
        )
        
        result = self.results_service.format_results_for_display([enriched_dish])
        formatted_dish = result['dishes'][0]
        
        assert formatted_dish['images']['has_images'] is True
        assert formatted_dish['images']['primary']['url'] == "https://example.com/sushi.jpg"
        assert formatted_dish['images']['primary']['thumbnail_url'] == "https://example.com/sushi_thumb.jpg"
        assert len(formatted_dish['images']['secondary']) == 1
        assert formatted_dish['images']['secondary'][0]['url'] == "https://example.com/sushi2.jpg"
    
    def test_format_dish_with_description(self):
        """Test formatting a dish with AI-generated description."""
        dish = Dish(
            name="Pad Thai",
            original_name="Pad Thai",
            price="$12.50",
            confidence=0.95
        )
        
        description = DishDescription(
            text="A classic Thai stir-fried noodle dish with sweet and tangy flavors.",
            ingredients=["rice noodles", "shrimp", "tofu", "bean sprouts", "peanuts"],
            dietary_restrictions=["gluten-free option available"],
            cuisine_type="Thai",
            spice_level="medium",
            preparation_method="stir-fried",
            confidence=0.9
        )
        
        enriched_dish = EnrichedDish(
            dish=dish,
            images={},
            description=description,
            processing_status="complete"
        )
        
        result = self.results_service.format_results_for_display([enriched_dish])
        formatted_dish = result['dishes'][0]
        
        assert formatted_dish['description'] is not None
        assert formatted_dish['description']['text'] == description.text
        assert formatted_dish['description']['cuisine_type'] == "Thai"
        assert formatted_dish['description']['spice_level'] == "medium"
        assert formatted_dish['description']['has_details'] is True
        assert len(formatted_dish['description']['ingredients']) == 5
    
    def test_format_dish_no_price(self):
        """Test formatting a dish without price information."""
        dish = Dish(
            name="Mystery Dish",
            original_name="Mystery Dish",
            price="",
            confidence=0.7
        )
        
        enriched_dish = EnrichedDish(
            dish=dish,
            images={},
            processing_status="complete"
        )
        
        result = self.results_service.format_results_for_display([enriched_dish])
        formatted_dish = result['dishes'][0]
        
        assert formatted_dish['dish']['price']['has_price'] is False
        assert formatted_dish['dish']['price']['display'] == "Price not available"
        assert formatted_dish['dish']['price']['formatted'] == "N/A"
    
    def test_format_results_with_errors(self):
        """Test formatting results with processing errors."""
        dish = Dish(
            name="Test Dish",
            original_name="Test Dish",
            price="$10.00",
            confidence=0.8
        )
        
        enriched_dish = EnrichedDish(
            dish=dish,
            images={},
            processing_status="complete"
        )
        
        errors = [
            ProcessingError(
                type=ErrorType.IMAGE_SEARCH,
                message="Failed to find images for some dishes",
                recoverable=True
            ),
            ProcessingError(
                type=ErrorType.DESCRIPTION,
                message="AI service temporarily unavailable",
                recoverable=True
            )
        ]
        
        result = self.results_service.format_results_for_display([enriched_dish], errors)
        
        assert result['has_errors'] is True
        assert len(result['errors']) == 2
        assert result['success'] is True  # Still successful if we have dishes
    
    def test_create_error_summary(self):
        """Test creating error summary for display."""
        errors = [
            ProcessingError(
                type=ErrorType.OCR,
                message="OCR failed for image",
                recoverable=False
            ),
            ProcessingError(
                type=ErrorType.IMAGE_SEARCH,
                message="Image search quota exceeded",
                recoverable=True
            ),
            ProcessingError(
                type=ErrorType.IMAGE_SEARCH,
                message="Another image search error",
                recoverable=True
            )
        ]
        
        summary = self.results_service.create_error_summary(errors)
        
        assert summary['has_errors'] is True
        assert summary['total_count'] == 3
        assert summary['recoverable_count'] == 2
        assert "1 ocr error" in summary['summary']
        assert "2 image_search errors" in summary['summary']
        assert "(2 recoverable)" in summary['summary']
    
    def test_create_error_summary_empty(self):
        """Test creating error summary with no errors."""
        summary = self.results_service.create_error_summary([])
        
        assert summary['has_errors'] is False
        assert summary['summary'] == ''
        assert summary['details'] == []
        assert summary['total_count'] == 0
        assert summary['recoverable_count'] == 0
    
    def test_validate_results_data_valid(self):
        """Test validation of properly formatted results data."""
        valid_data = {
            'dishes': [
                {
                    'dish': {'id': '1', 'name': 'Test'},
                    'images': {'has_images': False},
                    'description': None
                }
            ],
            'total_count': 1,
            'errors': [],
            'has_errors': False,
            'success': True
        }
        
        assert self.results_service.validate_results_data(valid_data) is True
    
    def test_validate_results_data_invalid(self):
        """Test validation of improperly formatted results data."""
        invalid_data = {
            'dishes': 'not a list',  # Should be a list
            'total_count': 1
            # Missing required fields
        }
        
        assert self.results_service.validate_results_data(invalid_data) is False
    
    def test_format_images_with_dict_input(self):
        """Test formatting images when provided as dictionaries."""
        images_dict = {
            'primary': {
                'url': 'https://example.com/primary.jpg',
                'thumbnail_url': 'https://example.com/primary_thumb.jpg',
                'title': 'Primary Image'
            },
            'secondary': [
                {
                    'url': 'https://example.com/secondary1.jpg',
                    'title': 'Secondary Image 1'
                }
            ]
        }
        
        formatted = self.results_service._format_images(images_dict)
        
        assert formatted['has_images'] is True
        assert formatted['primary']['url'] == 'https://example.com/primary.jpg'
        assert len(formatted['secondary']) == 1
        assert formatted['secondary'][0]['url'] == 'https://example.com/secondary1.jpg'
    
    def test_format_images_no_images(self):
        """Test formatting when no images are provided."""
        formatted = self.results_service._format_images({})
        
        assert formatted['has_images'] is False
        assert formatted['primary'] is None
        assert formatted['secondary'] == []
    
    def test_format_price_edge_cases(self):
        """Test price formatting with various edge cases."""
        # Empty price
        result = self.results_service._format_price("")
        assert result['has_price'] is False
        assert result['display'] == "Price not available"
        
        # None price
        result = self.results_service._format_price(None)
        assert result['has_price'] is False
        
        # Whitespace only
        result = self.results_service._format_price("   ")
        assert result['has_price'] is False
        
        # Valid price with whitespace
        result = self.results_service._format_price("  $15.99  ")
        assert result['has_price'] is True
        assert result['display'] == "$15.99"
        assert result['original'] == "  $15.99  "