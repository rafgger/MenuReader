"""
Test for AI Menu Analyzer - Minimal automated test.

Tests the happy path and one edge case for the AI menu analysis functionality.
"""

import os
import json
import tempfile
from unittest.mock import Mock, patch
from PIL import Image, ImageDraw, ImageFont

from app.services.ai_menu_analyzer import AIMenuAnalyzer
from app.models.data_models import RequestCache, ParsedDish


def create_test_menu_image() -> bytes:
    """Create a simple test menu image with text."""
    # Create a simple menu image
    img = Image.new('RGB', (400, 300), color='white')
    draw = ImageDraw.Draw(img)
    
    # Add menu text
    try:
        # Try to use a default font
        font = ImageFont.load_default()
    except:
        font = None
    
    draw.text((20, 50), "MENU", fill='black', font=font)
    draw.text((20, 100), "Pasta Carbonara - $15.99", fill='black', font=font)
    draw.text((20, 130), "Caesar Salad - $12.50", fill='black', font=font)
    draw.text((20, 160), "Grilled Salmon - $22.00", fill='black', font=font)
    
    # Convert to bytes
    import io
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='JPEG')
    image_data = img_buffer.getvalue()
    
    return image_data


def test_ai_menu_analyzer_happy_path():
    """Test AI menu analyzer with successful response."""
    print("Testing AI Menu Analyzer - Happy Path")
    
    # Mock successful API response
    mock_response_data = {
        "dishes": [
            {"dish_name": "Pasta Carbonara", "price": "$15.99"},
            {"dish_name": "Caesar Salad", "price": "$12.50"},
            {"dish_name": "Grilled Salmon", "price": "$22.00"}
        ]
    }
    
    # Create test image
    image_data = create_test_menu_image()
    
    # Mock the API request
    with patch('requests.Session.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'choices': [{'message': {'content': json.dumps(mock_response_data)}}]
        }
        mock_post.return_value = mock_response
        
        # Set environment variable for test
        os.environ['OPENROUTER_API_KEY'] = 'test_key'
        
        try:
            # Initialize analyzer
            cache = RequestCache()
            analyzer = AIMenuAnalyzer(cache=cache)
            
            # Analyze menu
            dishes = analyzer.analyze_menu(image_data)
            
            # Verify results
            assert len(dishes) == 3, f"Expected 3 dishes, got {len(dishes)}"
            assert dishes[0].name == "Pasta Carbonara", f"Expected 'Pasta Carbonara', got '{dishes[0].name}'"
            assert dishes[0].price == "$15.99", f"Expected '$15.99', got '{dishes[0].price}'"
            assert dishes[0].confidence == 0.9, f"Expected 0.9 confidence, got {dishes[0].confidence}"
            
            print("✅ PASS: Happy path test successful")
            return True
            
        except Exception as e:
            print(f"❌ FAIL: Happy path test failed - {e}")
            return False


def test_ai_menu_analyzer_edge_case():
    """Test AI menu analyzer with empty response (edge case)."""
    print("Testing AI Menu Analyzer - Edge Case (No Dishes)")
    
    # Mock empty response
    mock_response_data = {"dishes": []}
    
    # Create test image
    image_data = create_test_menu_image()
    
    # Mock the API request
    with patch('requests.Session.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'choices': [{'message': {'content': json.dumps(mock_response_data)}}]
        }
        mock_post.return_value = mock_response
        
        # Set environment variable for test
        os.environ['OPENROUTER_API_KEY'] = 'test_key'
        
        try:
            # Initialize analyzer
            cache = RequestCache()
            analyzer = AIMenuAnalyzer(cache=cache)
            
            # Analyze menu
            dishes = analyzer.analyze_menu(image_data)
            
            # Verify results
            assert len(dishes) == 0, f"Expected 0 dishes, got {len(dishes)}"
            
            print("✅ PASS: Edge case test successful")
            return True
            
        except Exception as e:
            print(f"❌ FAIL: Edge case test failed - {e}")
            return False


def run_tests():
    """Run all tests and provide summary."""
    print("=" * 50)
    print("AI Menu Analyzer Test Suite")
    print("=" * 50)
    
    results = []
    
    # Run tests
    results.append(test_ai_menu_analyzer_happy_path())
    results.append(test_ai_menu_analyzer_edge_case())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 50)
    print(f"Test Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests PASSED!")
    else:
        print("⚠️  Some tests FAILED!")
    
    print("=" * 50)
    
    return passed == total


if __name__ == "__main__":
    run_tests()