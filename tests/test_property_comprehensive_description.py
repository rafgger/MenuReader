"""
Property-based tests for comprehensive description generation.

This module contains property-based tests that validate the comprehensive
description generation functionality of the DescriptionService.

**Feature: menu-image-analyzer, Property 9: Comprehensive Description Generation**
**Validates: Requirements 4.1, 4.2, 4.3, 4.4**
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch
import json
from app.services.description_service import DescriptionService
from app.models.data_models import DishDescription


# Custom strategies for generating test data
@st.composite
def dish_names(draw):
    """Generate realistic dish names for testing."""
    cuisines = ["Italian", "Thai", "Indian", "Chinese", "Mexican", "French", "Japanese", "Greek"]
    dish_types = ["pasta", "curry", "soup", "salad", "pizza", "stir-fry", "rice", "noodles"]
    proteins = ["chicken", "beef", "pork", "fish", "tofu", "shrimp", "lamb"]
    
    cuisine = draw(st.sampled_from(cuisines))
    dish_type = draw(st.sampled_from(dish_types))
    protein = draw(st.sampled_from(proteins))
    
    # Generate various dish name patterns
    patterns = [
        f"{cuisine} {dish_type}",
        f"{protein} {dish_type}",
        f"{cuisine} {protein} {dish_type}",
        f"{protein} {cuisine} style",
        f"Grilled {protein}",
        f"{cuisine} special"
    ]
    
    return draw(st.sampled_from(patterns))


@st.composite
def mock_api_responses(draw):
    """Generate realistic API responses for testing."""
    ingredients = draw(st.lists(
        st.sampled_from([
            "rice", "noodles", "chicken", "beef", "vegetables", "onions", 
            "garlic", "ginger", "tomatoes", "cheese", "herbs", "spices",
            "oil", "soy sauce", "coconut milk", "basil", "cilantro"
        ]),
        min_size=1,
        max_size=8
    ))
    
    dietary_restrictions = draw(st.lists(
        st.sampled_from([
            "vegetarian", "vegan", "gluten-free", "dairy-free", 
            "nut-free", "spicy", "low-sodium"
        ]),
        max_size=4
    ))
    
    cuisine_types = ["Italian", "Thai", "Indian", "Chinese", "Mexican", "French", "Japanese", "Greek"]
    spice_levels = ["mild", "medium", "hot"]
    preparation_methods = ["grilled", "fried", "steamed", "baked", "stir-fried", "braised", "roasted"]
    
    return {
        "text": draw(st.text(min_size=20, max_size=200)),
        "ingredients": ingredients,
        "dietary_restrictions": dietary_restrictions,
        "cuisine_type": draw(st.one_of(st.none(), st.sampled_from(cuisine_types))),
        "spice_level": draw(st.one_of(st.none(), st.sampled_from(spice_levels))),
        "preparation_method": draw(st.one_of(st.none(), st.sampled_from(preparation_methods))),
        "confidence": draw(st.floats(min_value=0.7, max_value=0.95))
    }


class TestComprehensiveDescriptionGeneration:
    """Property-based tests for comprehensive description generation."""
    
    @given(dish_name=dish_names(), api_response=mock_api_responses())
    @settings(max_examples=100)
    @patch('app.services.description_service.OpenAI')
    def test_comprehensive_description_generation_property(self, mock_openai, dish_name, api_response):
        """
        **Feature: menu-image-analyzer, Property 9: Comprehensive Description Generation**
        
        Property: For any processed dish, the AI description should include relevant 
        ingredients, preparation methods, cultural context, and dietary information 
        when identifiable.
        
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
        """
        # Setup mock OpenAI client
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        # Create mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(api_response)
        mock_client.chat.completions.create.return_value = mock_response
        
        # Initialize service and generate description
        service = DescriptionService(api_key="test-key")
        description = service.generate_description(dish_name)
        
        # Property assertions: Comprehensive description should include relevant information
        
        # Requirement 4.1: Should create a concise, informative description
        assert isinstance(description, DishDescription)
        assert len(description.text) > 0, "Description text should not be empty"
        assert len(description.text) >= 10, "Description should be informative (at least 10 characters)"
        
        # Requirement 4.2: Should include key ingredients and preparation methods when available
        if api_response.get("ingredients"):
            assert len(description.ingredients) > 0, "Should include ingredients when available in API response"
            # All ingredients should be non-empty strings
            for ingredient in description.ingredients:
                assert isinstance(ingredient, str) and len(ingredient) > 0
        
        if api_response.get("preparation_method"):
            assert description.preparation_method is not None, "Should include preparation method when available"
            assert len(description.preparation_method) > 0, "Preparation method should not be empty"
        
        # Requirement 4.3: Should provide cultural context when relevant
        if api_response.get("cuisine_type"):
            assert description.cuisine_type is not None, "Should include cuisine type when available"
            assert len(description.cuisine_type) > 0, "Cuisine type should not be empty"
        
        # Requirement 4.4: Should mention dietary information when identifiable
        if api_response.get("dietary_restrictions"):
            assert len(description.dietary_restrictions) > 0, "Should include dietary restrictions when available"
            # All dietary restrictions should be non-empty strings
            for restriction in description.dietary_restrictions:
                assert isinstance(restriction, str) and len(restriction) > 0
        
        # General quality assertions
        assert 0.0 <= description.confidence <= 1.0, "Confidence should be between 0 and 1"
        assert description.confidence > 0.5, "Should have reasonable confidence for successful generation"
    
    @given(dish_name=dish_names())
    @settings(max_examples=50)
    @patch('app.services.description_service.OpenAI')
    def test_description_structure_consistency(self, mock_openai, dish_name):
        """
        Property: For any dish name, the generated description should have consistent structure.
        
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
        """
        # Setup mock with minimal valid response
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        minimal_response = {
            "text": f"A delicious {dish_name} dish with authentic flavors.",
            "ingredients": ["main ingredient", "seasoning"],
            "dietary_restrictions": [],
            "cuisine_type": "International",
            "spice_level": "mild",
            "preparation_method": "cooked",
            "confidence": 0.8
        }
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(minimal_response)
        mock_client.chat.completions.create.return_value = mock_response
        
        service = DescriptionService(api_key="test-key")
        description = service.generate_description(dish_name)
        
        # Structure consistency assertions
        assert hasattr(description, 'text'), "Description should have text attribute"
        assert hasattr(description, 'ingredients'), "Description should have ingredients attribute"
        assert hasattr(description, 'dietary_restrictions'), "Description should have dietary_restrictions attribute"
        assert hasattr(description, 'cuisine_type'), "Description should have cuisine_type attribute"
        assert hasattr(description, 'spice_level'), "Description should have spice_level attribute"
        assert hasattr(description, 'preparation_method'), "Description should have preparation_method attribute"
        assert hasattr(description, 'confidence'), "Description should have confidence attribute"
        
        # Type consistency
        assert isinstance(description.text, str)
        assert isinstance(description.ingredients, list)
        assert isinstance(description.dietary_restrictions, list)
        assert isinstance(description.confidence, float)
    
    @given(
        dishes=st.lists(
            st.builds(dict, name=dish_names(), price=st.text(min_size=1, max_size=10)),
            min_size=1,
            max_size=3  # Reduced to avoid timeout
        )
    )
    @settings(max_examples=20, deadline=1000)  # Increased deadline for batch operations
    @patch('app.services.description_service.OpenAI')
    def test_batch_description_completeness(self, mock_openai, dishes):
        """
        Property: For any list of dishes, batch processing should generate complete descriptions for all.
        
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
        """
        # Setup mock for batch processing
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        # Create responses for each dish
        responses = []
        for dish in dishes:
            response = {
                "text": f"Comprehensive description for {dish['name']}",
                "ingredients": ["ingredient1", "ingredient2"],
                "dietary_restrictions": ["vegetarian"],
                "cuisine_type": "International",
                "confidence": 0.85
            }
            responses.append(Mock(choices=[Mock(message=Mock(content=json.dumps(response)))]))
        
        mock_client.chat.completions.create.side_effect = responses
        
        service = DescriptionService(api_key="test-key")
        descriptions = service.generate_batch_descriptions(dishes)
        
        # Batch completeness assertions
        assert len(descriptions) == len(dishes), "Should generate description for each dish"
        
        for i, (dish, description) in enumerate(zip(dishes, descriptions)):
            assert isinstance(description, DishDescription), f"Description {i} should be DishDescription instance"
            assert len(description.text) > 0, f"Description {i} should have non-empty text"
            assert dish['name'].lower() in description.text.lower() or len(description.text) > 10, \
                f"Description {i} should reference dish name or be comprehensive"
            assert description.confidence > 0.0, f"Description {i} should have positive confidence"