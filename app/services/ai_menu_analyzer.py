"""
AI Menu Analyzer Service - AI model-based menu analysis.

This module provides AI-powered menu analysis using vision models to directly extract
dish names and prices from menu images, replacing traditional OCR + parsing approach.
"""

import os
import base64
import hashlib
import time
import logging
from typing import List, Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.models.data_models import ParsedDish, ProcessingError, ErrorType, RequestCache


logger = logging.getLogger(__name__)


class AIMenuAnalyzer:
    """
    AI-powered menu analyzer that directly extracts dish information from images.
    
    Uses vision models to identify dishes and prices without traditional OCR preprocessing.
    """
    
    def __init__(self, cache: Optional[RequestCache] = None, timeout: int = 30):
        """
        Initialize AI menu analyzer.
        
        Args:
            cache: Optional cache instance for storing results
            timeout: Request timeout in seconds
        """
        self.cache = cache or RequestCache()
        self.timeout = timeout
        
        # Get API configuration
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model_name = os.getenv("AI_MODEL", "openai/gpt-4o")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        
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
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 500ms between requests
        
        logger.info(f"AI Menu Analyzer initialized with model: {self.model_name}")
    
    def analyze_menu(self, image_data: bytes) -> List[ParsedDish]:
        """
        Analyze menu image and extract dish information using AI model.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            List of ParsedDish objects with extracted information
            
        Raises:
            Exception: If analysis fails after all retries
        """
        # Generate cache key from image data
        image_hash = hashlib.md5(image_data).hexdigest()
        
        # Check cache first
        if self.cache:
            cached_result = self.cache.get_ai_analysis_result(image_hash)
            if cached_result:
                logger.info(f"AI analysis result found in cache for image hash: {image_hash[:8]}...")
                return cached_result
        
        # Rate limiting
        self._enforce_rate_limit()
        
        try:
            # Convert image to base64
            img_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare API request with proper response schema
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": self._get_analysis_prompt()
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_base64}"
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.0,
                "max_tokens": 2048,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "menu_analysis",
                        "schema": self._get_response_schema()
                    }
                }
            }
            
            # Make API request
            response = self.session.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Parse response
            result_data = response.json()
            content = result_data['choices'][0]['message']['content']
            
            # Parse JSON response
            import json
            analysis_result = json.loads(content)
            
            # Convert to ParsedDish objects
            dishes = self._convert_to_parsed_dishes(analysis_result)
            
            # Cache the result
            if self.cache:
                self.cache.set_ai_analysis_result(image_hash, dishes)
            
            logger.info(f"AI analysis successful. Found {len(dishes)} dishes")
            return dishes
            
        except requests.exceptions.RequestException as e:
            error_msg = f"AI analysis API request failed: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse AI analysis response: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"AI analysis failed: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def _get_analysis_prompt(self) -> str:
        """
        Get the prompt for AI menu analysis.
        
        Returns:
            Formatted prompt string
        """
        return """
Analyze this menu image and extract all visible dishes with their names and prices.

IMPORTANT: Return ONLY a valid JSON object with this exact structure:
{
  "dishes": [
    {
      "dish_name": "exact dish name as shown",
      "price": "price as shown (including currency symbol if present)"
    }
  ]
}

Rules:
- Extract ONLY dishes that are clearly visible and readable
- Use exact dish names as they appear on the menu
- Include prices exactly as shown (with currency symbols, decimals, etc.)
- If no price is visible for a dish, use null for the price field
- Ignore section headers, restaurant names, or non-food items
- If no dishes are found, return {"dishes": []}
- Do not include any text outside the JSON object
"""
    
    def _get_response_schema(self) -> Dict[str, Any]:
        """
        Get the JSON schema for AI response validation.
        
        Returns:
            JSON schema dictionary for menu analysis response
        """
        return {
            "type": "object",
            "properties": {
                "dishes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "dish_name": {
                                "type": "string",
                                "description": "Name of the dish as it appears on the menu"
                            },
                            "price": {
                                "type": ["string", "null"],
                                "description": "Price as shown on menu with currency symbol, or null if not visible"
                            }
                        },
                        "required": ["dish_name", "price"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["dishes"],
            "additionalProperties": False
        }
    
    def _convert_to_parsed_dishes(self, analysis_result: Dict[str, Any]) -> List[ParsedDish]:
        """
        Convert AI analysis result to ParsedDish objects.
        
        Args:
            analysis_result: Parsed JSON response from AI model
            
        Returns:
            List of ParsedDish objects
        """
        dishes = []
        
        if "dishes" not in analysis_result:
            logger.warning("No 'dishes' key found in AI analysis result")
            return dishes
        
        for dish_data in analysis_result["dishes"]:
            try:
                dish_name = dish_data.get("dish_name", "").strip()
                price = dish_data.get("price")
                
                if not dish_name:
                    continue
                
                # Clean up price if present
                if price and isinstance(price, str):
                    price = price.strip()
                    if not price or price.lower() == "null":
                        price = None
                
                # Create ParsedDish with high confidence (AI model is more reliable)
                parsed_dish = ParsedDish(
                    name=dish_name,
                    price=price,
                    confidence=0.9  # High confidence for AI-extracted data
                )
                
                dishes.append(parsed_dish)
                
            except Exception as e:
                logger.warning(f"Failed to parse dish data: {dish_data}, error: {e}")
                continue
        
        return dishes
    
    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between API requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def validate_api_key(self) -> bool:
        """
        Validate that the API key is working.
        
        Returns:
            True if API key is valid, False otherwise
        """
        if not self.api_key:
            return False
        
        try:
            # Create a minimal test request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": "Test"}],
                "max_tokens": 1
            }
            
            response = self.session.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"API key validation failed: {str(e)}")
            return False