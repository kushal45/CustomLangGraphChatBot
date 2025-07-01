# LangGraph Code Review Chatbot - Project Context

## Project Overview
This is a sophisticated code review chatbot built using LangGraph for analyzing GitHub MCP (Model Context Protocol) server repositories. The chatbot performs automated code reviews, identifies potential issues, suggests improvements, and provides detailed feedback on code quality, security, and best practices.

## Technology Stack
- **Framework**: LangGraph for building stateful, multi-agent conversational AI
- **Language**: Python 3.9+
- **AI Integration**: OpenAI GPT models / Anthropic Claude
- **GitHub Integration**: GitHub API, webhooks, and MCP protocol
- **Data Processing**: Langchain for document processing and retrieval
- **Vector Store**: ChromaDB/Pinecone for code embeddings
- **Web Framework**: FastAPI for API endpoints
- **Authentication**: GitHub OAuth/Token-based auth
- **Deployment**: Docker containerization

## Core Architecture Patterns

### LangGraph State Management
- Use StateGraph for managing conversation flow
- Implement proper state transitions between review stages
- Maintain conversation context across multiple interactions
- Handle error states and recovery mechanisms

### Code Analysis Pipeline
1. **Repository Ingestion**: Clone and parse repository structure
2. **Code Parsing**: Extract functions, classes, and dependencies
3. **Static Analysis**: Run linting, security scans, complexity analysis
4. **AI Review**: Generate contextual code review feedback
5. **Report Generation**: Compile comprehensive review reports

### GitHub MCP Integration
- Implement MCP protocol for GitHub repository access
- Handle repository metadata, commits, pull requests
- Process file changes and diffs effectively
- Manage rate limiting and API quotas

## Code Organization Structure
```
src/
├── agents/          # LangGraph agent definitions
├── tools/           # GitHub API and analysis tools
├── schemas/         # Pydantic models and data structures
├── services/        # Business logic services
├── api/            # FastAPI routes and endpoints
├── utils/          # Utility functions and helpers
├── config/         # Configuration management
└── tests/          # Test suites
```

## Key Components to Focus On

### LangGraph Agents
- **ReviewCoordinator**: Orchestrates the entire review process
- **CodeAnalyzer**: Performs technical code analysis
- **SecurityScanner**: Identifies security vulnerabilities
- **QualityAssessor**: Evaluates code quality metrics
- **ReportGenerator**: Compiles and formats review results

### GitHub Integration
- Repository cloning and file system navigation
- Commit history analysis and diff processing
- Pull request context understanding
- Issue tracking and linking

### AI-Powered Analysis
- Code smell detection using pattern matching
- Performance bottleneck identification
- Best practice recommendations
- Documentation quality assessment

## Development Standards

### LangGraph Best Practices
- Define clear state schemas with proper typing
- Use conditional edges for complex decision logic
- Implement proper error handling in all nodes
- Maintain conversation memory efficiently
- Test state transitions thoroughly

### Code Quality Standards
- Follow PEP 8 for Python code formatting
- Use type hints for all function signatures
- Implement comprehensive error handling
- Write descriptive docstrings for all public methods
- Maintain test coverage above 80%

### GitHub API Integration
- Implement proper rate limiting and retry logic
- Use pagination for large repository data
- Cache frequently accessed repository information
- Handle GitHub API authentication securely

## Testing Strategy
- Unit tests for individual LangGraph nodes
- Integration tests for complete review workflows
- Mock GitHub API responses for consistent testing
- Performance tests for large repository handling
- End-to-end tests for complete user journeys

## Security Considerations
- Secure storage of GitHub tokens and API keys
- Input validation for all user-provided data
- Sandboxed code execution for analysis
- Audit logging for all review actions
- Rate limiting to prevent abuse

## Performance Optimization
- Efficient repository parsing and caching
- Parallel processing of multiple files
- Optimized vector embeddings for code search
- Streaming responses for large reviews
- Memory management for large codebases