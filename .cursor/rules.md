# LangGraph Code Review Chatbot - Development Rules

## LangGraph Specific Rules

### State Management
- Always define state schemas using Pydantic models with proper typing
- Use `TypedDict` for simple state structures
- Implement state validation in each node function
- Never mutate state directly - always return new state objects
- Use `add_messages` for conversation history management

### Graph Construction
- Define nodes with clear, descriptive names that indicate their purpose
- Use conditional edges for complex routing logic
- Always specify START and END nodes explicitly
- Implement proper error handling nodes for failure scenarios
- Add human-in-the-loop nodes where manual intervention might be needed

### Agent Design
- Keep individual nodes focused on single responsibilities
- Use tools for external API calls (GitHub API, analysis tools)
- Implement proper retry logic with exponential backoff
- Log all state transitions for debugging purposes
- Use streaming for long-running operations

## Python Code Standards

### Type Hints and Documentation
```python
from typing import Dict, List, Optional, Union, Any
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

def analyze_code(state: ReviewState) -> Dict[str, Any]:
    """Analyze code quality and generate review comments.
    
    Args:
        state: Current review state containing repository data
        
    Returns:
        Updated state with analysis results
        
    Raises:
        AnalysisError: If code analysis fails
    """
```

### Error Handling
- Use custom exception classes for different error types
- Implement try-catch blocks in all external API calls
- Log errors with sufficient context for debugging
- Provide graceful degradation when possible
- Never expose internal errors to end users

### Async/Await Patterns
- Use async/await for all I/O operations
- Implement proper session management for HTTP clients
- Use asyncio.gather() for parallel operations
- Handle timeouts appropriately
- Use connection pooling for efficiency

## GitHub Integration Rules

### API Usage
- Always check rate limits before making requests
- Implement exponential backoff for rate limit handling
- Use GitHub App authentication when possible
- Cache repository data to minimize API calls
- Validate webhook signatures for security

### Repository Processing
- Clone repositories to temporary directories
- Clean up temporary files after processing
- Handle large repositories with streaming
- Respect .gitignore patterns during analysis
- Process binary files appropriately

### Code Analysis
```python
# Good: Structured analysis with proper error handling
async def analyze_python_file(file_path: str, content: str) -> FileAnalysis:
    try:
        tree = ast.parse(content)
        analysis = FileAnalysis(
            file_path=file_path,
            language="python",
            complexity=calculate_complexity(tree),
            issues=find_issues(tree),
            suggestions=generate_suggestions(tree)
        )
        return analysis
    except SyntaxError as e:
        logger.warning(f"Syntax error in {file_path}: {e}")
        return FileAnalysis.create_error_analysis(file_path, str(e))
```

## Testing Rules

### Unit Testing
- Test each LangGraph node independently
- Mock all external dependencies (GitHub API, AI models)
- Use pytest fixtures for common test data
- Test both success and failure scenarios
- Maintain test coverage above 80%

### Integration Testing
- Test complete graph execution paths
- Use real repository data for integration tests
- Test error recovery and retry mechanisms
- Validate state transitions between nodes
- Test webhook handling end-to-end

### Test Structure
```python
@pytest.mark.asyncio
async def test_code_analysis_node():
    # Arrange
    initial_state = create_test_state()
    
    # Act
    result = await analyze_code_node(initial_state)
    
    # Assert
    assert result["analysis_complete"] is True
    assert len(result["issues"]) > 0
    assert result["confidence_score"] > 0.7
```

## Security Rules

### Authentication & Authorization
- Store GitHub tokens in environment variables or secure vaults
- Validate all webhook signatures
- Implement proper scope validation for GitHub tokens
- Use least-privilege principle for API access
- Rotate tokens regularly

### Input Validation
- Sanitize all user inputs before processing
- Validate repository URLs and paths
- Prevent path traversal attacks in file operations
- Limit file size and processing time
- Validate JSON payloads against schemas

### Code Execution Safety
- Never execute user-provided code directly
- Use sandboxed environments for code analysis
- Implement timeout limits for all operations
- Log all security-relevant events
- Scan for malicious patterns in code

## Performance Rules

### Memory Management
- Use generators for large file processing
- Implement proper cleanup in finally blocks
- Monitor memory usage for large repositories
- Use streaming for large API responses
- Cache expensive computations

### Concurrency
- Limit concurrent GitHub API requests
- Use semaphores to control resource usage
- Implement proper backpressure handling
- Use connection pooling efficiently
- Handle task cancellation gracefully

### Optimization Guidelines
```python
# Good: Efficient repository processing
async def process_repository_files(repo_path: str) -> List[FileAnalysis]:
    async def process_file(file_path: str) -> FileAnalysis:
        async with aiofiles.open(file_path, 'r') as f:
            content = await f.read()
            return await analyze_file(file_path, content)
    
    # Process files concurrently with controlled concurrency
    semaphore = asyncio.Semaphore(10)
    tasks = []
    
    for file_path in get_python_files(repo_path):
        async with semaphore:
            task = asyncio.create_task(process_file(file_path))
            tasks.append(task)
    
    return await asyncio.gather(*tasks, return_exceptions=True)
```

## Git and Version Control

### Commit Standards
- Use conventional commit format: `type(scope): description`
- Types: feat, fix, docs, style, refactor, test, chore
- Keep commits atomic and focused
- Write clear, descriptive commit messages
- Reference issues and PRs where relevant

### Branch Strategy
- Use feature branches for new functionality
- Keep main branch always deployable
- Use descriptive branch names: `feature/langgraph-integration`
- Squash commits before merging to main
- Tag releases with semantic versioning

## Documentation Rules

### Code Documentation
- Document all public APIs with comprehensive docstrings
- Include usage examples in docstrings
- Document complex algorithms and business logic
- Keep README files up to date
- Document configuration options and environment variables

### Architecture Documentation
- Maintain architecture decision records (ADRs)
- Document LangGraph state flow diagrams
- Keep API documentation current
- Document deployment procedures
- Maintain troubleshooting guides