"""
Tests for the Description Service.

This module contains unit tests for the DescriptionService class,
testing both successful operations and error handling scenarios.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from app.services.description_service import DescriptionService
from app.models.data_models import DishDescription


class TestDescriptionService:
    """Test cases for the DescriptionService class."""
    
    def test_init_with_api_key(self):
        """Test service initialization with API key."""
        service = DescriptionService(api_key="test-key")
        assert service.api_key == "test-key"
        assert service.model == "gpt-3.5-turbo"
    
    def test_init_without_api_key(self):
        """Test service initialization without API key."""
        with patch.dict('os.environ', {}, clear=True):
            service = DescriptionService()
            assert service.api_key is None
            assert service.client is None
    
    def test_is_available_with_client(self):
        """Test availability check when client is configured."""
        with patch('app.services.description_service.OpenAI') as mock_openai:
            mock_openai.return_value = Mock()
            service = DescriptionService(api_key="test-key")
            assert service.is_available() is True
    
    def test_is_available_without_client(self):
        """Test availability check when client is not configured."""
        service = DescriptionService()
        service.client = None
        assert service.is_available() is False
    
    def test_get_service_info(self):
        """Test service information retrieval."""
        service = DescriptionService(api_key="test-key")
        info = service.get_service_info()
        
        assert info['service_name'] == 'OpenAI Description Service'
        assert info['model'] == 'gpt-3.5-turbo'
        assert 'available' in info
        assert 'api_key_configured' in info
    
    def test_create_fallback_description(self):
        """Test fallback description creation."""
        service = DescriptionService()
        description = service._create_fallback_description("Test Dish")
        
        assert isinstance(description, DishDescription)
        assert description.text == "A delicious Test Dish dish."
        assert description.ingredients == []
        assert description.dietary_restrictions == []
        assert description.confidence == 0.1
    
    def test_create_description_prompt(self):
        """Test prompt creation for description generation."""
        service = DescriptionService()
        prompt = service._create_description_prompt(
            dish_name="Pad Thai",
            price="$12.95",
            menu_context="Thai restaurant"
        )
        
        assert "Pad Thai" in prompt
        assert "$12.95" in prompt
        assert "Thai restaurant" in prompt
        assert "JSON" in prompt
    
    def test_parse_response_valid_json(self):
        """Test parsing valid JSON response."""
        service = DescriptionService()
        response = json.dumps({
            "text": "Delicious Thai noodle dish",
            "ingredients": ["rice noodles", "shrimp", "peanuts"],
            "dietary_restrictions": ["gluten-free"],
            "cuisine_type": "Thai",
            "spice_level": "medium",
            "preparation_method": "stir-fried",
            "confidence": 0.9
        })
        
        description = service._parse_response(response, "Pad Thai")
        
        assert description.text == "Delicious Thai noodle dish"
        assert "rice noodles" in description.ingredients
        assert "gluten-free" in description.dietary_restrictions
        assert description.cuisine_type == "Thai"
        assert description.spice_level == "medium"
        assert description.confidence == 0.9
    
    def test_parse_response_invalid_json(self):
        """Test parsing invalid JSON response."""
        service = DescriptionService()
        response = "This is not valid JSON"
        
        description = service._parse_response(response, "Test Dish")
        
        assert isinstance(description, DishDescription)
        assert description.text == "A delicious Test Dish dish."
        assert description.confidence == 0.1
    
    def test_parse_response_with_code_blocks(self):
        """Test parsing JSON response wrapped in code blocks."""
        service = DescriptionService()
        response = """```json
        {
            "text": "Test description",
            "ingredients": ["test"],
            "confidence": 0.8
        }
        ```"""
        
        description = service._parse_response(response, "Test Dish")
        
        assert description.text == "Test description"
        assert description.confidence == 0.8
    
    @patch('app.services.description_service.OpenAI')
    def test_generate_description_success(self, mock_openai):
        """Test successful description generation."""
        # Mock the OpenAI client and response
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "text": "Authentic Thai stir-fried noodles",
            "ingredients": ["rice noodles", "shrimp"],
            "confidence": 0.85
        })
        
        mock_client.chat.completions.create.return_value = mock_response
        
        service = DescriptionService(api_key="test-key")
        description = service.generate_description("Pad Thai", "$12.95")
        
        assert description.text == "Authentic Thai stir-fried noodles"
        assert "rice noodles" in description.ingredients
        assert description.confidence == 0.85
    
    @patch('app.services.description_service.OpenAI')
    def test_generate_description_api_error(self, mock_openai):
        """Test description generation with API error."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        service = DescriptionService(api_key="test-key")
        description = service.generate_description("Test Dish")
        
        # Should return fallback description
        assert description.text == "A delicious Test Dish dish."
        assert description.confidence == 0.1
    
    def test_generate_description_no_client(self):
        """Test description generation without client."""
        service = DescriptionService()
        service.client = None
        
        description = service.generate_description("Test Dish")
        
        # Should return fallback description
        assert description.text == "A delicious Test Dish dish."
        assert description.confidence == 0.1
    
    @patch('app.services.description_service.OpenAI')
    def test_generate_batch_descriptions(self, mock_openai):
        """Test batch description generation."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        # Mock responses for each dish
        responses = [
            json.dumps({"text": f"Description for dish {i}", "confidence": 0.8})
            for i in range(3)
        ]
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        
        # Set up side effect to return different responses
        mock_client.chat.completions.create.side_effect = [
            Mock(choices=[Mock(message=Mock(content=resp))]) for resp in responses
        ]
        
        service = DescriptionService(api_key="test-key")
        dishes = [
            {"name": "Dish 1", "price": "$10"},
            {"name": "Dish 2", "price": "$15"},
            {"name": "Dish 3", "price": "$20"}
        ]
        
        descriptions = service.generate_batch_descriptions(dishes)
        
        assert len(descriptions) == 3
        for i, desc in enumerate(descriptions):
            assert f"Description for dish {i}" in desc.text
    
    def test_generate_batch_descriptions_empty_list(self):
        """Test batch generation with empty dish list."""
        service = DescriptionService(api_key="test-key")
        descriptions = service.generate_batch_descriptions([])
        
        assert descriptions == []
    
    def test_generate_batch_descriptions_invalid_dish(self):
        """Test batch generation with invalid dish data."""
        service = DescriptionService(api_key="test-key")
        dishes = [{"price": "$10"}]  # Missing name
        
        descriptions = service.generate_batch_descriptions(dishes)
        
        assert len(descriptions) == 1
        assert descriptions[0].text == "A delicious Unknown Dish dish."