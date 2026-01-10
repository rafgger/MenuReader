#!/usr/bin/env python3
"""
Simple launcher for the Menu Image Analyzer Flask application.
"""

import sys
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.app import create_app

if __name__ == '__main__':
    app = create_app()
    print("🍽️  Menu Image Analyzer - Starting Flask Application")
    print("=" * 60)
    print("✅ Server starting on http://localhost:5000")
    print("✅ OCR Service: Google Vision (Service Account)")
    print("⚠️  Image Search: Not configured (requires API keys)")
    print("⚠️  AI Descriptions: Not configured (requires OpenAI API)")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)