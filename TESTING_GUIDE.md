# Modular Testing Guide

## Overview

The CustomLangGraphChatBot project now has comprehensive modular test infrastructure that allows you to test specific tool categories independently. This guide shows how to use the testing system effectively.

## Test Structure

The project has separate test files for each tool category:

```
tests/
├── conftest.py                    # Shared test configuration and fixtures
├── test_ai_analysis_tools.py      # AI-powered analysis tools
├── test_static_analysis_tools.py  # Static code analysis tools  
├── test_github_tools.py           # GitHub integration tools
├── test_filesystem_tools.py       # File system operation tools
├── test_communication_tools.py    # Communication and notification tools
└── test_workflow_integration.py   # End-to-end workflow tests
```

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test Categories

**AI Analysis Tools:**
```bash
pytest tests/test_ai_analysis_tools.py -v
```

**Static Analysis Tools:**
```bash
pytest tests/test_static_analysis_tools.py -v
```

**GitHub Integration Tools:**
```bash
pytest tests/test_github_tools.py -v
```

**File System Tools:**
```bash
pytest tests/test_filesystem_tools.py -v
```

### Run Specific Test Classes

**Test only Pylint functionality:**
```bash
pytest tests/test_static_analysis_tools.py::TestPylintTool -v
```

**Test only AI configuration:**
```bash
pytest tests/test_ai_analysis_tools.py::TestAIConfig -v
```

**Test only GitHub repository tools:**
```bash
pytest tests/test_github_tools.py::TestGitHubRepositoryTool -v
```

### Run Individual Tests

**Test specific functionality:**
```bash
pytest tests/test_static_analysis_tools.py::TestPylintTool::test_successful_pylint_analysis -v
```

**Test AI provider configuration:**
```bash
pytest tests/test_ai_analysis_tools.py::TestAIConfig::test_default_config_groq -v
```

## Working Test Examples

### ✅ Currently Working Tests

**AI Configuration Tests (4/4 passing):**
```bash
pytest tests/test_ai_analysis_tools.py::TestAIConfig -v
# Tests: provider selection, fallback mechanisms, explicit configuration
```

**Static Analysis - Pylint Tests (5/5 passing):**
```bash
pytest tests/test_static_analysis_tools.py::TestPylintTool -v
# Tests: successful analysis, no issues, not installed, timeout, large code
```

**Static Analysis - Flake8 Tests (3/3 passing):**
```bash
pytest tests/test_static_analysis_tools.py::TestFlake8Tool -v
# Tests: successful analysis, no issues, not installed
```

**Static Analysis - Bandit Security Tests (3/3 passing):**
```bash
pytest tests/test_static_analysis_tools.py::TestBanditSecurityTool -v
# Tests: successful analysis, no issues, not installed
```

## Test Features

### Comprehensive Mocking
- External API calls are mocked to prevent actual network requests
- File system operations use temporary directories
- Environment variables are properly isolated

### Async Testing Support
- Full support for testing async tool methods (`_arun`)
- Proper async mocking with `AsyncMock`
- pytest-asyncio integration

### Parametrized Testing
- Multiple test scenarios with different inputs
- Edge case coverage
- Error condition testing

### Fixture Management
- Shared fixtures in `conftest.py`
- Tool instances with proper configuration
- Mock data for consistent testing

## Test Categories Status

| Category | Test File | Status | Working Tests |
|----------|-----------|--------|---------------|
| AI Analysis | `test_ai_analysis_tools.py` | ⚠️ Partial | 4/14 tests |
| Static Analysis | `test_static_analysis_tools.py` | ✅ Mostly Working | 12/17 tests |
| GitHub Integration | `test_github_tools.py` | ⚠️ Partial | 11/17 tests |
| File System | `test_filesystem_tools.py` | ❌ Needs Fixes | 4/21 tests |
| Communication | `test_communication_tools.py` | ❓ Not Tested | - |

## Known Issues

### Test-Implementation Mismatches
Some tests expect different return structures than actual implementations provide. This is due to:
- Tests written during early development phases
- Implementation changes after test creation
- Generic AI provider refactor that changed class names

### Outdated References
Some tests reference old classes that were replaced:
- `GrokLLM` → `GenericAILLM`
- `GrokConfig` → `AIConfig`

## Best Practices

### Running Tests During Development
1. **Start with working tests** to verify setup:
   ```bash
   pytest tests/test_ai_analysis_tools.py::TestAIConfig -v
   ```

2. **Test specific functionality** you're working on:
   ```bash
   pytest tests/test_static_analysis_tools.py::TestPylintTool -v
   ```

3. **Use verbose output** to see detailed test results:
   ```bash
   pytest tests/test_github_tools.py -v -s
   ```

### Adding New Tests
1. Follow the existing test structure in working test files
2. Use proper mocking for external dependencies
3. Test both success and error scenarios
4. Include edge cases and boundary conditions

## Quick Start Examples

**Test AI provider configuration:**
```bash
cd /path/to/CustomLangGraphChatBot
pytest tests/test_ai_analysis_tools.py::TestAIConfig::test_default_config_groq -v
```

**Test static analysis tools:**
```bash
pytest tests/test_static_analysis_tools.py::TestPylintTool::test_successful_pylint_analysis -v
```

**Test with coverage:**
```bash
pytest tests/test_static_analysis_tools.py --cov=tools.static_analysis_tools -v
```

The modular testing infrastructure is working and allows independent testing of each tool category. Focus on the working test examples above while the remaining test-implementation mismatches are resolved.
