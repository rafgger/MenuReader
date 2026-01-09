"""
Menu Image Analyzer Flask Application

This module contains the main Flask application factory and configuration.
"""

from typing import Optional
from flask import Flask, request, jsonify, render_template
import os
import logging
from werkzeug.exceptions import RequestEntityTooLarge, BadRequest


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
    
    @app.route('/')
    def index():
        """Main application page."""
        return render_template('index.html')
    
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'service': 'menu-image-analyzer'
        })
    
    @app.route('/upload', methods=['POST'])
    def upload_image():
        """Handle image upload endpoint."""
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
            
            # TODO: Process the uploaded image
            # This will be implemented in subsequent tasks
            
            return jsonify({
                'message': 'File uploaded successfully',
                'filename': file.filename,
                'status': 'processing'
            })
            
        except Exception as e:
            app.logger.error(f'Upload error: {e}')
            return jsonify({
                'error': 'Upload failed',
                'message': 'An error occurred while processing your upload'
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