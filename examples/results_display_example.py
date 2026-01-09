#!/usr/bin/env python3
"""
Results Display Example

This example demonstrates the results display functionality with mock data.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.results_service import ResultsService
from app.models.data_models import (
    Dish, EnrichedDish, FoodImage, DishDescription, ProcessingError, ErrorType
)


def create_mock_dishes():
    """Create mock dishes for demonstration."""
    dishes = []
    
    # Dish 1: Complete dish with all information
    dish1 = Dish(
        name="Pad Thai",
        original_name="Pad Thai",
        price="$12.99",
        confidence=0.95
    )
    
    primary_image1 = FoodImage(
        url="https://example.com/pad-thai.jpg",
        thumbnail_url="https://example.com/pad-thai-thumb.jpg",
        title="Delicious Pad Thai",
        source="example.com",
        width=800,
        height=600,
        load_status="loaded"
    )
    
    secondary_images1 = [
        FoodImage(
            url="https://example.com/pad-thai-2.jpg",
            thumbnail_url="https://example.com/pad-thai-2-thumb.jpg",
            title="Pad Thai Close-up",
            source="example.com",
            width=400,
            height=300,
            load_status="loaded"
        ),
        FoodImage(
            url="https://example.com/pad-thai-3.jpg",
            thumbnail_url="https://example.com/pad-thai-3-thumb.jpg",
            title="Pad Thai Ingredients",
            source="example.com",
            width=600,
            height=400,
            load_status="loaded"
        )
    ]
    
    description1 = DishDescription(
        text="A classic Thai stir-fried noodle dish featuring rice noodles tossed with shrimp, tofu, bean sprouts, and a perfect balance of sweet, sour, and savory flavors. Garnished with crushed peanuts and lime.",
        ingredients=["rice noodles", "shrimp", "tofu", "bean sprouts", "peanuts", "lime", "fish sauce", "tamarind"],
        dietary_restrictions=["gluten-free option available", "can be made vegetarian"],
        cuisine_type="Thai",
        spice_level="medium",
        preparation_method="stir-fried",
        confidence=0.92
    )
    
    enriched_dish1 = EnrichedDish(
        dish=dish1,
        images={
            'primary': primary_image1,
            'secondary': secondary_images1
        },
        description=description1,
        processing_status="complete"
    )
    
    dishes.append(enriched_dish1)
    
    # Dish 2: Dish with no images
    dish2 = Dish(
        name="Tom Yum Soup",
        original_name="Tom Yum Soup",
        price="$8.50",
        confidence=0.88
    )
    
    description2 = DishDescription(
        text="A hot and sour Thai soup with aromatic herbs, mushrooms, and your choice of protein. Known for its distinctive spicy and tangy flavor profile.",
        ingredients=["lemongrass", "kaffir lime leaves", "galangal", "mushrooms", "chili", "lime juice"],
        dietary_restrictions=["gluten-free", "dairy-free"],
        cuisine_type="Thai",
        spice_level="hot",
        preparation_method="simmered",
        confidence=0.89
    )
    
    enriched_dish2 = EnrichedDish(
        dish=dish2,
        images={},
        description=description2,
        processing_status="complete"
    )
    
    dishes.append(enriched_dish2)
    
    # Dish 3: Dish with no description and no price
    dish3 = Dish(
        name="Green Curry",
        original_name="แกงเขียวหวาน",
        price="",
        confidence=0.75
    )
    
    primary_image3 = FoodImage(
        url="https://example.com/green-curry.jpg",
        thumbnail_url="https://example.com/green-curry-thumb.jpg",
        title="Thai Green Curry",
        source="example.com",
        width=600,
        height=450,
        load_status="loaded"
    )
    
    enriched_dish3 = EnrichedDish(
        dish=dish3,
        images={
            'primary': primary_image3,
            'secondary': []
        },
        description=None,
        processing_status="partial"
    )
    
    dishes.append(enriched_dish3)
    
    return dishes


def create_mock_errors():
    """Create mock processing errors for demonstration."""
    return [
        ProcessingError(
            type=ErrorType.IMAGE_SEARCH,
            message="Could not find images for 1 dish due to API rate limiting",
            recoverable=True
        ),
        ProcessingError(
            type=ErrorType.DESCRIPTION,
            message="AI description service temporarily unavailable for 1 dish",
            recoverable=True
        )
    ]


def main():
    """Run the results display example."""
    print("Results Display Example")
    print("=" * 50)
    
    # Initialize the results service
    results_service = ResultsService()
    
    # Create mock data
    mock_dishes = create_mock_dishes()
    mock_errors = create_mock_errors()
    
    print(f"Created {len(mock_dishes)} mock dishes")
    print(f"Created {len(mock_errors)} mock errors")
    print()
    
    # Format results for display
    formatted_results = results_service.format_results_for_display(
        mock_dishes, mock_errors
    )
    
    print("Formatted Results Summary:")
    print(f"- Total dishes: {formatted_results['total_count']}")
    print(f"- Success: {formatted_results['success']}")
    print(f"- Has errors: {formatted_results['has_errors']}")
    print(f"- Error count: {len(formatted_results['errors'])}")
    print()
    
    # Display each dish
    for i, dish_data in enumerate(formatted_results['dishes'], 1):
        print(f"Dish {i}: {dish_data['dish']['name']}")
        print(f"  Original: {dish_data['dish']['original_name']}")
        print(f"  Price: {dish_data['dish']['price']['display']}")
        print(f"  Has images: {dish_data['images']['has_images']}")
        if dish_data['images']['has_images']:
            print(f"  Primary image: {dish_data['images']['primary']['url']}")
            print(f"  Secondary images: {len(dish_data['images']['secondary'])}")
        
        if dish_data['description']:
            print(f"  Description: {dish_data['description']['text'][:100]}...")
            print(f"  Cuisine: {dish_data['description']['cuisine_type']}")
            print(f"  Spice level: {dish_data['description']['spice_level']}")
            print(f"  Ingredients: {len(dish_data['description']['ingredients'])}")
        else:
            print("  Description: Not available")
        
        print(f"  Status: {dish_data['processing_status']}")
        print()
    
    # Display error summary
    if formatted_results['has_errors']:
        error_summary = results_service.create_error_summary(formatted_results['errors'])
        print("Error Summary:")
        print(f"  {error_summary['summary']}")
        for detail in error_summary['details']:
            print(f"  - {detail['message']} (recoverable: {detail['recoverable']})")
    
    print("\nResults display formatting completed successfully!")
    
    # Validate the results data
    is_valid = results_service.validate_results_data(formatted_results)
    print(f"Results data validation: {'PASSED' if is_valid else 'FAILED'}")


if __name__ == "__main__":
    main()