"""
Tests for the data models module.
Run: pytest tests/test_data_models.py

"""

import pytest
from datetime import datetime
from app.models.data_models import (
    Dish, EnrichedDish, FoodImage, DishDescription, 
    ProcessingState, ProcessingError, ProcessingStep, ErrorType,
    OCRResult, ParsedDish, MenuAnalysisResult, APIConfig, RequestCache
)


class TestDish:
    """Test cases for the Dish model."""
    
    def test_dish_creation(self):
        """Test creating a basic dish."""
        dish = Dish(
            name="Pasta Carbonara",
            original_name="Pasta Carbonara",
            price="$15.99",
            confidence=0.95
        )
        
        assert dish.name == "Pasta Carbonara"
        assert dish.original_name == "Pasta Carbonara"
        assert dish.price == "$15.99"
        assert dish.confidence == 0.95
        assert dish.id is not None  # UUID should be generated
        assert isinstance(dish.position, dict)
    
    def test_dish_validation(self):
        """Test dish validation rules."""
        # Test minimum name length
        with pytest.raises(ValueError):
            Dish(name="", original_name="test")
        
        # Test confidence bounds
        with pytest.raises(ValueError):
            Dish(name="test", original_name="test", confidence=1.5)
        
        with pytest.raises(ValueError):
            Dish(name="test", original_name="test", confidence=-0.1)


class TestFoodImage:
    """Test cases for the FoodImage model."""
    
    def test_food_image_creation(self):
        """Test creating a food image."""
        image = FoodImage(
            url="https://example.com/image.jpg",
            thumbnail_url="https://example.com/thumb.jpg",
            title="Delicious Pasta",
            source="example.com",
            width=800,
            height=600
        )
        
        assert image.url == "https://example.com/image.jpg"
        assert image.thumbnail_url == "https://example.com/thumb.jpg"
        assert image.title == "Delicious Pasta"
        assert image.source == "example.com"
        assert image.width == 800
        assert image.height == 600
        assert image.load_status == "loading"  # Default value


class TestDishDescription:
    """Test cases for the DishDescription model."""
    
    def test_dish_description_creation(self):
        """Test creating a dish description."""
        description = DishDescription(
            text="A classic Italian pasta dish with eggs, cheese, and pancetta",
            ingredients=["pasta", "eggs", "parmesan", "pancetta"],
            dietary_restrictions=["contains gluten", "contains dairy"],
            cuisine_type="Italian",
            spice_level="mild",
            preparation_method="pan-fried",
            confidence=0.9
        )
        
        assert description.text == "A classic Italian pasta dish with eggs, cheese, and pancetta"
        assert "pasta" in description.ingredients
        assert "contains gluten" in description.dietary_restrictions
        assert description.cuisine_type == "Italian"
        assert description.spice_level == "mild"
        assert description.confidence == 0.9


class TestEnrichedDish:
    """Test cases for the EnrichedDish model."""
    
    def test_enriched_dish_creation(self):
        """Test creating an enriched dish."""
        dish = Dish(name="Test Dish", original_name="Test Dish")
        description = DishDescription(text="Test description")
        
        enriched = EnrichedDish(
            dish=dish,
            description=description,
            processing_status="complete"
        )
        
        assert enriched.dish.name == "Test Dish"
        assert enriched.description.text == "Test description"
        assert enriched.processing_status == "complete"
        assert isinstance(enriched.images, dict)


class TestProcessingState:
    """Test cases for the ProcessingState dataclass."""
    
    def test_processing_state_creation(self):
        """Test creating a processing state."""
        state = ProcessingState(
            current_step=ProcessingStep.OCR,
            progress=50,
            errors=[],
            start_time=""
        )
        
        assert state.current_step == ProcessingStep.OCR
        assert state.progress == 50
        assert isinstance(state.errors, list)
        assert state.start_time != ""  # Should be set in __post_init__


class TestProcessingError:
    """Test cases for the ProcessingError dataclass."""
    
    def test_processing_error_creation(self):
        """Test creating a processing error."""
        error = ProcessingError(
            type=ErrorType.OCR,
            message="OCR failed to extract text",
            dish_id="123",
            recoverable=True,
            timestamp=""
        )
        
        assert error.type == ErrorType.OCR
        assert error.message == "OCR failed to extract text"
        assert error.dish_id == "123"
        assert error.recoverable is True
        assert error.timestamp != ""  # Should be set in __post_init__


class TestRequestCache:
    """Test cases for the RequestCache class."""
    
    def test_cache_operations(self):
        """Test basic cache operations."""
        cache = RequestCache()
        
        # Test OCR result caching
        ocr_result = OCRResult(text="test text", confidence=0.9)
        cache.set_ocr_result("hash123", ocr_result)
        retrieved = cache.get_ocr_result("hash123")
        assert retrieved.text == "test text"
        assert retrieved.confidence == 0.9
        
        # Test image search caching
        images = [FoodImage(url="test.jpg", thumbnail_url="thumb.jpg")]
        cache.set_image_search_result("pasta", images)
        retrieved_images = cache.get_image_search_result("pasta")
        assert len(retrieved_images) == 1
        assert retrieved_images[0].url == "test.jpg"
        
        # Test description caching
        description = DishDescription(text="test description")
        cache.set_description("pasta", description)
        retrieved_desc = cache.get_description("pasta")
        assert retrieved_desc.text == "test description"
        
        # Test cache clearing
        cache.clear()
        assert cache.get_ocr_result("hash123") is None
        assert cache.get_image_search_result("pasta") is None
        assert cache.get_description("pasta") is None


class TestAPIConfig:
    """Test cases for the APIConfig model."""
    
    def test_api_config_creation(self):
        """Test creating API configuration."""
        config = APIConfig(
            ocr={"api_key": "test_key", "endpoint": "https://api.example.com"},
            image_search={"cx": "search_engine_id", "key": "api_key"},
            ai_description={"model": "gpt-3.5-turbo", "api_key": "openai_key"}
        )
        
        assert config.ocr["api_key"] == "test_key"
        assert config.image_search["cx"] == "search_engine_id"
        assert config.ai_description["model"] == "gpt-3.5-turbo"