"""
Data models for the Menu Image Analyzer application.

This module contains Pydantic models for type-safe data handling throughout the application.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
import uuid
import time
from datetime import datetime


class ProcessingStep(Enum):
    """Enumeration of processing steps in the menu analysis pipeline."""
    UPLOAD = "upload"
    OCR = "ocr"
    PARSING = "parsing"
    ENRICHMENT = "enrichment"
    COMPLETE = "complete"


class ErrorType(Enum):
    """Enumeration of error types that can occur during processing."""
    OCR = "ocr"
    PARSING = "parsing"
    IMAGE_SEARCH = "image_search"
    DESCRIPTION = "description"
    NETWORK = "network"
    VALIDATION = "validation"


@dataclass
class ProcessingError:
    """Represents an error that occurred during processing."""
    type: ErrorType
    message: str
    dish_id: Optional[str] = None
    recoverable: bool = True
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class ProcessingState:
    """Tracks the current state of menu processing."""
    current_step: ProcessingStep
    progress: int  # 0-100
    errors: List[ProcessingError]
    start_time: float
    estimated_completion: Optional[str] = None
    
    def __post_init__(self):
        if not self.start_time:
            self.start_time = time.time()


class Dish(BaseModel):
    """Core dish data model extracted from menu."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, description="Name of the dish")
    original_name: str = Field(..., description="Original text from menu")
    price: str = Field(default="", description="Price as extracted from menu")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="OCR confidence score")
    position: Dict[str, int] = Field(default_factory=dict, description="Location in original image")


class FoodImage(BaseModel):
    """Represents a food image from search results."""
    url: str = Field(..., description="Full-size image URL")
    thumbnail_url: str = Field(..., description="Thumbnail image URL")
    title: str = Field(default="", description="Image title or description")
    source: str = Field(default="", description="Source website or domain")
    width: int = Field(default=0, ge=0, description="Image width in pixels")
    height: int = Field(default=0, ge=0, description="Image height in pixels")
    load_status: str = Field(default="loading", description="Image loading status")


class DishDescription(BaseModel):
    """AI-generated description of a dish."""
    text: str = Field(..., description="Main description text")
    ingredients: List[str] = Field(default_factory=list, description="List of ingredients")
    dietary_restrictions: List[str] = Field(default_factory=list, description="Dietary information")
    cuisine_type: Optional[str] = Field(None, description="Type of cuisine")
    spice_level: Optional[str] = Field(None, description="Spice level: mild, medium, hot")
    preparation_method: Optional[str] = Field(None, description="How the dish is prepared")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="AI confidence score")


class EnrichedDish(BaseModel):
    """Complete dish information with all enrichment data."""
    dish: Dish
    images: Dict[str, Any] = Field(default_factory=dict, description="Primary, secondary, placeholder images")
    description: Optional[DishDescription] = None
    processing_status: str = Field(default="pending", description="Processing status")


class OCRResult(BaseModel):
    """Result from OCR text extraction."""
    text: str = Field(..., description="Extracted text")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall confidence")
    language: str = Field(default="unknown", description="Detected language")
    bounding_boxes: List[Dict[str, Any]] = Field(default_factory=list, description="Text region coordinates")


class ParsedDish(BaseModel):
    """Dish information parsed from OCR text."""
    name: str = Field(..., min_length=1, description="Parsed dish name")
    price: str = Field(default="", description="Parsed price")
    description: Optional[str] = Field(None, description="Any description found in menu")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Parsing confidence")


class MenuAnalysisResult(BaseModel):
    """Complete result of menu analysis."""
    dishes: List[EnrichedDish] = Field(default_factory=list)
    processing_time: float = Field(default=0.0, ge=0.0, description="Total processing time in seconds")
    errors: List[ProcessingError] = Field(default_factory=list)
    success: bool = Field(default=False, description="Whether analysis was successful")


class APIConfig(BaseModel):
    """Configuration for external API integrations."""
    ocr: Dict[str, Any] = Field(default_factory=dict)
    image_search: Dict[str, Any] = Field(default_factory=dict)
    ai_description: Dict[str, Any] = Field(default_factory=dict)


class RequestCache:
    """Simple in-memory cache for API requests."""
    
    def __init__(self):
        self.ocr_results: Dict[str, OCRResult] = {}
        self.image_search_results: Dict[str, List[FoodImage]] = {}
        self.descriptions: Dict[str, DishDescription] = {}
    
    def clear(self) -> None:
        """Clear all cached data."""
        self.ocr_results.clear()
        self.image_search_results.clear()
        self.descriptions.clear()
    
    def get_ocr_result(self, image_hash: str) -> Optional[OCRResult]:
        """Get cached OCR result by image hash."""
        return self.ocr_results.get(image_hash)
    
    def set_ocr_result(self, image_hash: str, result: OCRResult) -> None:
        """Cache OCR result by image hash."""
        self.ocr_results[image_hash] = result
    
    def get_image_search_result(self, dish_name: str) -> Optional[List[FoodImage]]:
        """Get cached image search results by dish name."""
        return self.image_search_results.get(dish_name)
    
    def set_image_search_result(self, dish_name: str, images: List[FoodImage]) -> None:
        """Cache image search results by dish name."""
        self.image_search_results[dish_name] = images
    
    def get_description(self, dish_name: str) -> Optional[DishDescription]:
        """Get cached description by dish name."""
        return self.descriptions.get(dish_name)
    
    def set_description(self, dish_name: str, description: DishDescription) -> None:
        """Cache description by dish name."""
        self.descriptions[dish_name] = description