# 🍽️ AI Menu Analyzer

Transform menu photos into rich, visual dining guides using AI vision models in about 20s! Upload a photo of a restaurant menu and get detailed information about each dish including images and AI-generated descriptions. Try out at: https://huggingface.co/spaces/rafgger/MenuReader

<a href="https://www.youtube.com/watch?v=N-Atq0eP7lU" target="_blank">
  <img src="https://github.com/user-attachments/assets/ba95792c-5a6d-4a56-83cc-2794b5f5218f" alt="Menu Reader video" width="500"/>
</a>


## ✨ Features

- **AI-Powered Menu Analysis**: Uses GPT-4o and Gemini Pro Vision for direct dish extraction
- **Visual Food Discovery**: Automatically finds relevant food images for each dish
- **Smart Descriptions**: AI-generated detailed descriptions with ingredients and dietary info
- **Multi-Language Support**: Works with menus in multiple languages
- **No OCR Required**: Direct AI vision analysis for better accuracy

## 🚀 Live Demo

Try it now: [AI Menu Analyzer on Hugging Face Spaces](https://huggingface.co/spaces/your-username/ai-menu-analyzer)

## 🛠️ Technology Stack

- **Frontend**: Gradio for interactive web interface
- **AI Models**: OpenAI GPT-4o, Google Gemini Pro Vision via OpenRouter
- **Image Search**: Google Custom Search API
- **Descriptions**: OpenAI GPT-3.5/4 for detailed dish descriptions
- **Backend**: Python with Pydantic for type safety

## 📋 Requirements

- Python 3.9+
- API Keys:
  - OpenRouter API key (for AI vision models)
  - Google Custom Search API key + Engine ID
  - OpenAI API key (for descriptions)

## 🔧 Local Development

1. Clone the repository:
```bash
git clone <your-repo-url>
cd ai-menu-analyzer
```

2. Install dependencies:
```bash
uv sync
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. Run the application:
```bash
python app.py
```

## 🌐 Deployment

### Hugging Face Spaces

This app is designed for easy deployment on Hugging Face Spaces:

1. Create a new Space on Hugging Face
2. Upload the code
3. Set environment variables in Space settings
4. The app will automatically deploy

### Environment Variables

Set these in your Hugging Face Space settings:

- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `GOOGLE_SEARCH_API_KEY`: Google Custom Search API key
- `GOOGLE_SEARCH_ENGINE_ID`: Google Custom Search Engine ID
- `OPENAI_API_KEY`: OpenAI API key for descriptions

## 📁 Project Structure

```
├── app/                    # Core application modules
│   ├── models/            # Data models and schemas
│   ├── services/          # Business logic services
│   └── config.py          # Configuration management
├── examples/              # Example images and usage
├── app.py                 # Main Gradio application
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🔄 CI/CD Pipeline

The project includes GitHub Actions for:
- Automated testing
- Code quality checks
- Automatic deployment to Hugging Face Spaces

## 📝 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For issues and questions, please open an issue on GitHub.
