"""
AI Description Generation Service for Menu Image Analyzer.

This service integrates with OpenAI API to generate comprehensive dish descriptions
including ingredients, dietary information, cultural context, and preparation methods.
"""

import os
import logging
import json
from typing import Optional, List, Dict, Any
import openai
from openai import OpenAI
import time
from dataclasses import asdict

from ..models.data_models import DishDescription, ProcessingError, ErrorType


class DescriptionService:
    """Service for generating AI-powered dish descriptions using OpenAI API."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        Initialize the Description Service.
        
        Args:
            api_key: OpenAI API key. If None, will try to get from environment.
            model: OpenAI model to use for generation.
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.client = None
        self.logger = logging.getLogger(__name__)
        
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
                self.logger.info("OpenAI client initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        else:
            self.logger.warning("No OpenAI API key provided")
    
    def generate_description(self, dish_name: str, price: str = "", 
                           menu_context: str = "") -> DishDescription:
        """
        Generate a comprehensive description for a dish.
        
        Args:
            dish_name: Name of the dish to describe
            price: Price of the dish (optional)
            menu_context: Additional context from the menu (optional)
            
        Returns:
            DishDescription object with generated content
        """
        if not self.client:
            self.logger.error("OpenAI client not available")
            return self._create_fallback_description(dish_name)
        
        try:
            # Create the prompt for description generation
            prompt = self._create_description_prompt(dish_name, price, menu_context)
            
            # Make API call with retry logic
            response = self._make_api_call(prompt)
            
            if response:
                return self._parse_response(response, dish_name)
            else:
                return self._create_fallback_description(dish_name)
                
        except Exception as e:
            self.logger.error(f"Error generating description for '{dish_name}': {e}")
            return self._create_fallback_description(dish_name)
    
    def _create_description_prompt(self, dish_name: str, price: str = "", 
                                 menu_context: str = "") -> str:
        """
        Create a well-engineered prompt for dish description generation.
        
        Args:
            dish_name: Name of the dish
            price: Price information
            menu_context: Additional menu context
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a knowledgeable food expert helping diners understand menu items. 
Generate a comprehensive description for the following dish that will help someone decide whether to order it.

Dish Name: {dish_name}"""
        
        if price:
            prompt += f"\nPrice: {price}"
        
        if menu_context:
            prompt += f"\nMenu Context: {menu_context}"
        
        prompt += """

Please provide a JSON response with the following structure:
{
    "text": "A concise, appetizing description (2-3 sentences) that explains what the dish is and what makes it special",
    "ingredients": ["list", "of", "key", "ingredients"],
    "dietary_restrictions": ["vegetarian", "vegan", "gluten-free", "dairy-free", "nut-free", "spicy", etc.],
    "cuisine_type": "Type of cuisine (e.g., Italian, Thai, Mexican, etc.)",
    "spice_level": "mild, medium, or hot (if applicable)",
    "preparation_method": "Brief description of how it's prepared (e.g., grilled, fried, steamed, etc.)",
    "confidence": 0.85
}

Guidelines:
- Keep the main description appetizing and informative
- Only include dietary restrictions that are clearly applicable
- Be specific about ingredients when possible
- Include cultural context if the dish is from a specific tradition
- Set confidence between 0.7-0.95 based on how well-known the dish is
- If you're unsure about any field, use null or empty array
- Focus on helping diners make informed choices

Respond only with valid JSON."""
        
        return prompt
    
    def _make_api_call(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """
        Make API call to OpenAI with retry logic.
        
        Args:
            prompt: The prompt to send
            max_retries: Maximum number of retry attempts
            
        Returns:
            Response text or None if failed
        """
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system", 
                            "content": "You are a helpful food expert who provides accurate, concise dish descriptions in JSON format."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    temperature=0.7,
                    timeout=30
                )
                
                if response.choices and response.choices[0].message:
                    return response.choices[0].message.content
                    
            except openai.RateLimitError as e:
                self.logger.warning(f"Rate limit hit on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                continue
                
            except openai.APITimeoutError as e:
                self.logger.warning(f"API timeout on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.5)  # Reduced from 1 second
                continue
                
            except Exception as e:
                self.logger.error(f"API call failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.5)  # Reduced from 1 second
                continue
        
        return None
    
    def _parse_response(self, response: str, dish_name: str) -> DishDescription:
        """
        Parse the JSON response from OpenAI into a DishDescription object.
        
        Args:
            response: JSON response string from OpenAI
            dish_name: Original dish name for fallback
            
        Returns:
            DishDescription object
        """
        try:
            # Clean the response - sometimes OpenAI adds extra text
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            data = json.loads(response)
            
            # Validate and extract fields with defaults
            return DishDescription(
                text=data.get('text', f"A delicious {dish_name} dish."),
                ingredients=data.get('ingredients', []),
                dietary_restrictions=data.get('dietary_restrictions', []),
                cuisine_type=data.get('cuisine_type'),
                spice_level=data.get('spice_level'),
                preparation_method=data.get('preparation_method'),
                confidence=float(data.get('confidence', 0.8))
            )
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            self.logger.debug(f"Raw response: {response}")
            return self._create_fallback_description(dish_name)
            
        except Exception as e:
            self.logger.error(f"Error parsing response: {e}")
            return self._create_fallback_description(dish_name)
    
    def _create_fallback_description(self, dish_name: str) -> DishDescription:
        """
        Create a basic fallback description when AI generation fails.
        
        Args:
            dish_name: Name of the dish
            
        Returns:
            Basic DishDescription object
        """
        return DishDescription(
            text=f"A delicious {dish_name} dish.",
            ingredients=[],
            dietary_restrictions=[],
            cuisine_type=None,
            spice_level=None,
            preparation_method=None,
            confidence=0.1  # Low confidence for fallback
        )
    
    def generate_batch_descriptions(self, dishes: List[Dict[str, str]], 
                                  max_concurrent: int = 3) -> List[DishDescription]:
        """
        Generate descriptions for multiple dishes with rate limiting.
        
        Args:
            dishes: List of dish dictionaries with 'name' and optional 'price'
            max_concurrent: Maximum concurrent API calls
            
        Returns:
            List of DishDescription objects
        """
        descriptions = []
        
        for dish in dishes:
            dish_name = dish.get('name', '')
            price = dish.get('price', '')
            
            if not dish_name:
                descriptions.append(self._create_fallback_description("Unknown Dish"))
                continue
            
            description = self.generate_description(dish_name, price)
            descriptions.append(description)
            
            # Small delay to respect rate limits
            time.sleep(0.1)
        
        return descriptions
    
    def is_available(self) -> bool:
        """
        Check if the description service is available and configured.
        
        Returns:
            True if service is ready to use
        """
        return self.client is not None and self.api_key is not None
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the service configuration.
        
        Returns:
            Dictionary with service information
        """
        return {
            'service_name': 'OpenAI Description Service',
            'model': self.model,
            'available': self.is_available(),
            'api_key_configured': bool(self.api_key)
        }