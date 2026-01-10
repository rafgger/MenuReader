"""
AI Menu Processor - AI model-based menu processing service.

This module provides the AIMenuProcessor class that uses AI vision models
instead of traditional OCR + parsing for menu analysis.
"""

import os
import time
import logging
import hashlib
from typing import List, Optional, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from app.models.data_models import (
    MenuAnalysisResult, EnrichedDish, Dish, ProcessingState, ProcessingStep,
    ProcessingError, ErrorType, ParsedDish, RequestCache
)
from app.services.secure_api_client import SecureAPIClient, APIProvider
from app.services.ai_menu_analyzer import AIMenuAnalyzer
from app.services.image_search_service import ImageSearchService
from app.services.description_service import DescriptionService


logger = logging.getLogger(__name__)


class AIMenuProcessor:
    """
    AI-powered menu processor that uses vision models for direct dish extraction.
    
    Replaces OCR + parsing with AI model analysis while maintaining the same interface.
    """
    
    def __init__(self, 
                 api_client: Optional[SecureAPIClient] = None,
                 cache: Optional[RequestCache] = None):
        """
        Initialize the AI menu processor.
        
        Args:
            api_client: Secure API client for external service communication
            cache: Optional shared cache instance
        """
        self.api_client = api_client or SecureAPIClient()
        self.cache = cache or RequestCache()
        self.logger = logging.getLogger(__name__)
        
        # Initialize services
        self._initialize_services()
        
        # Processing state management
        self.processing_states: Dict[str, ProcessingState] = {}
        self.state_lock = threading.Lock()
        
        # Progress tracking callbacks
        self.progress_callbacks: Dict[str, Callable[[ProcessingState], None]] = {}
        
        # Configuration
        self.max_concurrent_enrichment = 3
        self.processing_timeout = 300  # 5 minutes
        
        # Log initialization status
        self._log_service_status()
        
    def _initialize_services(self) -> None:
        """Initialize all external services."""
        try:
            # Initialize AI menu analyzer
            self.ai_analyzer = AIMenuAnalyzer(cache=self.cache)
            self.logger.info("AI Menu Analyzer initialized")
            
            # Initialize image search service
            if self.api_client.is_configured(APIProvider.GOOGLE_SEARCH):
                credentials = self.api_client.credentials[APIProvider.GOOGLE_SEARCH]
                self.image_search_service = ImageSearchService(
                    api_key=credentials.api_key,
                    search_engine_id=credentials.additional_params.get('engine_id', ''),
                    cache=self.cache
                )
                self.logger.info("Image search service initialized")
            else:
                self.image_search_service = None
                self.logger.warning("Image search service not available - missing credentials")
            
            # Initialize description service
            if self.api_client.is_configured(APIProvider.OPENAI):
                credentials = self.api_client.credentials[APIProvider.OPENAI]
                self.description_service = DescriptionService(api_key=credentials.api_key)
                self.logger.info("Description service initialized")
            else:
                self.description_service = None
                self.logger.warning("Description service not available - missing OpenAI API key")
                
        except Exception as e:
            self.logger.error(f"Error initializing services: {str(e)}")
            raise
    
    def _log_service_status(self) -> None:
        """Log the status of all services for debugging."""
        provider_status = self.api_client.get_provider_status()
        
        # Check AI analyzer
        try:
            if self.ai_analyzer.validate_api_key():
                self.logger.info("AI Menu Analyzer: Configured and validated")
            else:
                self.logger.warning("AI Menu Analyzer: API key validation failed")
        except Exception as e:
            self.logger.error(f"AI Menu Analyzer: Error - {e}")
        
        # Check other services
        for provider, status in provider_status.items():
            if status['configured']:
                self.logger.info(f"{provider} API: Configured ({status['api_key_masked']})")
            else:
                self.logger.warning(f"{provider} API: Not configured - {status.get('error', 'Unknown error')}")
    
    def process_menu(self, image_data: bytes, 
                    processing_id: Optional[str] = None,
                    progress_callback: Optional[Callable[[ProcessingState], None]] = None) -> MenuAnalysisResult:
        """
        Process a menu image using AI model analysis.
        
        Args:
            image_data: Raw image bytes
            processing_id: Optional unique ID for tracking progress
            progress_callback: Optional callback for progress updates
            
        Returns:
            MenuAnalysisResult with enriched dishes and processing information
        """
        # Generate processing ID if not provided
        if not processing_id:
            processing_id = hashlib.md5(image_data).hexdigest()[:16]
        
        # Initialize processing state
        processing_state = ProcessingState(
            current_step=ProcessingStep.UPLOAD,
            progress=0,
            errors=[],
            start_time=time.time()
        )
        
        with self.state_lock:
            self.processing_states[processing_id] = processing_state
            if progress_callback:
                self.progress_callbacks[processing_id] = progress_callback
        
        try:
            self.logger.info(f"Starting AI menu processing for ID: {processing_id}")
            
            # Validate image data
            if not self._validate_image_security(image_data):
                error = ProcessingError(
                    type=ErrorType.VALIDATION,
                    message="Image data failed security validation",
                    recoverable=False
                )
                self._add_error(processing_id, error)
                return self._create_failed_result(processing_id, [error])
            
            # Step 1: AI Analysis (replaces OCR + Parsing)
            self._update_progress(processing_id, ProcessingStep.OCR, 20)
            parsed_dishes = self._perform_ai_analysis(image_data, processing_id)
            
            if not parsed_dishes:
                error = ProcessingError(
                    type=ErrorType.PARSING,
                    message="No dishes could be identified in the menu",
                    recoverable=False
                )
                self._add_error(processing_id, error)
                return self._create_failed_result(processing_id, [error])
            
            # Step 2: Dish Enrichment (Images + Descriptions)
            self._update_progress(processing_id, ProcessingStep.ENRICHMENT, 50)
            enriched_dishes = self._enrich_dishes(parsed_dishes, processing_id)
            
            # Step 3: Complete
            self._update_progress(processing_id, ProcessingStep.COMPLETE, 100)
            
            # Create final result
            processing_time = time.time() - processing_state.start_time
            errors = processing_state.errors.copy()
            
            result = MenuAnalysisResult(
                dishes=enriched_dishes,
                processing_time=processing_time,
                errors=errors,
                success=len(enriched_dishes) > 0
            )
            
            self.logger.info(f"AI menu processing completed for ID: {processing_id}. "
                           f"Found {len(enriched_dishes)} dishes in {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"AI menu processing failed for ID: {processing_id}: {str(e)}", exc_info=True)
            error = ProcessingError(
                type=ErrorType.NETWORK,
                message=f"Processing failed: {str(e)}",
                recoverable=True
            )
            self._add_error(processing_id, error)
            return self._create_failed_result(processing_id, [error])
            
        finally:
            # Cleanup processing state
            with self.state_lock:
                self.processing_states.pop(processing_id, None)
                self.progress_callbacks.pop(processing_id, None)
    
    def _validate_image_security(self, image_data: bytes) -> bool:
        """Validate image data for security concerns."""
        try:
            # Check minimum size
            if len(image_data) < 100:
                return False
            
            # Check maximum size (prevent DoS)
            max_size = 50 * 1024 * 1024  # 50MB
            if len(image_data) > max_size:
                return False
            
            # Check for valid image headers
            valid_headers = [
                b'\xFF\xD8\xFF',  # JPEG
                b'\x89PNG\r\n\x1a\n',  # PNG
                b'RIFF',  # WebP
            ]
            
            has_valid_header = any(image_data.startswith(header) for header in valid_headers)
            if not has_valid_header:
                return False
            
            # Additional WebP validation
            if image_data.startswith(b'RIFF') and b'WEBP' not in image_data[:20]:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Image security validation failed: {e}")
            return False
    
    def _perform_ai_analysis(self, image_data: bytes, processing_id: str) -> List[ParsedDish]:
        """
        Perform AI analysis on the menu image.
        
        Args:
            image_data: Raw image bytes
            processing_id: Processing ID for error tracking
            
        Returns:
            List of ParsedDish objects or empty list if analysis fails
        """
        try:
            self.logger.info(f"Starting AI analysis for processing ID: {processing_id}")
            dishes = self.ai_analyzer.analyze_menu(image_data)
            
            self.logger.info(f"AI analysis completed. Found {len(dishes)} dishes")
            return dishes
            
        except Exception as e:
            self.logger.error(f"AI analysis failed: {str(e)}")
            error = ProcessingError(
                type=ErrorType.OCR,
                message=f"AI analysis failed: {str(e)}",
                recoverable=True
            )
            self._add_error(processing_id, error)
            return []
    
    def _enrich_dishes(self, parsed_dishes: List[ParsedDish], processing_id: str) -> List[EnrichedDish]:
        """Enrich parsed dishes with images and descriptions."""
        enriched_dishes = []
        total_dishes = len(parsed_dishes)
        
        # Process dishes with controlled concurrency
        with ThreadPoolExecutor(max_workers=self.max_concurrent_enrichment) as executor:
            # Submit enrichment tasks
            future_to_dish = {}
            for i, parsed_dish in enumerate(parsed_dishes):
                future = executor.submit(self._enrich_single_dish, parsed_dish, processing_id)
                future_to_dish[future] = (i, parsed_dish)
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_dish):
                dish_index, parsed_dish = future_to_dish[future]
                completed += 1
                
                try:
                    enriched_dish = future.result()
                    if enriched_dish:
                        enriched_dishes.append(enriched_dish)
                    
                    # Update progress
                    progress = 50 + int((completed / total_dishes) * 40)  # 50-90% range
                    self._update_progress(processing_id, ProcessingStep.ENRICHMENT, progress)
                    
                except Exception as e:
                    self.logger.error(f"Failed to enrich dish '{parsed_dish.name}': {str(e)}")
                    error = ProcessingError(
                        type=ErrorType.NETWORK,
                        message=f"Failed to enrich dish '{parsed_dish.name}': {str(e)}",
                        dish_id=parsed_dish.name,
                        recoverable=True
                    )
                    self._add_error(processing_id, error)
        
        # Sort dishes by confidence (highest first)
        enriched_dishes.sort(key=lambda d: d.dish.confidence, reverse=True)
        
        self.logger.info(f"Dish enrichment completed. {len(enriched_dishes)}/{total_dishes} dishes enriched")
        return enriched_dishes
    
    def _enrich_single_dish(self, parsed_dish: ParsedDish, processing_id: str) -> Optional[EnrichedDish]:
        """Enrich a single dish with images and description."""
        try:
            # Convert ParsedDish to Dish
            dish = Dish(
                name=parsed_dish.name,
                original_name=parsed_dish.name,
                price=parsed_dish.price,
                confidence=parsed_dish.confidence
            )
            
            # Search for images using simplified dish name (before first comma)
            images = {}
            if self.image_search_service:
                try:
                    # Use only the part before the first comma for better image search results
                    search_name = dish.name.split(',')[0].strip()
                    food_images = self.image_search_service.search_food_images(
                        search_name, max_results=5
                    )
                    if food_images:
                        images['primary'] = food_images[0].model_dump()
                        images['secondary'] = [img.model_dump() for img in food_images[1:]] if len(food_images) > 1 else []
                    else:
                        images['placeholder'] = True
                except Exception as e:
                    self.logger.warning(f"Image search failed for '{dish.name}': {str(e)}")
                    images['placeholder'] = True
            else:
                images['placeholder'] = True
            
            # Generate description
            description = None
            if self.description_service:
                try:
                    description = self.description_service.generate_description(
                        dish.name, dish.price
                    )
                except Exception as e: 
                    self.logger.warning(f"Description generation failed for '{dish.name}': {str(e)}")
            
            # Create enriched dish
            enriched_dish = EnrichedDish(
                dish=dish,
                images=images,
                description=description,
                processing_status='complete'
            )
            
            return enriched_dish
            
        except Exception as e:
            self.logger.error(f"Failed to enrich dish '{parsed_dish.name}': {str(e)}")
            return None
    
    def _update_progress(self, processing_id: str, step: ProcessingStep, progress: int) -> None:
        """Update processing progress and notify callbacks."""
        with self.state_lock:
            if processing_id in self.processing_states:
                state = self.processing_states[processing_id]
                state.current_step = step
                state.progress = progress
                
                # Notify progress callback if registered
                if processing_id in self.progress_callbacks:
                    try:
                        self.progress_callbacks[processing_id](state)
                    except Exception as e:
                        self.logger.error(f"Progress callback failed: {str(e)}")
    
    def _add_error(self, processing_id: str, error: ProcessingError) -> None:
        """Add an error to the processing state."""
        with self.state_lock:
            if processing_id in self.processing_states:
                self.processing_states[processing_id].errors.append(error)
    
    def _create_failed_result(self, processing_id: str, errors: List[ProcessingError]) -> MenuAnalysisResult:
        """Create a failed result with error information."""
        with self.state_lock:
            state = self.processing_states.get(processing_id)
            processing_time = time.time() - state.start_time if state else 0.0
        
        return MenuAnalysisResult(
            dishes=[],
            processing_time=processing_time,
            errors=errors,
            success=False
        )