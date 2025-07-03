"""Tool registry and configuration management for CustomLangGraphChatBot."""

import os
from typing import Dict, List, Any, Optional, Type
from enum import Enum
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from logging_config import get_logger

logger = get_logger(__name__)

# Import all tool modules
from .github_tools import GITHUB_TOOLS
from .analysis_tools import ANALYSIS_TOOLS
from .ai_analysis_tools import AI_ANALYSIS_TOOLS
from .filesystem_tools import FILESYSTEM_TOOLS
from .communication_tools import COMMUNICATION_TOOLS


class ToolCategory(Enum):
    """Categories of available tools."""
    GITHUB = "github"
    STATIC_ANALYSIS = "static_analysis"
    AI_ANALYSIS = "ai_analysis"
    FILESYSTEM = "filesystem"
    COMMUNICATION = "communication"


class RepositoryType(Enum):
    """Types of repositories that can be analyzed."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CSHARP = "csharp"
    GO = "go"
    RUST = "rust"
    CPP = "cpp"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class ToolConfig(BaseModel):
    """Configuration for tool management."""
    # Core tool configuration
    enabled_categories: List[str] = Field(default_factory=lambda: ["filesystem", "analysis", "ai_analysis", "github", "communication"])
    max_concurrent_tools: int = Field(default_factory=lambda: int(os.getenv("TOOL_MAX_CONCURRENT", "5")))
    tool_timeout: int = Field(default_factory=lambda: int(os.getenv("TOOL_TIMEOUT", "300")))
    enable_caching: bool = Field(default_factory=lambda: os.getenv("TOOL_ENABLE_CACHING", "true").lower() == "true")

    # GitHub configuration
    github_token: str = Field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))

    # AI analysis configuration - Generic AI provider support
    ai_provider: str = Field(default_factory=lambda: os.getenv("AI_PROVIDER", "groq"))
    groq_api_key: str = Field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    huggingface_api_key: str = Field(default_factory=lambda: os.getenv("HUGGINGFACE_API_KEY", ""))
    together_api_key: str = Field(default_factory=lambda: os.getenv("TOGETHER_API_KEY", ""))
    google_api_key: str = Field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    openrouter_api_key: str = Field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    xai_api_key: str = Field(default_factory=lambda: os.getenv("XAI_API_KEY", ""))  # Grok
    ollama_base_url: str = Field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"))

    # Legacy OpenAI support (deprecated but kept for backward compatibility)
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    ai_model: str = "llama3-8b-8192"  # Default to Groq model
    ai_temperature: float = 0.1
    
    # Static analysis configuration
    enable_pylint: bool = True
    enable_flake8: bool = True
    enable_bandit: bool = True
    enable_complexity_analysis: bool = True
    
    # Communication configuration
    slack_webhook_url: str = Field(default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL", ""))
    email_enabled: bool = False
    jira_enabled: bool = False
    
    # File system configuration
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: List[str] = Field(default_factory=lambda: [
        '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.go', 
        '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.r', '.m',
        '.txt', '.md', '.json', '.yaml', '.yml', '.xml', '.toml', '.ini'
    ])
    
    # Tool selection based on repository type
    tool_selection_rules: Dict[str, List[str]] = Field(default_factory=lambda: {
        "python": ["github_repository", "github_file_content", "pylint_analysis", 
                  "flake8_analysis", "bandit_security", "code_complexity", 
                  "ai_code_review", "file_reader"],
        "javascript": ["github_repository", "github_file_content", "ai_code_review", 
                      "file_reader", "directory_lister"],
        "typescript": ["github_repository", "github_file_content", "ai_code_review", 
                      "file_reader", "directory_lister"],
        "java": ["github_repository", "github_file_content", "ai_code_review", 
                "file_reader", "directory_lister"],
        "mixed": ["github_repository", "github_file_content", "ai_code_review", 
                 "file_reader", "directory_lister", "git_repository"],
        "default": ["github_repository", "github_file_content", "ai_code_review", 
                   "file_reader"]
    })


class ToolRegistry:
    """Registry for managing and accessing tools."""

    def __init__(self, config: Optional[ToolConfig] = None):
        self.config = config or ToolConfig()
        self._tools: Dict[str, BaseTool] = {}
        self._categories: Dict[ToolCategory, List[str]] = {}

        logger.info("Initializing tool registry", extra={
            "config_type": type(self.config).__name__
        })

        self._initialize_tools()

        logger.info("Tool registry initialized successfully", extra={
            "total_tools": len(self._tools),
            "categories": list(self._categories.keys()),
            "tools_by_category": {cat.value: len(tools) for cat, tools in self._categories.items()}
        })
    
    def _initialize_tools(self):
        """Initialize all available tools."""
        logger.debug("Starting tool initialization")

        # Register GitHub tools
        logger.debug(f"Registering {len(GITHUB_TOOLS)} GitHub tools")
        for tool in GITHUB_TOOLS:
            self._tools[tool.name] = tool
            logger.debug(f"Registered GitHub tool: {tool.name}")
        self._categories[ToolCategory.GITHUB] = [tool.name for tool in GITHUB_TOOLS]

        # Register static analysis tools
        logger.debug(f"Registering {len(ANALYSIS_TOOLS)} static analysis tools")
        for tool in ANALYSIS_TOOLS:
            self._tools[tool.name] = tool
            logger.debug(f"Registered analysis tool: {tool.name}")
        self._categories[ToolCategory.STATIC_ANALYSIS] = [tool.name for tool in ANALYSIS_TOOLS]

        # Register AI analysis tools
        logger.debug(f"Registering {len(AI_ANALYSIS_TOOLS)} AI analysis tools")
        for tool in AI_ANALYSIS_TOOLS:
            self._tools[tool.name] = tool
            logger.debug(f"Registered AI tool: {tool.name}")
        self._categories[ToolCategory.AI_ANALYSIS] = [tool.name for tool in AI_ANALYSIS_TOOLS]

        # Register filesystem tools
        logger.debug(f"Registering {len(FILESYSTEM_TOOLS)} filesystem tools")
        for tool in FILESYSTEM_TOOLS:
            self._tools[tool.name] = tool
            logger.debug(f"Registered filesystem tool: {tool.name}")
        self._categories[ToolCategory.FILESYSTEM] = [tool.name for tool in FILESYSTEM_TOOLS]

        # Register communication tools
        logger.debug(f"Registering {len(COMMUNICATION_TOOLS)} communication tools")
        for tool in COMMUNICATION_TOOLS:
            self._tools[tool.name] = tool
            logger.debug(f"Registered communication tool: {tool.name}")
        self._categories[ToolCategory.COMMUNICATION] = [tool.name for tool in COMMUNICATION_TOOLS]

        logger.debug("Tool initialization completed")
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a specific tool by name."""
        logger.debug(f"Retrieving tool: {tool_name}")
        tool = self._tools.get(tool_name)

        if tool:
            logger.debug(f"Tool found: {tool_name}")
        else:
            logger.warning(f"Tool not found: {tool_name}", extra={
                "available_tools": list(self._tools.keys())
            })

        return tool
    
    def get_tools_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """Get all tools in a specific category."""
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def get_all_tools(self) -> List[BaseTool]:
        """Get all available tools."""
        return list(self._tools.values())
    
    def get_tools_for_repository(self, repo_type: RepositoryType) -> List[BaseTool]:
        """Get recommended tools for a specific repository type."""
        repo_type_str = repo_type.value
        
        # Get tool names for this repository type
        if repo_type_str in self.config.tool_selection_rules:
            tool_names = self.config.tool_selection_rules[repo_type_str]
        else:
            tool_names = self.config.tool_selection_rules["default"]
        
        # Return actual tool instances
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def detect_repository_type(self, file_extensions: List[str]) -> RepositoryType:
        """Detect repository type based on file extensions."""
        extension_counts = {}
        
        for ext in file_extensions:
            ext_lower = ext.lower()
            extension_counts[ext_lower] = extension_counts.get(ext_lower, 0) + 1
        
        # Determine primary language based on file extensions
        if extension_counts.get('.py', 0) > 0:
            if len([ext for ext in extension_counts.keys() if ext in ['.js', '.ts', '.java', '.cpp']]) > 0:
                return RepositoryType.MIXED
            return RepositoryType.PYTHON
        
        elif extension_counts.get('.js', 0) > 0:
            return RepositoryType.JAVASCRIPT
        
        elif extension_counts.get('.ts', 0) > 0:
            return RepositoryType.TYPESCRIPT
        
        elif extension_counts.get('.java', 0) > 0:
            return RepositoryType.JAVA
        
        elif extension_counts.get('.cs', 0) > 0:
            return RepositoryType.CSHARP
        
        elif extension_counts.get('.go', 0) > 0:
            return RepositoryType.GO
        
        elif extension_counts.get('.rs', 0) > 0:
            return RepositoryType.RUST
        
        elif any(ext in extension_counts for ext in ['.cpp', '.c', '.h']):
            return RepositoryType.CPP
        
        elif len(extension_counts) > 3:
            return RepositoryType.MIXED
        
        else:
            return RepositoryType.UNKNOWN
    
    def get_tool_names(self) -> List[str]:
        """Get list of all available tool names."""
        return list(self._tools.keys())
    
    def get_category_tools(self) -> Dict[str, List[str]]:
        """Get tools organized by category."""
        return {
            category.value: tool_names 
            for category, tool_names in self._categories.items()
        }
    
    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check if a specific tool is enabled based on configuration."""
        # Check static analysis tool enablement
        if tool_name == "pylint_analysis" and not self.config.enable_pylint:
            return False
        elif tool_name == "flake8_analysis" and not self.config.enable_flake8:
            return False
        elif tool_name == "bandit_security" and not self.config.enable_bandit:
            return False
        elif tool_name == "code_complexity" and not self.config.enable_complexity_analysis:
            return False
        
        # Check AI tool requirements - check for any available AI provider
        if tool_name in ["ai_code_review", "ai_documentation_generator", "ai_refactoring_suggestions", "ai_test_generator"]:
            return self._has_ai_provider_available()
        
        if tool_name in ["github_repository", "github_file_content", "github_pull_request"]:
            return bool(self.config.github_token)
        
        if tool_name == "slack_notification":
            return bool(self.config.slack_webhook_url)
        
        if tool_name == "email_notification":
            return self.config.email_enabled
        
        if tool_name == "jira_integration":
            return self.config.jira_enabled
        
        return True

    def _has_ai_provider_available(self) -> bool:
        """Check if any AI provider is available."""
        return any([
            self.config.groq_api_key,
            self.config.huggingface_api_key,
            self.config.together_api_key,
            self.config.google_api_key,
            self.config.openrouter_api_key,
            self.config.xai_api_key,
            self.config.openai_api_key,  # Legacy support
            True  # Ollama doesn't need API key, always available if running locally
        ])

    def get_enabled_tools(self) -> List[BaseTool]:
        """Get only the tools that are enabled based on configuration."""
        return [
            tool for tool_name, tool in self._tools.items() 
            if self.is_tool_enabled(tool_name)
        ]
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate the current configuration and return status."""
        validation_results = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "enabled_tools": [],
            "disabled_tools": []
        }
        
        # Check required configurations
        if not self.config.github_token:
            validation_results["warnings"].append("GitHub token not configured - GitHub tools will be disabled")
        
        if not self.config.openai_api_key:
            validation_results["warnings"].append("OpenAI API key not configured - AI analysis tools will be disabled")
        
        # Check tool availability
        for tool_name in self._tools.keys():
            if self.is_tool_enabled(tool_name):
                validation_results["enabled_tools"].append(tool_name)
            else:
                validation_results["disabled_tools"].append(tool_name)
        
        # Check if any tools are enabled
        if not validation_results["enabled_tools"]:
            validation_results["valid"] = False
            validation_results["errors"].append("No tools are enabled - check your configuration")
        
        return validation_results


# Global tool registry instance
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry(config: Optional[ToolConfig] = None) -> ToolRegistry:
    """Get the global tool registry instance."""
    global _global_registry
    
    if _global_registry is None or config is not None:
        _global_registry = ToolRegistry(config)
    
    return _global_registry


def initialize_tools(config: Optional[ToolConfig] = None) -> ToolRegistry:
    """Initialize the tool registry with configuration."""
    return get_tool_registry(config)


# Convenience functions
def get_tool(tool_name: str) -> Optional[BaseTool]:
    """Get a tool by name from the global registry."""
    return get_tool_registry().get_tool(tool_name)


def get_tools_for_repo_type(repo_type: RepositoryType) -> List[BaseTool]:
    """Get tools recommended for a repository type."""
    return get_tool_registry().get_tools_for_repository(repo_type)


def get_enabled_tools() -> List[BaseTool]:
    """Get all enabled tools from the global registry."""
    return get_tool_registry().get_enabled_tools()
