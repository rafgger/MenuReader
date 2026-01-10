"""
Menu Image Analyzer Flask Application

This module contains the main Flask application factory and configuration
with enhanced security, CORS support, and secure API key management.
"""

from typing import Optional
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import logging
import uuid
from werkzeug.exceptions import RequestEntityTooLarge, BadRequest
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import get_config, validate_api_credentials
from app.services.results_service import ResultsService
from app.services.menu_processor import MenuProcessor
from app.services.secure_api_client import SecureAPIClient
from app.models.data_models import EnrichedDish, ProcessingError, ProcessingState, RequestCache


def create_app(config_name: Optional[str] = None) -> Flask:
    """
    Create and configure the Flask application with security enhancements.
    
    Args:
        config_name: Configuration name ('development', 'production', 'testing')
        
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__, template_folder='templates')
    
    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Configure logging
    configure_logging(app)
    
    # Add proxy fix for production deployments
    if not app.config.get('DEBUG', False):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Configure CORS
    configure_cors(app, config)
    
    # Configure rate limiting
    configure_rate_limiting(app)
    
    # Initialize secure API client
    api_client = SecureAPIClient()
    
    # Validate API credentials on startup
    validate_startup_credentials(api_client)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register routes
    register_routes(app, api_client)
    
    # Add security headers
    register_security_headers(app)
    
    app.logger.info("Flask application created successfully")
    return app


def configure_logging(app: Flask) -> None:
    """Configure application logging."""
    log_level = logging.DEBUG if app.config.get('DEBUG') else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s'
    )
    app.logger.setLevel(log_level)


def configure_cors(app: Flask, config) -> None:
    """
    Configure Cross-Origin Resource Sharing (CORS).
    
    Args:
        app: Flask application
        config: Application configuration
    """
    cors_origins = getattr(config, 'CORS_ORIGINS', [])
    
    if cors_origins:
        CORS(app, 
             origins=cors_origins,
             methods=['GET', 'POST', 'OPTIONS'],
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
             supports_credentials=True,
             max_age=3600)
        
        app.logger.info(f"CORS configured with origins: {cors_origins}")
    else:
        app.logger.warning("CORS not configured - no origins specified")


def configure_rate_limiting(app: Flask) -> None:
    """
    Configure rate limiting for API endpoints.
    
    Args:
        app: Flask application
    """
    try:
        limiter = Limiter(
            key_func=get_remote_address,
            app=app,
            default_limits=[app.config.get('RATELIMIT_DEFAULT', '100 per hour')],
            storage_uri=app.config.get('RATELIMIT_STORAGE_URL', 'memory://')
        )
        
        app.limiter = limiter
        app.logger.info("Rate limiting configured")
        
    except Exception as e:
        app.logger.warning(f"Failed to configure rate limiting: {e}")


def validate_startup_credentials(api_client: SecureAPIClient) -> None:
    """
    Validate API credentials on application startup.
    
    Args:
        api_client: Secure API client instance
    """
    try:
        validation_results = validate_api_credentials()
        
        for service, is_valid in validation_results.items():
            if is_valid:
                logging.info(f"{service} credentials validated successfully")
            else:
                logging.warning(f"{service} credentials not configured or invalid")
        
        # Log provider status
        provider_status = api_client.get_provider_status()
        for provider, status in provider_status.items():
            if status['configured']:
                logging.info(f"{provider} API client configured: {status['api_key_masked']}")
            else:
                logging.warning(f"{provider} API client not configured")
                
    except Exception as e:
        logging.error(f"Credential validation failed: {e}")


def register_security_headers(app: Flask) -> None:
    """
    Register security headers for all responses.
    
    Args:
        app: Flask application
    """
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Content Security Policy (basic)
        if not app.config.get('DEBUG'):
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https:; "
                "font-src 'self' data:;"
            )
            response.headers['Content-Security-Policy'] = csp
        
        return response


def register_error_handlers(app: Flask) -> None:
    """Register error handlers for the Flask application."""
    
    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(error):
        """Handle file size too large errors."""
        app.logger.warning(f"File too large error from {request.remote_addr}")
        return jsonify({
            'error': 'File too large',
            'message': 'Please upload an image smaller than 16MB',
            'error_code': 'FILE_TOO_LARGE'
        }), 413
    
    @app.errorhandler(BadRequest)
    def handle_bad_request(error):
        """Handle bad request errors."""
        app.logger.warning(f"Bad request from {request.remote_addr}: {error}")
        return jsonify({
            'error': 'Bad request',
            'message': 'Invalid request format or missing required data',
            'error_code': 'BAD_REQUEST'
        }), 400
    
    @app.errorhandler(429)
    def handle_rate_limit(error):
        """Handle rate limit errors."""
        app.logger.warning(f"Rate limit exceeded from {request.remote_addr}")
        return jsonify({
            'error': 'Rate limit exceeded',
            'message': 'Too many requests. Please try again later.',
            'error_code': 'RATE_LIMIT_EXCEEDED'
        }), 429
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle internal server errors."""
        app.logger.error(f'Internal server error: {error}', exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred. Please try again.',
            'error_code': 'INTERNAL_ERROR'
        }), 500
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle not found errors."""
        return jsonify({
            'error': 'Not found',
            'message': 'The requested resource was not found',
            'error_code': 'NOT_FOUND'
        }), 404


def register_routes(app: Flask, api_client: SecureAPIClient) -> None:
    """
    Register application routes with secure API client.
    
    Args:
        app: Flask application
        api_client: Secure API client instance
    """
    
    # Initialize services with secure API client
    results_service = ResultsService()
    
    # Initialize shared cache
    shared_cache = RequestCache()
    
    # Initialize menu processor with secure API client
    menu_processor = MenuProcessor(
        api_client=api_client,
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
        """Health check endpoint with security information."""
        try:
            # Get service status without exposing sensitive information
            config = app.config
            api_config = config.get_api_config() if hasattr(config, 'get_api_config') else {}
            
            return jsonify({
                'status': 'healthy',
                'service': 'menu-image-analyzer',
                'version': '1.0',
                'services': {
                    'ocr_configured': api_config.get('ocr_configured', False),
                    'image_search_configured': api_config.get('image_search_configured', False),
                    'ai_description_configured': api_config.get('ai_description_configured', False)
                },
                'security': {
                    'cors_enabled': bool(api_config.get('cors_origins')),
                    'rate_limiting': hasattr(app, 'limiter'),
                    'ssl_required': not app.config.get('DEBUG', False)
                }
            })
        except Exception as e:
            app.logger.error(f"Health check failed: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': 'Health check failed'
            }), 500
    
    @app.route('/api/config')
    def get_api_config():
        """Get API configuration status (without sensitive data)."""
        try:
            config = app.config
            if hasattr(config, 'get_api_config'):
                api_config = config.get_api_config()
                return jsonify(api_config)
            else:
                return jsonify({
                    'error': 'Configuration not available'
                }), 500
        except Exception as e:
            app.logger.error(f"Config endpoint error: {e}")
            return jsonify({
                'error': 'Failed to retrieve configuration'
            }), 500
    
    
    @app.route('/upload', methods=['POST'])
    @app.limiter.limit("10 per minute") if hasattr(app, 'limiter') else lambda f: f
    def upload_image():
        """Handle image upload and start processing with security validation."""
        try:
            # Validate request
            if not request.content_type or 'multipart/form-data' not in request.content_type:
                return jsonify({
                    'error': 'Invalid content type',
                    'message': 'Request must be multipart/form-data',
                    'error_code': 'INVALID_CONTENT_TYPE'
                }), 400
            
            # Check if file is present in request
            if 'file' not in request.files:
                return jsonify({
                    'error': 'No file provided',
                    'message': 'Please select an image file to upload',
                    'error_code': 'NO_FILE'
                }), 400
            
            file = request.files['file']
            
            # Check if file was selected
            if file.filename == '':
                return jsonify({
                    'error': 'No file selected',
                    'message': 'Please select an image file to upload',
                    'error_code': 'NO_FILE_SELECTED'
                }), 400
            
            # Validate file type
            if not allowed_file(file.filename, app.config['ALLOWED_EXTENSIONS']):
                return jsonify({
                    'error': 'Invalid file type',
                    'message': 'Please upload a JPEG, PNG, or WebP image',
                    'error_code': 'INVALID_FILE_TYPE'
                }), 400
            
            # Read image data
            image_data = file.read()
            
            # Validate image size
            if len(image_data) == 0:
                return jsonify({
                    'error': 'Empty file',
                    'message': 'The uploaded file appears to be empty',
                    'error_code': 'EMPTY_FILE'
                }), 400
            
            # Additional security: Check for malicious file headers
            if not is_valid_image_data(image_data):
                return jsonify({
                    'error': 'Invalid image data',
                    'message': 'The uploaded file does not appear to be a valid image',
                    'error_code': 'INVALID_IMAGE_DATA'
                }), 400
            
            # Generate processing ID
            processing_id = str(uuid.uuid4())[:16]
            
            # Log upload (without sensitive data)
            app.logger.info(f"Image upload started: {processing_id}, size: {len(image_data)} bytes, "
                          f"type: {file.content_type}, client: {request.remote_addr}")
            
            # Define progress callback for real-time updates
            def progress_callback(state: ProcessingState):
                app.logger.info(f"Processing {processing_id}: {state.current_step.value} - {state.progress}%")
            
            # Start processing
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
                app.logger.error(f'Processing failed for {processing_id}: {processing_error}', exc_info=True)
                return jsonify({
                    'error': 'Processing failed',
                    'message': f'Menu analysis failed: {str(processing_error)}',
                    'error_code': 'PROCESSING_FAILED'
                }), 500
            
        except Exception as e:
            app.logger.error(f'Upload error: {e}', exc_info=True)
            return jsonify({
                'error': 'Upload failed',
                'message': 'An error occurred while processing your upload',
                'error_code': 'UPLOAD_FAILED'
            }), 500
    
    @app.route('/status/<processing_id>')
    def get_processing_status(processing_id: str):
        """Get processing status for a given ID."""
        try:
            # Validate processing ID format
            if not processing_id or len(processing_id) != 16:
                return jsonify({
                    'error': 'Invalid processing ID',
                    'message': 'Processing ID format is invalid'
                }), 400
            
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
            app.logger.error(f'Status check error: {e}', exc_info=True)
            return jsonify({
                'error': 'Status check failed',
                'message': 'Could not retrieve processing status'
            }), 500
    
    @app.route('/results/<processing_id>')
    def show_results_json(processing_id: str):
        """Display results for a processed menu (JSON API)."""
        try:
            # Validate processing ID
            if not processing_id or len(processing_id) != 16:
                return jsonify({
                    'error': 'Invalid processing ID',
                    'message': 'Processing ID format is invalid'
                }), 400
            
            # Check if results are available
            if processing_id not in processing_results:
                return jsonify({
                    'error': 'Results not found',
                    'message': 'Processing may still be in progress or results have expired'
                }), 404
            
            result = processing_results[processing_id]
            
            # Format results for JSON response (without exposing internal data)
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
            app.logger.error(f'Results retrieval error: {e}', exc_info=True)
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
            app.logger.error(f'Results page error: {e}', exc_info=True)
            return render_template('results.html', 
                                 dishes=[], 
                                 processing_status='error',
                                 errors=[{
                                     'message': 'Error loading results page',
                                     'recoverable': False
                                 }])
    
    @app.route('/cancel/<processing_id>', methods=['POST'])
    def cancel_processing(processing_id: str):
        """Cancel an ongoing processing operation."""
        try:
            # Validate processing ID
            if not processing_id or len(processing_id) != 16:
                return jsonify({
                    'error': 'Invalid processing ID',
                    'message': 'Processing ID format is invalid'
                }), 400
            
            success = menu_processor.cancel_processing(processing_id)
            
            if success:
                app.logger.info(f"Processing cancelled: {processing_id}")
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
            app.logger.error(f'Cancellation error: {e}', exc_info=True)
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
    if not filename or '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in allowed_extensions


def is_valid_image_data(image_data: bytes) -> bool:
    """
    Validate that the uploaded data is actually image data.
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        True if data appears to be a valid image
    """
    if not image_data or len(image_data) < 10:
        return False
    
    # Check for common image file signatures
    image_signatures = [
        b'\xFF\xD8\xFF',  # JPEG
        b'\x89PNG\r\n\x1a\n',  # PNG
        b'RIFF',  # WebP (starts with RIFF)
        b'GIF87a',  # GIF87a
        b'GIF89a',  # GIF89a
    ]
    
    for signature in image_signatures:
        if image_data.startswith(signature):
            return True
    
    # Check for WebP specifically (RIFF + WEBP)
    if image_data.startswith(b'RIFF') and b'WEBP' in image_data[:20]:
        return True
    
    return False


if __name__ == '__main__':
    app = create_app()
    
    # Get configuration
    config = app.config
    debug_mode = config.get('DEBUG', False)
    port = int(os.environ.get('PORT', 5000))
    
    if debug_mode:
        app.logger.warning("Running in DEBUG mode - not suitable for production")
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)