#!/usr/bin/env python3
"""
Example usage of the Description Service for generating AI-powered dish descriptions.

This example demonstrates how to use the DescriptionService to generate
comprehensive descriptions for menu items including ingredients, dietary
information, and cultural context.
"""

import os
import sys
from dotenv import load_dotenv

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.description_service import DescriptionService


def main():
    """Demonstrate the Description Service functionality."""
    # Load environment variables
    load_dotenv()
    
    print("=== Menu Image Analyzer - Description Service Example ===\n")
    
    # Initialize the service
    service = DescriptionService()
    
    # Check if service is available
    if not service.is_available():
        print("❌ Description service is not available.")
        print("Please set OPENAI_API_KEY in your .env file.")
        return
    
    print("✅ Description service initialized successfully")
    print(f"Service info: {service.get_service_info()}\n")
    
    # Example dishes to generate descriptions for
    example_dishes = [
        {"name": "Pad Thai", "price": "$12.95"},
        {"name": "Chicken Tikka Masala", "price": "$15.50"},
        {"name": "Margherita Pizza", "price": "$14.00"},
        {"name": "Beef Bourguignon", "price": "$24.95"},
        {"name": "Sushi Platter", "price": "$28.00"},
        {"name": "Unknown Dish", "price": "$10.00"}  # Test fallback
    ]
    
    print("Generating descriptions for example dishes...\n")
    
    for i, dish in enumerate(example_dishes, 1):
        print(f"--- Dish {i}: {dish['name']} ---")
        
        try:
            # Generate description
            description = service.generate_description(
                dish_name=dish['name'],
                price=dish['price']
            )
            
            # Display results
            print(f"Description: {description.text}")
            print(f"Ingredients: {', '.join(description.ingredients) if description.ingredients else 'Not specified'}")
            print(f"Dietary Info: {', '.join(description.dietary_restrictions) if description.dietary_restrictions else 'Not specified'}")
            print(f"Cuisine Type: {description.cuisine_type or 'Not specified'}")
            print(f"Spice Level: {description.spice_level or 'Not specified'}")
            print(f"Preparation: {description.preparation_method or 'Not specified'}")
            print(f"Confidence: {description.confidence:.2f}")
            
        except Exception as e:
            print(f"❌ Error generating description: {e}")
        
        print()
    
    # Test batch processing
    print("--- Testing Batch Processing ---")
    try:
        batch_dishes = [
            {"name": "Caesar Salad", "price": "$9.95"},
            {"name": "Fish and Chips", "price": "$16.50"},
            {"name": "Ramen Bowl", "price": "$13.00"}
        ]
        
        descriptions = service.generate_batch_descriptions(batch_dishes)
        
        for dish, desc in zip(batch_dishes, descriptions):
            print(f"{dish['name']}: {desc.text[:50]}... (confidence: {desc.confidence:.2f})")
            
    except Exception as e:
        print(f"❌ Error in batch processing: {e}")
    
    print("\n=== Example completed ===")


if __name__ == "__main__":
    main()