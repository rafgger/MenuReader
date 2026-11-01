---
title: AI Menu Analyzer
emoji: 🍽️
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: "6.3.0"
python_version: "3.11"
app_file: app.py
pinned: false
---

# 🍽️ AI Menu Analyzer

Transform menu photos into rich, visual dining guides using AI vision models! Upload a photo of a restaurant menu and get detailed information about each dish including images and AI-generated descriptions.

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

### Test on your phone over local Wi-Fi (Windows)

Connect your phone and computer to the same Wi-Fi. After completing the setup
above, run these commands in PowerShell from the project directory:

```powershell
$env:GRADIO_SERVER_NAME = '0.0.0.0'
$env:GRADIO_SERVER_PORT = '7860'
$env:GRADIO_SHARE = 'false'
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe -u app.py
```

`0.0.0.0` makes Gradio listen on all network interfaces, including Wi-Fi, instead
of only localhost. Port `7860` is the app's HTTP port. `GRADIO_SHARE=false` keeps
Gradio's public sharing tunnel disabled; no router port forwarding is needed.

Find the computer's Wi-Fi IPv4 address in another PowerShell window:

```powershell
ipconfig
```

On your phone, open `http://<Wi-Fi IPv4 address>:7860`. For example, the address
during our local test was **http://10.0.0.36:7860**. Your computer's address may
change when it reconnects to the network. Use the actual address on the phone,
not `localhost` or `0.0.0.0`.

Keep the computer awake and the server running. Press `Ctrl+C` in the server
terminal to stop it. If the phone cannot connect, check that both devices use the
same Wi-Fi, that the network allows devices to communicate (guest Wi-Fi may not),
and that Windows Firewall allows Python on your private network.

You can check that the app responds from the computer with:

```powershell
(Invoke-WebRequest -Uri 'http://10.0.0.36:7860' -UseBasicParsing).StatusCode
```

Replace the address as needed; a successful response returns `200`. This checks
the server's response, but the phone still needs network access to the computer.

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
