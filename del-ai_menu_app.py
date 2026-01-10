"""
AI Menu Analyzer - Simple Flask app using AI model instead of OCR.

This module provides a Flask interface for AI-powered menu analysis
that directly extracts dish names and prices from menu images.
"""

import os
import base64
import json
import logging
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from dotenv import load_dotenv

from app.services.ai_menu_processor import AIMenuProcessor
from app.models.data_models import RequestCache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Load environment variables
load_dotenv()

# Initialize AI menu processor
cache = RequestCache()
menu_processor = AIMenuProcessor(cache=cache)

# Simple HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Menu Analyzer</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .upload-area { border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 20px 0; }
        .results { margin-top: 20px; }
        .dish { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .dish-name { font-weight: bold; font-size: 18px; color: #333; }
        .dish-price { color: #007bff; font-size: 16px; margin-top: 5px; }
        .confidence { color: #666; font-size: 12px; }
        .error { color: #dc3545; padding: 10px; background: #f8d7da; border-radius: 5px; }
        .success { color: #155724; padding: 10px; background: #d4edda; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>🍽️ AI Menu Analyzer</h1>
    <p>Upload a menu image to extract dish names and prices using AI vision models.</p>
    
    <form id="uploadForm" enctype="multipart/form-data">
        <div class="upload-area">
            <input type="file" id="imageInput" name="image" accept="image/*" required>
            <p>Choose a menu image (JPEG, PNG, WebP)</p>
        </div>
        <button type="submit">🔍 Analyze Menu</button>
    </form>
    
    <div id="results" class="results"></div>
    
    <script>
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData();
            const imageFile = document.getElementById('imageInput').files[0];
            
            if (!imageFile) {
                alert('Please select an image file');
                return;
            }
            
            formData.append('image', imageFile);
            
            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = '<p>Analyzing menu... Please wait.</p>';
            
            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.error) {
                    resultsDiv.innerHTML = `<div class="error">Error: ${data.error}</div>`;
                } else {
                    displayResults(data.result);
                }
            } catch (error) {
                resultsDiv.innerHTML = `<div class="error">Request failed: ${error.message}</div>`;
            }
        });
        
        function displayResults(result) {
            const resultsDiv = document.getElementById('results');
            
            if (!result.dishes || result.dishes.length === 0) {
                resultsDiv.innerHTML = '<div class="error">No dishes found in the menu image.</div>';
                return;
            }
            
            let html = `<div class="success">Found ${result.dishes.length} dishes in ${result.processing_time.toFixed(2)} seconds</div>`;
            
            result.dishes.forEach((enrichedDish, index) => {
                const dish = enrichedDish.dish;
                html += `
                    <div class="dish">
                        <div class="dish-name">${index + 1}. ${dish.name}</div>
                        ${dish.price ? `<div class="dish-price">Price: ${dish.price}</div>` : ''}
                        <div class="confidence">Confidence: ${(dish.confidence * 100).toFixed(1)}%</div>
                    </div>
                `;
            });
            
            resultsDiv.innerHTML = html;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the main page."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Analyze menu image using AI model."""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
        
        image = request.files['image']
        if image.filename == '':
            return jsonify({'error': 'No image selected'}), 400
            
        # Read image data
        img_bytes = image.read()
        
        logger.info(f"Processing menu image: {len(img_bytes)} bytes")
        
        # Process the menu using AI
        result = menu_processor.process_menu(image_data=img_bytes)
        
        if not result.success:
            error_messages = [error.message for error in result.errors]
            return jsonify({'error': '; '.join(error_messages)}), 500
        
        # Convert result to JSON-serializable format
        result_data = {
            'dishes': [],
            'processing_time': result.processing_time,
            'success': result.success
        }
        
        for enriched_dish in result.dishes:
            dish_data = {
                'dish': {
                    'name': enriched_dish.dish.name,
                    'price': enriched_dish.dish.price,
                    'confidence': enriched_dish.dish.confidence
                }
            }
            result_data['dishes'].append(dish_data)
        
        logger.info(f"Analysis completed: found {len(result.dishes)} dishes")
        
        return jsonify({'result': result_data})
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}", exc_info=True)
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/api/status')
def status():
    """Get service status."""
    try:
        # Check if AI analyzer is working
        ai_status = menu_processor.ai_analyzer.validate_api_key()
        
        return jsonify({
            'ai_analyzer': ai_status,
            'openrouter_configured': bool(os.getenv("OPENROUTER_API_KEY")),
            'model': os.getenv("AI_MODEL", "openai/gpt-4o")
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)