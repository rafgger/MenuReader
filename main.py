"""
Main entry point for the Menu Image Analyzer application.
"""

from app.app import create_app
from app.config import get_config
import os


def main():
    """Main function to run the Flask application."""
    # Get configuration based on environment
    config_name = os.environ.get('FLASK_ENV', 'development')
    config = get_config(config_name)
    
    # Create Flask app
    app = create_app(config.__dict__)
    
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = config.DEBUG
    
    print(f"Starting Menu Image Analyzer on {host}:{port}")
    print(f"Environment: {config_name}")
    print(f"Debug mode: {debug}")
    
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
