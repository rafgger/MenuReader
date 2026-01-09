"""
Menu Processor - Main orchestration service for Menu Image Analyzer.

This module provides the MenuProcessor class that orchestrates the complete
workflow from image upload to enriched dish results with progress tracking,
comprehensive error handling, and secure API client integration.
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
    ProcessingError, ErrorType, OCRResult, ParsedDish, FoodImage, DishDescription,
    RequestCache
)
from app.services.secure_api_client import SecureAPIClient, APIProvider
from app.services.ocr_service import OCRService
from app.services.google_vision_ocr_service import GoogleVisionOCRService
from app.services.menu_parser import MenuParser
from app.services.image_search_service import ImageSearchService
from app.services.description_service import DescriptionService


logger = logging.getLogger(__name__)


class MenuProcessor:
    """
    Main orchestration service for menu image analysis with secure API integration.
    
    Coordinates OCR, parsing, image search, and AI description generation
    with progress tracking, error handling, state management, and secure API access.
    """
    
    def __init__(self, 
                 api_client: Optional[SecureAPIClient] = None,
                 cache: Optional[RequestCache] = None):
        """
        Initialize the menu processor with secure API client.
        
        Args:
            api_client: Secure API client for external service communication
            cache: Optional shared cache instance
        """
        self.api_client = api_client or SecureAPIClient()
        self.cache = cache or RequestCache()
        self.logger = logging.getLogger(__name__)
        
        # Initialize services with secure API client
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
        """Initialize all external services with secure API client."""
        try:
            # Initialize OCR service
            if self.api_client.is_configured(APIProvider.GOOGLE_VISION):
                self.ocr_service = GoogleVisionOCRService(cache=self.cache)
                self.logger.info("Using Google Vision OCR with secure API client")
            else:
                # Fallback to generic OCR service
                self.ocr_service = OCRService(
                    api_key=os.getenv('OCR_API_KEY', ''),
                    cache=self.cache
                )
                self.logger.warning("Google Vision not configured, using fallback OCR")
            
            # Initialize menu parser
            self.menu_parser = MenuParser()
            
            # Initialize image search service
            if self.api_client.is_configured(APIProvider.GOOGLE_SEARCH):
                credentials = self.api_client.credentials[APIProvider.GOOGLE_SEARCH]
                self.image_search_service = ImageSearchService(
                    api_key=credentials.api_key,
                    search_engine_id=credentials.additional_params.get('engine_id', ''),
                    cache=self.cache
                )
                self.logger.info("Image search service initialized with secure API client")
            else:
                self.image_search_service = None
                self.logger.warning("Image search service not available - missing credentials")
            
            # Initialize description service
            if self.api_client.is_configured(APIProvider.OPENAI):
                credentials = self.api_client.credentials[APIProvider.OPENAI]
                self.description_service = DescriptionService(api_key=credentials.api_key)
                self.logger.info("Description service initialized with secure API client")
            else:
                self.description_service = None
                self.logger.warning("Description service not available - missing OpenAI API key")
                
        except Exception as e:
            self.logger.error(f"Error initializing services: {str(e)}")
            raise
    
    def _log_service_status(self) -> None:
        """Log the status of all services for debugging."""
        provider_status = self.api_client.get_provider_status()
        
        for provider, status in provider_status.items():
            if status['configured']:
                self.logger.info(f"{provider} API: Configured ({status['api_key_masked']})")
            else:
                self.logger.warning(f"{provider} API: Not configured - {status.get('error', 'Unknown error')}")
    
    def process_menu(self, image_data: bytes, 
                    processing_id: Optional[str] = None,
                    progress_callback: Optional[Callable[[ProcessingState], None]] = None) -> MenuAnalysisResult:
        """
        Process a menu image through the complete analysis pipeline with security.
        
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
            self.logger.info(f"Starting secure menu processing for ID: {processing_id}")
            
            # Validate image data security
            if not self._validate_image_security(image_data):
                error = ProcessingError(
                    type=ErrorType.PARSING,
                    message="Image data failed security validation",
                    recoverable=False
                )
                self._add_error(processing_id, error)
                return self._create_failed_result(processing_id, [error])
            
            # Step 1: OCR Text Extraction
            self._update_progress(processing_id, ProcessingStep.OCR, 10)
            ocr_result = self._perform_ocr(image_data, processing_id)
            
            if not ocr_result or not ocr_result.text.strip():
                error = ProcessingError(
                    type=ErrorType.OCR,
                    message="No text could be extracted from the image",
                    recoverable=False
                )
                self._add_error(processing_id, error)
                return self._create_failed_result(processing_id, [error])
            
            # Step 2: Menu Parsing
            self._update_progress(processing_id, ProcessingStep.PARSING, 30)
            parsed_dishes = self._parse_menu_text(ocr_result, processing_id)
            
            if not parsed_dishes:
                error = ProcessingError(
                    type=ErrorType.PARSING,
                    message="No dishes could be identified in the menu",
                    recoverable=False
                )
                self._add_error(processing_id, error)
                return self._create_failed_result(processing_id, [error])
            
            # Step 3: Dish Enrichment (Images + Descriptions)
            self._update_progress(processing_id, ProcessingStep.ENRICHMENT, 50)
            enriched_dishes = self._enrich_dishes(parsed_dishes, processing_id)
            
            # Step 4: Complete
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
            
            self.logger.info(f"Secure menu processing completed for ID: {processing_id}. "
                           f"Found {len(enriched_dishes)} dishes in {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Menu processing failed for ID: {processing_id}: {str(e)}", exc_info=True)
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
        """
        Validate image data for security concerns.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            True if image passes security validation
        """
        try:
            # Check minimum size
            if len(image_data) < 100:
                self.logger.warning("Image data too small for security validation")
                return False
            
            # Check maximum size (prevent DoS)
            max_size = 50 * 1024 * 1024  # 50MB
            if len(image_data) > max_size:
                self.logger.warning(f"Image data too large: {len(image_data)} bytes")
                return False
            
            # Check for valid image headers
            valid_headers = [
                b'\xFF\xD8\xFF',  # JPEG
                b'\x89PNG\r\n\x1a\n',  # PNG
                b'RIFF',  # WebP (starts with RIFF)
            ]
            
            has_valid_header = any(image_data.startswith(header) for header in valid_headers)
            if not has_valid_header:
                self.logger.warning("Image data does not have valid image header")
                return False
            
            # Additional WebP validation
            if image_data.startswith(b'RIFF') and b'WEBP' not in image_data[:20]:
                self.logger.warning("RIFF file is not WebP format")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Image security validation failed: {e}")
            return False
    
    def _perform_ocr(self, image_data: bytes, processing_id: str) -> Optional[OCRResult]:
        """
        Perform OCR text extraction on the image.
        
        Args:
            image_data: Raw image bytes
            processing_id: Processing ID for error tracking
            
        Returns:
            OCRResult or None if extraction fails
        """
        try:
            self.logger.info(f"Starting OCR extraction for processing ID: {processing_id}")
            result = self.ocr_service.extract_text(image_data)
            
            self.logger.info(f"OCR completed. Text length: {len(result.text)}, "
                           f"Confidence: {result.confidence:.2f}, Language: {result.language}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"OCR extraction failed: {str(e)}")
            error = ProcessingError(
                type=ErrorType.OCR,
                message=f"Text extraction failed: {str(e)}",
                recoverable=True
            )
            self._add_error(processing_id, error)
            return None
    
    def _parse_menu_text(self, ocr_result: OCRResult, processing_id: str) -> List[ParsedDish]:
        """
        Parse OCR text to extract dish information.
        
        Args:
            ocr_result: OCR extraction result
            processing_id: Processing ID for error tracking
            
        Returns:
            List of parsed dishes
        """
        try:
            self.logger.info(f"Starting menu parsing for processing ID: {processing_id}")
            dishes = self.menu_parser.parse_dishes(ocr_result)
            
            self.logger.info(f"Menu parsing completed. Found {len(dishes)} dishes")
            
            # Log parsing statistics
            stats = self.menu_parser.get_parsing_statistics(dishes)
            self.logger.debug(f"Parsing statistics: {stats}")
            
            return dishes
            
        except Exception as e:
            self.logger.error(f"Menu parsing failed: {str(e)}")
            error = ProcessingError(
                type=ErrorType.PARSING,
                message=f"Menu parsing failed: {str(e)}",
                recoverable=True
            )
            self._add_error(processing_id, error)
            return []
    
    def _enrich_dishes(self, parsed_dishes: List[ParsedDish], processing_id: str) -> List[EnrichedDish]:
        """
        Enrich parsed dishes with images and descriptions.
        
        Args:
            parsed_dishes: List of parsed dishes
            processing_id: Processing ID for progress tracking
            
        Returns:
            List of enriched dishes
        """
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
        """
        Enrich a single dish with images and description.
        
        Args:
            parsed_dish: Parsed dish to enrich
            processing_id: Processing ID for error tracking
            
        Returns:
            EnrichedDish or None if enrichment fails
        """
        try:
            # Convert ParsedDish to Dish
            dish = Dish(
                name=parsed_dish.name,
                original_name=parsed_dish.name,
                price=parsed_dish.price,
                confidence=parsed_dish.confidence
            )
            
            # Search for images
            images = {}
            if self.image_search_service:
                try:
                    food_images = self.image_search_service.search_food_images(
                        dish.name, max_results=5
                    )
                    if food_images:
                        images['primary'] = food_images[0]
                        images['secondary'] = food_images[1:] if len(food_images) > 1 else []
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
        """
        Update processing progress and notify callbacks.
        
        Args:
            processing_id: Processing ID
            step: Current processing step
            progress: Progress percentage (0-100)
        """
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
        """
        Add an error to the processing state.
        
        Args:
            processing_id: Processing ID
            error: Error to add
        """
        with self.state_lock:
            if processing_id in self.processing_states:
                self.processing_states[processing_id].errors.append(error)
    
    def _create_failed_result(self, processing_id: str, errors: List[ProcessingError]) -> MenuAnalysisResult:
        """
        Create a failed result with error information.
        
        Args:
            processing_id: Processing ID
            errors: List of errors that occurred
            
        Returns:
            MenuAnalysisResult indicating failure
        """
        with self.state_lock:
            state = self.processing_states.get(processing_id)
            processing_time = time.time() - state.start_time if state else 0.0
        
        return MenuAnalysisResult(
            dishes=[],
            processing_time=processing_time,
            errors=errors,
            success=False
        )
    
    def get_processing_state(self, processing_id: str) -> Optional[ProcessingState]:
        """
        Get the current processing state for a given ID.
        
        Args:
            processing_id: Processing ID to query
            
        Returns:
            ProcessingState or None if not found
        """
        with self.state_lock:
            return self.processing_states.get(processing_id)
    
    def cancel_processing(self, processing_id: str) -> bool:
        """
        Cancel an ongoing processing operation.
        
        Args:
            processing_id: Processing ID to cancel
            
        Returns:
            True if cancellation was successful
        """
        with self.state_lock:
            if processing_id in self.processing_states:
                # Add cancellation error
                error = ProcessingError(
                    type=ErrorType.NETWORK,
                    message="Processing was cancelled by user",
                    recoverable=False
                )
                self.processing_states[processing_id].errors.append(error)
                
                # Remove from active processing
                self.processing_states.pop(processing_id, None)
                self.progress_callbacks.pop(processing_id, None)
                
                self.logger.info(f"Processing cancelled for ID: {processing_id}")
                return True
        
        return False
    
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get status information about all services with security information.
        
        Returns:
            Dictionary with service status information
        """
        # Get API client status
        provider_status = self.api_client.get_provider_status()
        security_info = self.api_client.get_security_info()
        
        status = {
            'ocr_service': {
                'available': bool(self.ocr_service),
                'type': type(self.ocr_service).__name__ if self.ocr_service else None,
                'api_configured': APIProvider.GOOGLE_VISION.value in provider_status and 
                               provider_status[APIProvider.GOOGLE_VISION.value]['configured']
            },
            'image_search_service': {
                'available': bool(self.image_search_service),
                'api_configured': APIProvider.GOOGLE_SEARCH.value in provider_status and 
                               provider_status[APIProvider.GOOGLE_SEARCH.value]['configured'],
                'statistics': self.image_search_service.get_search_statistics() 
                            if self.image_search_service else None
            },
            'description_service': {
                'available': self.description_service.is_available() 
                           if self.description_service else False,
                'api_configured': APIProvider.OPENAI.value in provider_status and 
                               provider_status[APIProvider.OPENAI.value]['configured'],
                'info': self.description_service.get_service_info() 
                       if self.description_service else None
            },
            'cache': {
                'ocr_results': len(self.cache.ocr_results),
                'image_search_results': len(self.cache.image_search_results),
                'descriptions': len(self.cache.descriptions)
            },
            'active_processing': len(self.processing_states),
            'security': {
                'ssl_verification': security_info.get('ssl_verification', True),
                'rate_limiting_enabled': bool(security_info.get('rate_limiting_enabled', False)),
                'configured_providers': [p.value for p in security_info.get('configured_providers', [])]
            }
        }
        
        return status
    
    def validate_api_credentials(self) -> Dict[str, bool]:
        """
        Validate all API credentials using the secure API client.
        
        Returns:
            Dictionary with validation results for each service
        """
        try:
            return self.api_client.validate_all_credentials()
        except Exception as e:
            self.logger.error(f"API credential validation failed: {e}")
            return {
                'google_vision': False,
                'google_search': False,
                'openai': False
            }
    
    def clear_cache(self) -> None:
        """Clear all service caches and API client history."""
        self.cache.clear()
        if self.image_search_service:
            self.image_search_service.clear_cache()
        self.api_client.clear_request_history()
        self.logger.info("All caches and API history cleared")