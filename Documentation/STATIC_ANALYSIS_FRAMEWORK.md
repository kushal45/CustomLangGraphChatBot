# Language-Agnostic Static Analysis Framework

## 📋 Overview

The Language-Agnostic Static Analysis Framework is a comprehensive, extensible system designed to integrate static analysis tools across multiple programming languages without coupling to specific languages or tools. This framework is part of **Milestone 3: analyze_code_node Integration & Debugging**.

## 🏗️ Architecture Design

### Core Design Principles

1. **Language Independence** - No coupling to specific programming languages
2. **Tool Abstraction** - Generic interfaces for any static analysis tool
3. **Extensibility** - Easy to add new languages and tools
4. **State Tracking** - Comprehensive debugging and monitoring
5. **SOLID Principles** - Clean, maintainable architecture

### Architecture Components

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Workflow                       │
│                   (analyze_code_node)                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              Static Analysis Integration                    │
│                 (Adapter Pattern)                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│           Static Analysis Framework Core                    │
│  ┌─────────────────┬─────────────────┬─────────────────┐   │
│  │   Orchestrator  │ Language        │ State Tracker   │   │
│  │                 │ Detector        │                 │   │
│  └─────────────────┴─────────────────┴─────────────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                Tool Analyzers                               │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐ │
│  │   Python    │ JavaScript  │    Java     │   Future    │ │
│  │   (Pylint)  │  (ESLint)   │ (SpotBugs)  │   Tools     │ │
│  └─────────────┴─────────────┴─────────────┴─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Key Components

### 1. Language Detection (`FileExtensionLanguageDetector`)

**Purpose**: Automatically detect programming languages based on file extensions.

**Supported Languages**:
- Python (`.py`, `.pyw`, `.pyi`)
- JavaScript/TypeScript (`.js`, `.jsx`, `.ts`, `.tsx`)
- Java (`.java`)
- C/C++ (`.c`, `.cpp`, `.h`, `.hpp`)
- Go (`.go`)
- Rust (`.rs`)
- And many more...

**Usage**:
```python
detector = FileExtensionLanguageDetector()
language = detector.detect_language("main.py")  # Returns "python"
```

### 2. Base Analyzer (`BaseStaticAnalyzer`)

**Purpose**: Abstract base class implementing common functionality for all analyzers.

**Key Features**:
- Template method pattern for consistent execution flow
- Timeout handling and error management
- Standardized result format
- Metrics calculation

**Implementation Pattern**:
```python
class CustomAnalyzer(BaseStaticAnalyzer):
    def _setup_analyzer(self) -> None:
        self.supported_languages = {'custom_language'}
    
    async def _execute_analysis(self, file_path: str, content: str, language: str) -> Dict[str, Any]:
        # Execute your analysis tool
        pass
    
    def _parse_results(self, raw_output: str, language: str) -> List[AnalysisIssue]:
        # Parse tool output into standardized format
        pass
```

### 3. Concrete Analyzers

#### Python Pylint Analyzer
- **Tool**: Pylint
- **Languages**: Python
- **Features**: Code quality, style, error detection
- **Output**: JSON format with detailed issue information

#### JavaScript ESLint Analyzer
- **Tool**: ESLint
- **Languages**: JavaScript, TypeScript
- **Features**: Syntax errors, style issues, best practices
- **Output**: JSON format with rule violations

### 4. Analysis Orchestrator (`StaticAnalysisOrchestrator`)

**Purpose**: Coordinates analysis across multiple tools and languages.

**Key Features**:
- Automatic language detection and tool selection
- Concurrent tool execution with timeout controls
- Result aggregation and metrics calculation
- Comprehensive state tracking

**Usage**:
```python
config = AnalysisConfig(timeout_per_tool=60, max_concurrent_tools=4)
orchestrator = StaticAnalysisOrchestrator(config)
result = await orchestrator.analyze_repository(repository_info)
```

### 5. State Tracking (`AnalysisStateTracker`)

**Purpose**: Comprehensive tracking of analysis execution for debugging and monitoring.

**Tracked Events**:
- Analysis start/completion
- Language analysis lifecycle
- Tool execution status
- Error conditions and failures
- Performance metrics

### 6. Integration Adapter (`StaticAnalysisAdapter`)

**Purpose**: Bridge between the analysis framework and LangGraph workflow nodes.

**Key Features**:
- State format conversion
- Error handling and fallback mechanisms
- Performance metrics collection
- Recommendation generation

## 📊 Data Structures

### Analysis Issue
```python
@dataclass
class AnalysisIssue:
    file_path: str
    line_number: int
    column: Optional[int]
    severity: IssueSeverity
    category: str
    message: str
    rule_id: Optional[str] = None
    suggestion: Optional[str] = None
```

### Tool Analysis Result
```python
@dataclass
class ToolAnalysisResult:
    tool_name: str
    language: str
    status: AnalysisStatus
    issues: List[AnalysisIssue]
    metrics: Dict[str, Any]
    execution_time: float
    error_message: Optional[str] = None
```

### Repository Analysis Result
```python
@dataclass
class RepositoryAnalysisResult:
    repository_url: str
    analysis_id: str
    timestamp: str
    languages_detected: Set[str]
    language_results: Dict[str, LanguageAnalysisResult]
    overall_metrics: Dict[str, Any]
    execution_summary: Dict[str, Any]
```

## 🚀 Usage Examples

### Basic Usage in analyze_code_node

```python
from tools.static_analysis_integration import analyze_repository_with_static_analysis

async def analyze_code_node(state: ReviewState) -> Dict[str, Any]:
    # Execute comprehensive static analysis
    updated_state = await analyze_repository_with_static_analysis(state)
    
    # Return results in node format
    return {
        "current_step": updated_state.get("current_step", "generate_report"),
        "analysis_results": updated_state.get("analysis_results", {}),
        "analysis_metadata": updated_state.get("analysis_metadata", {})
    }
```

### Custom Configuration

```python
from tools.static_analysis_integration import create_custom_analysis_config

# Create custom configuration
config = create_custom_analysis_config(
    timeout_per_tool=30,
    max_concurrent_tools=2,
    severity_threshold=IssueSeverity.MEDIUM,
    excluded_patterns=['*.min.js', 'node_modules/*']
)

adapter = StaticAnalysisAdapter(config)
```

### Adding New Analyzers

```python
class RustClippyAnalyzer(BaseStaticAnalyzer):
    def _setup_analyzer(self) -> None:
        self.supported_languages = {'rust'}
        self.tool_command = ['cargo', 'clippy', '--message-format=json']
    
    def get_tool_name(self) -> str:
        return "clippy"
    
    async def _execute_analysis(self, file_path: str, content: str, language: str) -> Dict[str, Any]:
        # Implementation for Rust Clippy
        pass
    
    def _parse_results(self, raw_output: str, language: str) -> List[AnalysisIssue]:
        # Parse Clippy output
        pass

# Add to orchestrator
orchestrator.add_analyzer(RustClippyAnalyzer(config))
```

## 🔍 Debugging and Monitoring

### State Tracking Integration

The framework integrates with the existing debugging infrastructure:

```python
from debug.repository_debugging import repo_debugger

# Debug breakpoints are automatically triggered at key points:
# - Analysis start/completion
# - Language detection
# - Tool execution
# - Error conditions
```

### Performance Metrics

```python
# Get integration metrics
adapter = StaticAnalysisAdapter()
metrics = adapter.get_integration_metrics()

print(f"Total analyses: {metrics['total_analyses']}")
print(f"Success rate: {metrics['successful_analyses'] / metrics['total_analyses']}")
print(f"Average execution time: {metrics['average_execution_time']:.2f}s")
```

### Analysis State Inspection

```python
# Get detailed analysis state
tracker = AnalysisStateTracker()
state = tracker.get_analysis_summary(analysis_id)

# Inspect execution log
for event in tracker.execution_log:
    print(f"{event['timestamp']}: {event['event_type']} - {event['data']}")
```

## 🧪 Testing

### Unit Tests
- Language detection functionality
- Individual analyzer implementations
- State tracking and metrics
- Configuration and validation

### Integration Tests
- End-to-end analysis workflows
- Multi-language repository analysis
- Error handling and recovery
- Performance and timeout scenarios

### Running Tests
```bash
# Run unit tests
python -m pytest tests/unit/test_static_analysis_framework.py -v

# Run integration tests
python -m pytest tests/integration/test_analyze_code_node_integration.py -v
```

## 🔄 Extensibility

### Adding New Languages

1. Update `FileExtensionLanguageDetector` with new file extensions
2. Create analyzer class inheriting from `BaseStaticAnalyzer`
3. Implement required abstract methods
4. Add to `AnalyzerFactory` if needed

### Adding New Tools

1. Create analyzer class for the tool
2. Implement tool-specific execution logic
3. Parse tool output into standardized format
4. Add to orchestrator configuration

### Custom Integration

The framework supports custom integration patterns through:
- Configurable analysis parameters
- Pluggable analyzer architecture
- Extensible result format
- Custom recommendation engines

## 📈 Performance Considerations

- **Concurrent Execution**: Multiple tools run in parallel
- **Timeout Controls**: Prevent hanging on problematic files
- **Memory Management**: Temporary file cleanup
- **Caching**: Future enhancement for repeated analyses
- **Streaming**: Large file handling capabilities

## 🛡️ Error Handling

- **Tool Failures**: Graceful degradation when tools fail
- **Timeout Management**: Automatic timeout and recovery
- **Validation**: Input validation and sanitization
- **Logging**: Comprehensive error logging and debugging
- **Fallback**: Continue analysis even if some tools fail

This framework provides a solid foundation for language-agnostic static analysis that can grow and adapt as new languages and tools are added to the ecosystem.
