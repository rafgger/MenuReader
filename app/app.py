"""
Menu Image Analyzer Flask Application

This module contains the main Flask application factory and configuration.
"""

from typing import Optional
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import os
import logging
import uuid
from werkzeug.exceptions import RequestEntityTooLarge, BadRequest
from app.services.results_service import ResultsService
from app.services.menu_processor import MenuProcessor
from app.models.data_models import EnrichedDish, ProcessingError, ProcessingState, RequestCache


def create_app(config: Optional[dict] = None) -> Flask:
    """
    Create and configure the Flask application.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__, template_folder='templates')
    
    # Default configuration
    app.config.update({
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB max file size
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev-key-change-in-production'),
        'UPLOAD_FOLDER': 'uploads',
        'ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg', 'webp'}
    })
    
    # Apply custom configuration if provided
    if config:
        app.config.update(config)
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register routes
    register_routes(app)
    
    return app


def register_error_handlers(app: Flask) -> None:
    """Register error handlers for the Flask application."""
    
    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(error):
        """Handle file size too large errors."""
        return jsonify({
            'error': 'File too large',
            'message': 'Please upload an image smaller than 16MB'
        }), 413
    
    @app.errorhandler(BadRequest)
    def handle_bad_request(error):
        """Handle bad request errors."""
        return jsonify({
            'error': 'Bad request',
            'message': 'Invalid request format or missing required data'
        }), 400
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle internal server errors."""
        app.logger.error(f'Internal server error: {error}')
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred. Please try again.'
        }), 500
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle not found errors."""
        return jsonify({
            'error': 'Not found',
            'message': 'The requested resource was not found'
        }), 404


def register_routes(app: Flask) -> None:
    """Register application routes."""
    
    # Initialize services
    results_service = ResultsService()
    
    # Initialize shared cache
    shared_cache = RequestCache()
    
    # Initialize menu processor with API keys from environment
    menu_processor = MenuProcessor(
        ocr_api_key=os.getenv('GOOGLE_VISION_API_KEY'),
        image_search_api_key=os.getenv('GOOGLE_SEARCH_API_KEY'),
        image_search_engine_id=os.getenv('GOOGLE_SEARCH_ENGINE_ID'),
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        cache=shared_cache
    )
    
    # Store processing results temporarily (in production, use Redis or database)
    processing_results = {}
    
    @app.route('/')
    def index():
        """Main application page."""
        return render_template('index.html')
    
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        service_status = menu_processor.get_service_status()
        return jsonify({
            'status': 'healthy',
            'service': 'menu-image-analyzer',
            'services': service_status
        })
    
    @app.route('/status/<processing_id>')
    def get_processing_status(processing_id: str):
        """Get processing status for a given ID."""
        try:
            # Check if processing is still active
            processing_state = menu_processor.get_processing_state(processing_id)
            
            if processing_state:
                # Processing is still active
                return jsonify({
                    'processing_id': processing_id,
                    'status': 'processing',
                    'current_step': processing_state.current_step.value,
                    'progress': processing_state.progress,
                    'errors': [
                        {
                            'type': error.type.value,
                            'message': error.message,
                            'recoverable': error.recoverable,
                            'dish_id': error.dish_id
                        } for error in processing_state.errors
                    ]
                })
            
            # Check if results are available
            if processing_id in processing_results:
                result = processing_results[processing_id]
                return jsonify({
                    'processing_id': processing_id,
                    'status': 'complete' if result.success else 'failed',
                    'progress': 100,
                    'dishes_found': len(result.dishes),
                    'processing_time': result.processing_time,
                    'errors': [
                        {
                            'type': error.type.value,
                            'message': error.message,
                            'recoverable': error.recoverable,
                            'dish_id': error.dish_id
                        } for error in result.errors
                    ]
                })
            
            # Processing ID not found
            return jsonify({
                'error': 'Processing ID not found',
                'message': 'The processing ID may have expired or is invalid'
            }), 404
            
        except Exception as e:
            app.logger.error(f'Status check error: {e}')
            return jsonify({
                'error': 'Status check failed',
                'message': 'Could not retrieve processing status'
            }), 500
    
    @app.route('/results/<processing_id>')
    def show_results(processing_id: str):
        """Display results for a processed menu."""
        try:
            # Check if results are available
            if processing_id not in processing_results:
                return jsonify({
                    'error': 'Results not found',
                    'message': 'Processing may still be in progress or results have expired'
                }), 404
            
            result = processing_results[processing_id]
            
            # Format results for JSON response
            formatted_dishes = []
            for enriched_dish in result.dishes:
                dish_data = {
                    'id': enriched_dish.dish.id,
                    'name': enriched_dish.dish.name,
                    'price': enriched_dish.dish.price,
                    'confidence': enriched_dish.dish.confidence,
                    'images': enriched_dish.images,
                    'description': None,
                    'processing_status': enriched_dish.processing_status
                }
                
                # Add description if available
                if enriched_dish.description:
                    dish_data['description'] = {
                        'text': enriched_dish.description.text,
                        'ingredients': enriched_dish.description.ingredients,
                        'dietary_restrictions': enriched_dish.description.dietary_restrictions,
                        'cuisine_type': enriched_dish.description.cuisine_type,
                        'spice_level': enriched_dish.description.spice_level,
                        'preparation_method': enriched_dish.description.preparation_method,
                        'confidence': enriched_dish.description.confidence
                    }
                
                formatted_dishes.append(dish_data)
            
            return jsonify({
                'processing_id': processing_id,
                'success': result.success,
                'dishes': formatted_dishes,
                'processing_time': result.processing_time,
                'total_dishes': len(result.dishes),
                'errors': [
                    {
                        'type': error.type.value,
                        'message': error.message,
                        'recoverable': error.recoverable,
                        'dish_id': error.dish_id
                    } for error in result.errors
                ]
            })
            
        except Exception as e:
            app.logger.error(f'Results retrieval error: {e}')
            return jsonify({
                'error': 'Results retrieval failed',
                'message': 'Could not retrieve processing results'
            }), 500
    
    @app.route('/results')
    def results_page():
        """Display results page with processed dishes."""
        try:
            # Get processing ID from query parameters
            processing_id = request.args.get('id')
            
            if not processing_id:
                return render_template('results.html', 
                                     dishes=[], 
                                     processing_status='error',
                                     errors=[{
                                         'message': 'No processing ID provided',
                                         'recoverable': False
                                     }])
            
            # Check if results are available
            if processing_id not in processing_results:
                return render_template('results.html', 
                                     dishes=[], 
                                     processing_status='not_found',
                                     errors=[{
                                         'message': 'Results not found or processing still in progress',
                                         'recoverable': True
                                     }])
            
            result = processing_results[processing_id]
            
            # Format results for display
            formatted_results = results_service.format_results_for_display(
                result.dishes, result.errors
            )
            
            return render_template('results.html', 
                                 dishes=formatted_results['dishes'],
                                 processing_status='complete' if result.success else 'error',
                                 errors=formatted_results['errors'],
                                 total_count=formatted_results['total_count'],
                                 processing_time=result.processing_time)
            
        except Exception as e:
            app.logger.error(f'Results page error: {e}')
            return render_template('results.html', 
                                 dishes=[], 
                                 processing_status='error',
                                 errors=[{
                                     'message': 'Error loading results page',
                                     'recoverable': False
                                 }])
    
    @app.route('/upload', methods=['POST'])
    def upload_image():
        """Handle image upload and start processing."""
        try:
            # Check if file is present in request
            if 'file' not in request.files:
                return jsonify({
                    'error': 'No file provided',
                    'message': 'Please select an image file to upload'
                }), 400
            
            file = request.files['file']
            
            # Check if file was selected
            if file.filename == '':
                return jsonify({
                    'error': 'No file selected',
                    'message': 'Please select an image file to upload'
                }), 400
            
            # Validate file type
            if not allowed_file(file.filename, app.config['ALLOWED_EXTENSIONS']):
                return jsonify({
                    'error': 'Invalid file type',
                    'message': 'Please upload a JPEG, PNG, or WebP image'
                }), 400
            
            # Read image data
            image_data = file.read()
            
            # Validate image size
            if len(image_data) == 0:
                return jsonify({
                    'error': 'Empty file',
                    'message': 'The uploaded file appears to be empty'
                }), 400
            
            # Generate processing ID
            processing_id = str(uuid.uuid4())[:16]
            
            # Define progress callback for real-time updates
            def progress_callback(state: ProcessingState):
                # In a real application, you might use WebSockets or Server-Sent Events
                # to push updates to the client
                app.logger.info(f"Processing {processing_id}: {state.current_step.value} - {state.progress}%")
            
            # Start processing in background (in production, use Celery or similar)
            try:
                result = menu_processor.process_menu(
                    image_data=image_data,
                    processing_id=processing_id,
                    progress_callback=progress_callback
                )
                
                # Store results
                processing_results[processing_id] = result
                
                # Return processing ID for status checking
                return jsonify({
                    'processing_id': processing_id,
                    'message': 'Image uploaded and processing started',
                    'status': 'processing'
                })
                
            except Exception as processing_error:
                app.logger.error(f'Processing failed: {processing_error}')
                return jsonify({
                    'error': 'Processing failed',
                    'message': f'Menu analysis failed: {str(processing_error)}'
                }), 500
            
        except Exception as e:
            app.logger.error(f'Upload error: {e}')
            return jsonify({
                'error': 'Upload failed',
                'message': 'An error occurred while processing your upload'
            }), 500
    
    @app.route('/cancel/<processing_id>', methods=['POST'])
    def cancel_processing(processing_id: str):
        """Cancel an ongoing processing operation."""
        try:
            success = menu_processor.cancel_processing(processing_id)
            
            if success:
                return jsonify({
                    'message': 'Processing cancelled successfully',
                    'processing_id': processing_id
                })
            else:
                return jsonify({
                    'error': 'Cancellation failed',
                    'message': 'Processing ID not found or already completed'
                }), 404
                
        except Exception as e:
            app.logger.error(f'Cancellation error: {e}')
            return jsonify({
                'error': 'Cancellation failed',
                'message': 'Could not cancel processing'
            }), 500


def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """
    Check if the uploaded file has an allowed extension.
    
    Args:
        filename: Name of the uploaded file
        allowed_extensions: Set of allowed file extensions
        
    Returns:
        True if file extension is allowed, False otherwise
    """
    return ('.' in filename and 
            filename.rsplit('.', 1)[1].lower() in allowed_extensions)


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)