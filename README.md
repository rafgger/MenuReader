# Menu Image Analyzer

A Flask-based web application that transforms menu photos into rich, visual dining guides. Upload a photo of a restaurant menu and get detailed information about each dish including images and AI-generated descriptions.

## Features

- **Image Upload**: Support for JPEG, PNG, and WebP formats
- **OCR Processing**: Extract text from menu images in multiple languages
- **Dish Extraction**: Identify individual food items and prices
- **Image Search**: Find relevant food images for each dish
- **AI Descriptions**: Generate informative descriptions with ingredients and dietary information
- **Responsive UI**: Clean, mobile-friendly interface

## Quick Start

### Using uv (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd menu-image-analyzer

# Install dependencies with uv
uv sync

# Run the application
uv run python main.py
```

### Using pip

```bash
# Clone the repository
git clone <repository-url>
cd menu-image-analyzer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

The application will be available at `http://localhost:5000`

## Development

### Project Structure

```
menu-image-analyzer/
├── app/
│   ├── __init__.py
│   ├── app.py              # Main Flask application
│   ├── config.py           # Configuration settings
│   ├── models/
│   │   ├── __init__.py
│   │   └── data_models.py  # Pydantic data models
│   ├── routes/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   └── templates/
│       └── index.html      # Main UI template
├── tests/
│   ├── __init__.py
│   ├── conftest.py         # Test configuration
│   └── test_app.py         # Application tests
├── main.py                 # Application entry point
├── pyproject.toml          # Project configuration
├── requirements.txt        # Dependencies for deployment
└── README.md
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app

# Run specific test file
uv run pytest tests/test_app.py
```

### Environment Variables

For production deployment, set these environment variables:

- `FLASK_ENV`: Set to `production` for production deployment
- `SECRET_KEY`: Flask secret key for session security
- `OCR_API_KEY`: API key for OCR service
- `GOOGLE_SEARCH_API_KEY`: Google Custom Search API key
- `GOOGLE_SEARCH_ENGINE_ID`: Google Custom Search Engine ID
- `OPENAI_API_KEY`: OpenAI API key for descriptions

## Deployment

### Hugging Face Spaces

This application is designed to work with Hugging Face Spaces. The `requirements.txt` file and Flask structure are compatible with the platform.

### Other Python Hosting Platforms

The application can be deployed to any Python-compatible hosting platform:

- **Heroku**: Use the included `requirements.txt`
- **Railway**: Compatible with the current structure
- **Render**: Works with Flask applications
- **PythonAnywhere**: Standard Flask deployment

## API Endpoints

- `GET /`: Main application interface
- `POST /upload`: Upload menu image for processing
- `GET /health`: Health check endpoint

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## Alternatives
[MenuGuide](https://menuguide.app/#download)

## License

This project is licensed under the MIT License - see the LICENSE file for details.