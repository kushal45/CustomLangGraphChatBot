# Free AI Providers Setup Guide

This guide helps you set up free AI API alternatives to replace GROK in the CustomLangGraphChatBot project.

## 🆓 Recommended Free AI Providers

### 1. **Groq** (Recommended - Fast & Free)
- **Website**: https://console.groq.com/
- **Free Tier**: 14,400 requests/day, very fast inference
- **Models**: Llama 3, Mixtral, Gemma
- **Setup**:
  ```bash
  # 1. Sign up at https://console.groq.com/
  # 2. Get your API key from the dashboard
  # 3. Add to .env file:
  GROQ_API_KEY=your_groq_api_key_here
  AI_PROVIDER=groq
  ```

### 2. **Hugging Face Inference API** (Good Free Tier)
- **Website**: https://huggingface.co/inference-api
- **Free Tier**: 1,000 requests/month
- **Models**: Thousands of open-source models
- **Setup**:
  ```bash
  # 1. Sign up at https://huggingface.co/
  # 2. Get your API token from https://huggingface.co/settings/tokens
  # 3. Add to .env file:
  HUGGINGFACE_API_KEY=your_huggingface_token_here
  AI_PROVIDER=huggingface
  ```

### 3. **Together AI** (Free Tier Available)
- **Website**: https://api.together.xyz/
- **Free Tier**: $25 free credits
- **Models**: Llama, Mistral, CodeLlama
- **Setup**:
  ```bash
  # 1. Sign up at https://api.together.xyz/
  # 2. Get your API key from the dashboard
  # 3. Add to .env file:
  TOGETHER_API_KEY=your_together_api_key_here
  AI_PROVIDER=together
  ```

### 4. **Google AI Studio (Gemini)** (Free Tier)
- **Website**: https://aistudio.google.com/
- **Free Tier**: 15 requests/minute, 1,500 requests/day
- **Models**: Gemini Pro, Gemini Pro Vision
- **Setup**:
  ```bash
  # 1. Sign up at https://aistudio.google.com/
  # 2. Get your API key
  # 3. Add to .env file:
  GOOGLE_API_KEY=your_google_api_key_here
  AI_PROVIDER=google
  ```

### 5. **Ollama** (Completely Free - Local)
- **Website**: https://ollama.ai/
- **Free**: Completely free, runs locally
- **Models**: Llama 2, Code Llama, Mistral, and more
- **Setup**:
  ```bash
  # 1. Install Ollama: https://ollama.ai/download
  # 2. Pull a model: ollama pull llama2
  # 3. Start Ollama server: ollama serve
  # 4. Add to .env file:
  AI_PROVIDER=ollama
  OLLAMA_BASE_URL=http://localhost:11434/v1
  ```

### 6. **OpenRouter** (Free Tier)
- **Website**: https://openrouter.ai/
- **Free Tier**: $1 free credits monthly
- **Models**: Access to multiple providers
- **Setup**:
  ```bash
  # 1. Sign up at https://openrouter.ai/
  # 2. Get your API key
  # 3. Add to .env file:
  OPENROUTER_API_KEY=your_openrouter_api_key_here
  AI_PROVIDER=openrouter
  ```

## 🚀 Quick Setup Instructions

### Step 1: Choose Your Provider
Pick one of the free providers above. **Groq is recommended** for best performance and generous free tier.

### Step 2: Install Dependencies
```bash
# Install additional dependencies for your chosen provider
pip install groq  # For Groq
# OR
pip install transformers  # For Hugging Face
# OR
pip install together  # For Together AI
# OR
pip install google-generativeai  # For Google Gemini
```

### Step 3: Configure Environment
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your chosen provider's API key
# Set AI_PROVIDER to your chosen provider
```

### Step 4: Test Your Setup
```bash
# Run the validation script
python validate_setup.py

# Or test with the test runner
python test_runner.py
```

## 🔧 Configuration Options

### Environment Variables
```bash
# Primary configuration
AI_PROVIDER=groq  # Choose: groq, huggingface, together, google, ollama, openrouter

# Provider-specific API keys (set only the one you're using)
GROQ_API_KEY=your_key_here
HUGGINGFACE_API_KEY=your_key_here
TOGETHER_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here

# Local Ollama (no API key needed)
OLLAMA_BASE_URL=http://localhost:11434/v1
```

### Programmatic Configuration
```python
from tools.ai_analysis_tools import AIConfig, AIProvider

# Configure specific provider
config = AIConfig(
    provider=AIProvider.GROQ,
    model_name="llama3-8b-8192",
    temperature=0.1,
    max_tokens=2000
)
```

## 📊 Provider Comparison

| Provider | Free Tier | Speed | Model Quality | Setup Difficulty |
|----------|-----------|-------|---------------|------------------|
| Groq | 14,400/day | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Hugging Face | 1,000/month | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Together AI | $25 credits | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Google Gemini | 1,500/day | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Ollama | Unlimited | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| OpenRouter | $1/month | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

## 🔍 Troubleshooting

### Common Issues

1. **"No API key found" error**
   - Make sure you've set the correct environment variable
   - Check that your .env file is in the project root
   - Verify the API key is valid

2. **"Provider not supported" error**
   - Check that AI_PROVIDER is set to a valid value
   - Ensure you've installed the required dependencies

3. **Rate limit errors**
   - Switch to a different provider
   - Implement request throttling
   - Consider upgrading to a paid tier

4. **Ollama connection errors**
   - Make sure Ollama is running: `ollama serve`
   - Check that the model is downloaded: `ollama pull llama2`
   - Verify the OLLAMA_BASE_URL is correct

### Getting Help
- Check the project's GitHub issues
- Review the provider's documentation
- Test with the validation script: `python validate_setup.py`

## 🎯 Best Practices

1. **Start with Groq** - Best free tier and performance
2. **Have a backup** - Configure multiple providers
3. **Monitor usage** - Keep track of your API limits
4. **Use appropriate models** - Smaller models for simple tasks
5. **Cache responses** - Avoid redundant API calls

## 🔄 Migration from GROK

The system automatically detects available providers and falls back gracefully. Your existing code will work without changes once you configure a new provider.

```python
# Old GROK code still works
from tools.ai_analysis_tools import CodeReviewTool

tool = CodeReviewTool()  # Now uses configured provider
result = tool.run('{"code": "def hello(): pass", "language": "python"}')
```
