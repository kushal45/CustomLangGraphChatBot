# CustomLangGraphChatBot

A modular, extensible chatbot for automated code review of GitHub repositories, built using [LangGraph](https://github.com/langchain-ai/langgraph). This project is designed to analyze code, generate review reports, and handle workflow logic for code review automation, especially for MCP server repositories.

## Features
- **Automated code review**: Analyze code from GitHub repositories and generate review reports.
- **Workflow orchestration**: Uses LangGraph to manage review steps, error handling, and branching logic.
- **Extensible nodes**: Each workflow step is a modular async function, making it easy to add or modify logic.
- **Ready for API integration**: Easily connect to FastAPI or other frameworks for chatbot or web API interfaces.

## Project Structure
```
CustomLangGraphChatBot/
│
├── tools/                          # External tools ecosystem
│   ├── __init__.py                 # Tools package initialization
│   ├── registry.py                 # Central tool registry and management
│   ├── ai_analysis_tools.py        # AI-powered analysis tools (Grok integration)
│   ├── analysis_tools.py           # Static code analysis tools
│   ├── github_tools.py             # GitHub API integration tools
│   ├── filesystem_tools.py         # File system operation tools
│   └── communication_tools.py      # Slack, email, Jira integration tools
│
├── tests/                          # Comprehensive test suite
│   └── test_tools_integration.py   # Integration tests for all tools
│
├── state.py                        # Workflow state model (ReviewState)
├── nodes.py                        # Async node functions for workflow steps
├── workflow.py                     # LangGraph workflow builder and logic
├── api.py                          # FastAPI backend for web integration
├── requirements.txt                # Python dependencies
├── test_runner.py                  # Comprehensive test runner
├── validate_setup.py               # Setup validation script
├── TESTING.md                      # Complete testing guide
├── TESTING_ARCHITECTURE.md        # Detailed testing architecture documentation
├── .env.example                    # Environment variables template
├── Dockerfile                      # Docker configuration
├── frontend.html                   # Web frontend interface
└── README.md                       # Project documentation
```

### Core Components
- **tools/**: Complete external tools ecosystem with 25+ specialized tools
- **state.py**: Workflow state management with comprehensive data models
- **nodes.py**: Modular async workflow nodes for each operation
- **workflow.py**: Advanced LangGraph workflows with conditional logic
- **api.py**: RESTful API backend with FastAPI integration
- **tests/**: Comprehensive testing infrastructure with validation scripts

## Setup Requirements

### Prerequisites
- **Python 3.9+** (tested with Python 3.12.8)
- **Git** for repository management
- **Internet connection** for API integrations

### Required API Keys
To use all features, you'll need the following API keys:

#### 🔑 **Required for Core Functionality**
- **GitHub Personal Access Token**: For repository analysis and GitHub integration
  - Get from: https://github.com/settings/tokens
  - Permissions needed: `repo`, `read:org`, `read:user`

- **AI Provider API Key**: For AI-powered code analysis (Multiple FREE options available)
  - **Recommended FREE options**:
    - **Groq**: https://console.groq.com/ (14,400 requests/day, very fast)
    - **Hugging Face**: https://huggingface.co/settings/tokens (1,000 requests/month)
    - **Google Gemini**: https://aistudio.google.com/ (1,500 requests/day)
    - **Ollama**: https://ollama.ai/ (Completely free, runs locally)
  - **See [AI_PROVIDERS_SETUP.md](AI_PROVIDERS_SETUP.md) for detailed setup instructions**
  - Used for: Code review, documentation generation, refactoring suggestions, test generation

#### 📢 **Optional for Notifications**
- **Slack Webhook URL**: For Slack notifications
- **Email Credentials**: For email notifications
- **Jira Credentials**: For Jira integration

### Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/kushal45/CustomLangGraphChatBot.git
cd CustomLangGraphChatBot
```

#### 2. Install Dependencies
```bash
# Install core dependencies
pip install -r requirements.txt

# For development and testing (optional)
pip install -r requirements-test.txt
```

#### 3. Configure Environment Variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your preferred editor
```

#### 4. Required Environment Variables
Add the following to your `.env` file:

```bash
# GitHub Integration (Required)
GITHUB_TOKEN=your_github_personal_access_token_here

# AI Provider Configuration (Required - Choose one)
AI_PROVIDER=groq  # Recommended: groq, huggingface, google, ollama

# FREE AI Provider Options (set one of these):
GROQ_API_KEY=your_groq_api_key_here                    # Recommended - Fast & generous free tier
HUGGINGFACE_API_KEY=your_huggingface_api_key_here      # Good free tier
GOOGLE_API_KEY=your_google_api_key_here                # Google Gemini free tier
# OLLAMA_BASE_URL=http://localhost:11434/v1            # Local Ollama (no API key needed)

# Legacy/Paid Options:
# XAI_API_KEY=your_xai_api_key_here                    # Grok (X.AI) - PAID
# OPENAI_API_KEY=your_openai_api_key_here              # OpenAI - PAID

# Optional: Communication integrations
SLACK_WEBHOOK_URL=your_slack_webhook_url_here
EMAIL_USERNAME=your_email_username_here
EMAIL_PASSWORD=your_email_password_here
JIRA_URL=your_jira_instance_url_here
JIRA_USERNAME=your_jira_username_here
JIRA_API_TOKEN=your_jira_api_token_here
```

#### 5. Install Optional Analysis Tools
For enhanced static code analysis:
```bash
# Install static analysis tools
pip install pylint flake8 bandit

# Verify installation
pylint --version
flake8 --version
bandit --version
```

#### 6. Validate Setup
Run the setup validation script:
```bash
python3 validate_setup.py
```

This will check:
- ✅ File structure integrity
- ✅ Python version compatibility
- ✅ Required dependencies
- ✅ Environment variable configuration
- ✅ Tool file syntax validation

#### 7. Run Tests
Test the installation:
```bash
# Run all tests
python3 test_runner.py

# Run specific tool category tests
python3 test_runner.py filesystem    # File system tools
python3 test_runner.py analysis      # Static analysis tools
python3 test_runner.py ai           # AI analysis tools (requires XAI_API_KEY)
python3 test_runner.py github       # GitHub tools (requires GITHUB_TOKEN)

# Run comprehensive test suite with pytest
pytest tests/ -v                    # All tests with verbose output
pytest tests/test_workflow_integration.py -v  # Integration tests
pytest tests/test_performance.py -v # Performance tests
pytest tests/test_error_handling.py -v       # Error handling tests
pytest tests/test_api_integration.py -v      # API tests

# Run with coverage reporting
pytest --cov=src --cov=tools tests/ --cov-report=html --cov-report=term
```

## Usage

### 🚀 Quick Start

#### 1. Basic Code Analysis
```python
from tools.registry import ToolRegistry

# Initialize tool registry
registry = ToolRegistry()

# Analyze a Python file
complexity_tool = registry.get_tool("code_complexity")
result = complexity_tool._run("path/to/your/file.py")
print(f"Complexity analysis: {result}")
```

#### 2. AI-Powered Code Review
```python
import json
from tools.registry import ToolRegistry

registry = ToolRegistry()
review_tool = registry.get_tool("ai_code_review")

# Review code with Grok AI
code_to_review = """
def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
"""

result = review_tool._run(json.dumps({
    "code": code_to_review,
    "language": "Python",
    "context": "Fibonacci calculation function"
}))

print(f"AI Review: {result}")
```

#### 3. GitHub Repository Analysis
```python
from tools.registry import ToolRegistry

registry = ToolRegistry()
github_tool = registry.get_tool("github_repo_info")

# Analyze a GitHub repository
result = github_tool._run("owner/repository-name")
print(f"Repository info: {result}")
```

### 🔧 Advanced Usage

#### Custom Workflow Integration
```python
from workflow import create_workflow
from state import ReviewState

# Create a custom workflow
workflow = create_workflow()

# Execute workflow with initial state
initial_state = ReviewState(
    repository_url="https://github.com/owner/repo",
    analysis_type="comprehensive",
    tools_to_use=["ai_code_review", "code_complexity", "security_analysis"]
)

result = workflow.invoke(initial_state)
```

#### API Integration
Start the FastAPI server:
```bash
python3 api.py
```

Then access the API at `http://localhost:8000`:
- **POST /analyze**: Analyze code or repositories
- **GET /tools**: List available tools
- **POST /workflow**: Execute custom workflows

### 📊 Available Tools

The system includes 25+ specialized tools organized in categories:

#### 🤖 AI Analysis Tools (4 tools)
- `ai_code_review`: Comprehensive code review using Grok
- `ai_documentation_generator`: Generate documentation and docstrings
- `ai_refactoring_suggestions`: AI-driven refactoring recommendations
- `ai_test_generator`: Automated unit test generation

#### 🔍 Static Analysis Tools (4 tools)
- `code_complexity`: Cyclomatic complexity analysis
- `security_analysis`: Security vulnerability detection
- `code_quality`: Style and quality checks
- `performance_analysis`: Performance profiling

#### 🐙 GitHub Integration Tools (3 tools)
- `github_repo_info`: Repository information and metadata
- `github_file_reader`: Read and analyze repository files
- `github_pr_analysis`: Pull request analysis and review

#### 📁 File System Tools (6 tools)
- `file_reader`: Read and process files
- `directory_analyzer`: Analyze directory structures
- `file_writer`: Write and modify files
- `code_search`: Search code patterns and symbols
- `project_structure`: Analyze project organization
- `dependency_analyzer`: Analyze project dependencies

#### 📢 Communication Tools (8 tools)
- `slack_notifier`: Send Slack notifications
- `email_sender`: Send email reports
- `jira_ticket_creator`: Create Jira tickets
- `report_generator`: Generate comprehensive reports
- And more...

## 🐳 Docker Setup

You can run the FastAPI backend in a Docker container for consistency and easy deployment.

### Build the Docker Image
```bash
docker build -t custom-langgraph-chatbot .
```

### Run the Docker Container
```bash
# Run with environment variables
docker run -p 8000:8000 \
  -e GITHUB_TOKEN=your_token_here \
  -e XAI_API_KEY=your_key_here \
  custom-langgraph-chatbot

# Or run with .env file
docker run -p 8000:8000 --env-file .env custom-langgraph-chatbot
```

The API will be available at http://localhost:8000

### Accessing the Frontend
- Open `frontend.html` in your browser
- The frontend connects to the API at `http://localhost:8000`
- Use the web interface for interactive code analysis

## 🔧 Troubleshooting

### Common Issues

#### 1. **Missing Dependencies**
```bash
# Error: ModuleNotFoundError
pip install -r requirements.txt

# For static analysis tools
pip install pylint flake8 bandit
```

#### 2. **API Key Issues**
```bash
# Error: Grok (X.AI) API key not configured
# Solution: Set the XAI_API_KEY environment variable
export XAI_API_KEY=your_key_here

# Or add to .env file
echo "XAI_API_KEY=your_key_here" >> .env
```

#### 3. **GitHub Rate Limiting**
```bash
# Error: GitHub API rate limit exceeded
# Solution: Use authenticated requests with GITHUB_TOKEN
export GITHUB_TOKEN=your_token_here
```

#### 4. **Tool Import Errors**
```bash
# Validate setup
python3 validate_setup.py

# Check specific tool
python3 -c "from tools.registry import ToolRegistry; print('Tools loaded successfully')"
```

### Getting Help

1. **Run Validation**: `python3 validate_setup.py`
2. **Check Logs**: Review error messages in terminal output
3. **Test Components**: Use `python3 test_runner.py [category]` to test specific components
4. **Review Documentation**: Check `TESTING.md` for detailed testing guide

## 🧪 Comprehensive Testing

The project includes extensive test coverage across all components with 10+ test files covering different aspects:

> 📋 **For detailed testing architecture, flow diagrams, and contributor guidelines, see [TESTING_ARCHITECTURE.md](TESTING_ARCHITECTURE.md)**

### Test Structure
```
tests/
├── test_ai_analysis_tools.py      # AI tools with Grok API mocking
├── test_static_analysis_tools.py  # Static analysis tools (Pylint, Flake8, Bandit)
├── test_github_tools.py           # GitHub API integration tests
├── test_filesystem_tools.py       # File system operation tests
├── test_communication_tools.py    # Slack, Email, Webhook, Jira tests
├── test_registry.py               # Tool registry and configuration tests
├── test_workflow_integration.py   # End-to-end workflow tests
├── test_performance.py            # Performance and load tests
├── test_error_handling.py         # Error scenarios and edge cases
├── test_api_integration.py        # FastAPI endpoint tests
└── conftest.py                    # Shared pytest fixtures
```

### Test Categories

#### 1. **Unit Tests** (300+ test cases)
- Individual tool functionality testing
- Input validation and error handling
- Mock external dependencies (APIs, subprocess calls)
- Configuration and parameter validation

#### 2. **Integration Tests** (50+ test cases)
- End-to-end workflow execution
- State management and data flow
- Tool interaction and coordination
- LangGraph workflow integration

#### 3. **Performance Tests** (25+ test cases)
- Tool execution timing benchmarks
- Memory usage monitoring
- Concurrent operation testing
- Large repository handling

#### 4. **Error Handling Tests** (100+ test cases)
- Network failure scenarios
- Invalid input handling
- File system edge cases
- API rate limiting and timeouts

#### 5. **API Tests** (40+ test cases)
- FastAPI endpoint validation
- Request/response format testing
- Authentication and security
- CORS and error handling

### Running Tests

#### Prerequisites
```bash
# Install test dependencies (if not already installed)
pip install -r requirements-test.txt
```

#### Quick Test Commands
```bash
# Run all tests (recommended)
pytest tests/ -v

# Run specific test categories
pytest tests/test_ai_analysis_tools.py -v      # AI tools
pytest tests/test_workflow_integration.py -v  # Integration
pytest tests/test_performance.py -v           # Performance
pytest tests/test_error_handling.py -v        # Error handling
pytest tests/test_api_integration.py -v       # API tests

# Run tests by markers
pytest tests/ -m "unit" -v          # Unit tests only
pytest tests/ -m "integration" -v   # Integration tests only
pytest tests/ -m "performance" -v   # Performance tests only
```

#### Advanced Testing
```bash
# Run with coverage reporting
pytest --cov=src --cov=tools tests/ --cov-report=html --cov-report=term

# Run tests in parallel (faster)
pytest tests/ -n auto  # Requires: pip install pytest-xdist

# Run with detailed output
pytest tests/ -v -s --tb=long

# Run performance tests with timing
pytest tests/test_performance.py -v -s --durations=10
```

### Test Coverage Metrics
- **Overall Coverage**: >90%
- **Critical Components**: >95%
- **Tool Coverage**: 100% (all 25+ tools tested)
- **API Coverage**: >95%
- **Error Handling**: >90%
- **Integration Paths**: >85%

### Performance Tips

- **Use GitHub Token**: Authenticated requests have higher rate limits
- **Cache Results**: The system caches analysis results for better performance
- **Batch Operations**: Process multiple files together when possible
- **Monitor Usage**: Keep track of API usage for Grok and GitHub

## 🤝 Contributing

We welcome contributions! This project is designed to be extensible and community-driven.

### Getting Started with Development

1. **Fork and Clone**
   ```bash
   git fork https://github.com/kushal45/CustomLangGraphChatBot.git
   git clone https://github.com/your-username/CustomLangGraphChatBot.git
   cd CustomLangGraphChatBot
   ```

2. **Set Up Development Environment**
   ```bash
   pip install -r requirements.txt
   cp .env.example .env
   # Add your API keys to .env
   ```

3. **Validate Setup**
   ```bash
   python3 validate_setup.py
   python3 test_runner.py
   ```

4. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

### 🛠️ Development Areas

#### **Add New Tools**
Create new tools in the appropriate category:
```python
# Example: tools/my_new_tools.py
from langchain.tools import BaseTool
from typing import Dict, Any

class MyCustomTool(BaseTool):
    name: str = "my_custom_tool"
    description: str = "Description of what this tool does"

    def _run(self, query: str) -> Dict[str, Any]:
        # Implement your tool logic
        return {"result": "success"}
```

#### **Extend AI Analysis**
- Add new AI-powered analysis capabilities
- Improve prompt engineering for better results
- Add support for additional programming languages
- Enhance error handling and response parsing

#### **Improve Workflows**
- Add new LangGraph workflow patterns
- Implement conditional logic for complex scenarios
- Add workflow state persistence
- Create workflow templates for common use cases

#### **Enhance Integrations**
- Add new communication platforms (Discord, Teams, etc.)
- Integrate with additional code hosting platforms (GitLab, Bitbucket)
- Add support for more project management tools
- Implement webhook integrations

### 📋 Contribution Guidelines

1. **Code Quality**
   - Follow Python PEP 8 style guidelines
   - Add type hints to all functions
   - Include comprehensive docstrings
   - Write unit tests for new functionality

2. **Testing**
   - Run `python3 test_runner.py` before submitting
   - Add tests for new tools and features
   - Ensure all existing tests pass
   - Test with different Python versions if possible

3. **Documentation**
   - Update README.md for new features
   - Add examples for new tools
   - Update TESTING.md for new test procedures
   - Follow testing architecture guidelines in [TESTING_ARCHITECTURE.md](TESTING_ARCHITECTURE.md)
   - Include inline code documentation

4. **Pull Request Process**
   - Create descriptive PR titles and descriptions
   - Reference related issues
   - Include screenshots for UI changes
   - Request review from maintainers

### 🎯 Priority Areas for Contributors

- **Multi-language Support**: Add support for more programming languages
- **Advanced AI Features**: Implement more sophisticated AI analysis
- **Performance Optimization**: Improve tool execution speed and efficiency
- **UI/UX Improvements**: Enhance the web frontend interface
- **Integration Expansion**: Add more third-party service integrations
- **Documentation**: Improve guides, tutorials, and API documentation

## 📈 Roadmap

### Upcoming Features
- **Multi-Repository Analysis**: Analyze multiple repositories simultaneously
- **Custom Rule Engine**: Define custom analysis rules and patterns
- **Advanced Reporting**: Generate detailed PDF and HTML reports
- **Real-time Collaboration**: Live collaboration features for team reviews
- **Plugin System**: Extensible plugin architecture for custom tools
- **Machine Learning**: ML-based code quality prediction and recommendations

### Version History
- **v1.0.0**: Initial release with basic workflow
- **v2.0.0**: Added comprehensive external tools ecosystem
- **v2.1.0**: Migrated from OpenAI to Grok for free AI analysis
- **v2.2.0**: Enhanced testing infrastructure and validation
- **v2.3.0**: Complete debugging infrastructure with VSCode integration

## 🔧 **Debugging & Development**

### **VSCode Debugging Guide**
For external contributors and developers, we provide a comprehensive debugging infrastructure:

📖 **[Complete VSCode Debugging Guide](VSCODE_DEBUGGING_GUIDE.md)**

**🎯 What's Included:**
- **21 debugging configurations** covering every scenario
- **Visual flow diagrams** for understanding debugging paths
- **Step-by-step examples** for common debugging tasks
- **Comprehensive troubleshooting** guide with solutions
- **Performance optimization** tips and best practices

**🚀 Quick Start:**
```bash
# 1. Open VSCode in project root
# 2. Press F5 or go to Run and Debug (Ctrl+Shift+D)
# 3. Select from 21 debugging configurations:

🚀 Main Application Issues     → Main Application Debugging
🔧 Individual Node Problems   → Node Debugging Tools
🔍 State/Data Issues          → State Inspection Tools
📊 Performance Problems       → Advanced Debugging Tools
🧪 Test Failures             → Testing & Workflow Debugging
🌐 API/Integration Issues     → API & Webhook Debugging
🔄 End-to-End Workflow Issues → Workflow Execution Debugging
```

**🔧 Available Debugging Tools:**
- **Node-level debugging** with tracing and profiling
- **State inspection and comparison** tools
- **Interactive debugging** sessions
- **Performance profiling** and bottleneck analysis
- **Complete test suite** debugging support
- **API and webhook** debugging capabilities
- **End-to-end workflow** debugging with error scenarios

### **Development Workflow**
1. **Setup**: Follow setup requirements above
2. **Debug**: Use appropriate VSCode debugging configuration
3. **Test**: Run comprehensive test suite
4. **Validate**: Use validation scripts
5. **Contribute**: Submit PRs with proper testing

## 🏆 Acknowledgments

- **LangGraph Team**: For the excellent workflow orchestration framework
- **LangChain Community**: For the comprehensive AI integration tools
- **Grok (X.AI)**: For providing free AI model access
- **GitHub**: For the robust API and platform
- **Open Source Community**: For inspiration and contributions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Contact & Support

### Getting Help
- **Issues**: [GitHub Issues](https://github.com/kushal45/CustomLangGraphChatBot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kushal45/CustomLangGraphChatBot/discussions)
- **Documentation**:
  - `TESTING.md` - Comprehensive testing guide
  - `VSCODE_DEBUGGING_GUIDE.md` - Complete debugging manual
  - `TESTING_ARCHITECTURE.md` - Testing framework documentation

### Maintainers
- **Kushal Bhattacharya** ([@kushal45](https://github.com/kushal45))
  - Email: bhattacharya.kushal4@gmail.com

### Community
- Star ⭐ this repository if you find it useful
- Fork 🍴 and contribute to make it better
- Share 📢 with others who might benefit

---

**Made with ❤️ by the CustomLangGraphChatBot community**

*Empowering developers with AI-powered code analysis and review automation*