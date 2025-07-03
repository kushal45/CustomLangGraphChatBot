# Real Parameter Testing Framework

This document describes the enhanced testing framework that supports real parameter testing instead of just mocked responses. This allows you to test tools with actual data sources like real GitHub repositories, files, and API endpoints.

## Overview

The testing framework now supports two modes:
1. **Mock Testing** (default): Uses predefined test data and mocked responses
2. **Real Parameter Testing**: Uses actual parameters to make real API calls and fetch real data

## Features

### Real Parameter Support
- **GitHub Tools**: Test with actual GitHub repositories and files
- **File System Tools**: Test with real file paths and directories
- **API Integration**: Make actual API calls instead of using mocked responses
- **Data Validation**: Verify tools work with real-world data structures

### Enhanced Debugging
- **VSCode Integration**: Debug configurations for real parameter testing
- **Detailed Reporting**: Shows actual data retrieved from real sources
- **Performance Metrics**: Measure real API response times
- **Error Handling**: Better error reporting for real-world scenarios

## Usage

### Command Line Interface

#### Basic Real Parameter Testing
```bash
# Test GitHub tools with real repository
python tests/test_module_sanity.py --real-params --github-repo https://github.com/kushal45/CustomLangGraphChatBot --test-file tools/registry.py

# Test specific category with real parameters
python tests/test_module_sanity.py --category github --real-params --github-repo https://github.com/octocat/Hello-World
```

#### Integration Runner with Real Parameters
```bash
# Run sanity checks with real parameters
python tools_integration_runner.py --sanity-check --real-world-test --github-repo https://github.com/kushal45/CustomLangGraphChatBot --test-file README.md

# Run specific category tests with real parameters
python tools_integration_runner.py --category github --real-world-test --github-repo https://github.com/octocat/Hello-World

# Run health checks with real parameters
python tools_integration_runner.py --health-check --real-world-test --github-repo https://github.com/kushal45/CustomLangGraphChatBot
```

### Python API

#### Direct Function Calls
```python
from tests.test_module_sanity import run_sanity_checks

# Test with real parameters
real_params = {
    "github_repo": "https://github.com/kushal45/CustomLangGraphChatBot",
    "test_file": "tools/registry.py"
}

results = run_sanity_checks(
    verbose=True,
    category="github",
    use_real_params=True,
    real_params=real_params
)
```

#### Integration Runner API
```python
from tools_integration_runner import ToolIntegrationRunner

# Create runner with real parameters
real_params = {
    "github_repo": "https://github.com/octocat/Hello-World",
    "test_file": "README.md"
}

runner = ToolIntegrationRunner(
    verbose=True,
    use_real_params=True,
    real_params=real_params
)

# Run tests
results = runner.run_sanity_checks(category="github")
```

## VSCode Debug Configurations

The framework includes enhanced VSCode debug configurations for real parameter testing:

### Available Configurations
1. **Debug Tool Integration Runner - Real Parameters**: Test integration runner with real GitHub data
2. **Debug Tool Sanity Checker - Real Parameters**: Test sanity checker with real parameters
3. **Debug Tool Health Checker - Real Parameters**: Test health checker with real data

### Input Variables
- `realGithubRepo`: GitHub repository URL for testing
- `realTestFile`: File path within the repository for testing
- `toolCategory`: Category of tools to test
- `specificTool`: Specific tool to test

## Environment Setup

### Required Environment Variables
```bash
# GitHub API access (required for GitHub tools)
export GITHUB_TOKEN="your_github_token_here"

# AI API keys (optional, for AI tools)
export XAI_API_KEY="your_xai_key_here"
export OPENAI_API_KEY="your_openai_key_here"

# Communication tools (optional)
export SLACK_WEBHOOK_URL="your_slack_webhook_here"
```

### GitHub Token Setup
1. Go to GitHub Settings > Developer settings > Personal access tokens
2. Generate a new token with appropriate permissions
3. Set the `GITHUB_TOKEN` environment variable

## Real Parameter Examples

### GitHub Repository Testing
```bash
# Test with public repository
python tools_integration_runner.py --category github --real-world-test --github-repo https://github.com/octocat/Hello-World --test-file README.md

# Test with your own repository
python tools_integration_runner.py --category github --real-world-test --github-repo https://github.com/kushal45/CustomLangGraphChatBot --test-file tools/registry.py
```

### File System Testing
```bash
# Test with real file paths
python tests/test_module_sanity.py --category filesystem --real-params --test-file /path/to/real/file.py
```

## Output Examples

### Mock Testing Output
```
🐙 Checking GitHub Tools...
   Testing github_repository...
   ✅ github_repository: PASS - Tool configured and ready for GitHub operations
```

### Real Parameter Testing Output
```
🐙 Checking GitHub Tools...
   🌐 Testing with real repository: https://github.com/kushal45/CustomLangGraphChatBot
   Testing github_repository...
      🌐 Testing with real repository: https://github.com/kushal45/CustomLangGraphChatBot
   ✅ github_repository: PASS - Successfully retrieved repository info for https://github.com/kushal45/CustomLangGraphChatBot (Real Test)
      Data retrieved:
         repo_name: CustomLangGraphChatBot
         description: Custom LangGraph ChatBot implementation...
         stars: 5
         language: Python
         files_found: 15
```

## Demo Script

Run the demo script to see real parameter testing in action:

```bash
python test_real_params_demo.py
```

This script demonstrates:
- Basic sanity checking with real parameters
- Integration runner with real parameters
- Comparison between mock and real testing

## Benefits

### Real-World Validation
- Tests work with actual data structures and API responses
- Validates error handling with real error conditions
- Ensures tools work with various repository sizes and structures

### Better Debugging
- See actual data being processed
- Identify real-world edge cases
- Performance testing with actual API latency

### Confidence in Deployment
- Tools tested with real data before workflow integration
- Reduced surprises in production environments
- Better understanding of tool capabilities and limitations

## Best Practices

### Security
- Never commit API tokens to version control
- Use environment variables for sensitive data
- Test with public repositories when possible

### Rate Limiting
- Be mindful of API rate limits when testing
- Use different repositories for testing to avoid hitting limits
- Consider using test repositories for frequent testing

### Error Handling
- Test with both valid and invalid parameters
- Verify error messages are helpful
- Ensure graceful degradation when APIs are unavailable

## Troubleshooting

### Common Issues
1. **GitHub API Rate Limiting**: Use different repositories or wait for rate limit reset
2. **Missing Environment Variables**: Ensure all required tokens are set
3. **Network Issues**: Check internet connectivity and API endpoint availability
4. **Repository Access**: Ensure the GitHub token has access to private repositories if needed

### Debug Tips
- Use verbose mode (`-v` or `--verbose`) for detailed output
- Check the VSCode debug console for additional information
- Review the actual API responses in the test output
- Verify environment variables are properly set

## Future Enhancements

- Support for more tool categories (AI, communication, etc.)
- Batch testing with multiple repositories
- Performance benchmarking with real data
- Integration with CI/CD pipelines for real-world testing
