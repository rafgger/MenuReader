"""
Tests for the main Flask application.
"""

import pytest
import io
from app.app import create_app, allowed_file


class TestFlaskApp:
    """Test cases for the Flask application."""
    
    def test_app_creation(self):
        """Test that the Flask app can be created successfully."""
        app = create_app()
        assert app is not None
        assert app.config['TESTING'] is False
    
    def test_app_with_custom_config(self):
        """Test app creation with custom configuration."""
        custom_config = {
            'TESTING': True,
            'SECRET_KEY': 'test-key'
        }
        app = create_app(custom_config)
        assert app.config['TESTING'] is True
        assert app.config['SECRET_KEY'] == 'test-key'
    
    def test_health_check_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'menu-image-analyzer'
    
    def test_index_page(self, client):
        """Test the main index page."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Menu Image Analyzer' in response.data
        assert b'Take Photo' in response.data
        assert b'capture="environment"' in response.data
    
    def test_upload_no_file(self, client):
        """Test upload endpoint with no file."""
        response = client.post('/upload')
        assert response.status_code == 400
        
        data = response.get_json()
        assert data['error'] == 'No file provided'
    
    def test_upload_empty_filename(self, client):
        """Test upload endpoint with empty filename."""
        data = {'file': (io.BytesIO(b''), '')}
        response = client.post('/upload', data=data)
        assert response.status_code == 400
        
        response_data = response.get_json()
        assert response_data['error'] == 'No file selected'
    
    def test_upload_invalid_file_type(self, client):
        """Test upload endpoint with invalid file type."""
        data = {'file': (io.BytesIO(b'test data'), 'test.txt')}
        response = client.post('/upload', data=data)
        assert response.status_code == 400
        
        response_data = response.get_json()
        assert response_data['error'] == 'Invalid file type'
    
    def test_upload_valid_image(self, client, sample_image_data):
        """Test upload endpoint with valid image."""
        data = {'file': (io.BytesIO(sample_image_data), 'test.jpg')}
        response = client.post('/upload', data=data)
        assert response.status_code == 200
        
        response_data = response.get_json()
        assert response_data['message'] == 'Image uploaded and processing started'
        assert 'processing_id' in response_data
        assert response_data['status'] == 'processing'
    
    def test_404_error_handler(self, client):
        """Test 404 error handler."""
        response = client.get('/nonexistent')
        assert response.status_code == 404
        
        data = response.get_json()
        assert data['error'] == 'Not found'
    
    def test_results_page_route(self, client):
        """Test results page route."""
        response = client.get('/results')
        assert response.status_code == 200
        
        # Check that the response contains HTML
        assert b'<!DOCTYPE html>' in response.data
        assert b'Menu Analysis Results' in response.data
    
    def test_results_api_route(self, client):
        """Test results API route with processing ID."""
        response = client.get('/results/test-processing-id')
        assert response.status_code == 404  # No results stored for this ID
        
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == 'Results not found'


class TestUtilityFunctions:
    """Test cases for utility functions."""
    
    def test_allowed_file_valid_extensions(self):
        """Test allowed_file function with valid extensions."""
        allowed_extensions = {'jpg', 'png', 'webp'}
        
        assert allowed_file('test.jpg', allowed_extensions) is True
        assert allowed_file('test.JPG', allowed_extensions) is True
        assert allowed_file('test.png', allowed_extensions) is True
        assert allowed_file('test.webp', allowed_extensions) is True
    
    def test_allowed_file_invalid_extensions(self):
        """Test allowed_file function with invalid extensions."""
        allowed_extensions = {'jpg', 'png', 'webp'}
        
        assert allowed_file('test.txt', allowed_extensions) is False
        assert allowed_file('test.pdf', allowed_extensions) is False
        assert allowed_file('test.gif', allowed_extensions) is False
        assert allowed_file('test', allowed_extensions) is False
    
    def test_allowed_file_no_extension(self):
        """Test allowed_file function with no extension."""
        allowed_extensions = {'jpg', 'png', 'webp'}
        
        assert allowed_file('test', allowed_extensions) is False
        assert allowed_file('', allowed_extensions) is False