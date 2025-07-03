"""AI-powered analysis tools for LangGraph workflow with multiple AI provider support."""

import os
import requests
import json
from typing import Dict, Any, List, Optional, Literal
from langchain.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from enum import Enum
from .logging_utils import log_tool_execution, log_api_call, LoggedBaseTool
from logging_config import get_logger

logger = get_logger(__name__)


class AIProvider(str, Enum):
    """Supported AI providers."""
    GROQ = "groq"
    HUGGINGFACE = "huggingface"
    TOGETHER = "together"
    GOOGLE = "google"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    GROK = "grok"  # Keep for backward compatibility


class AIConfig(BaseModel):
    """Configuration for AI analysis tools with multiple provider support."""
    provider: AIProvider = Field(default=AIProvider.GROQ, description="AI provider to use")
    model_name: str = Field(default="llama3-8b-8192", description="Model name")
    temperature: float = 0.1
    max_tokens: int = 2000
    api_key: str = Field(default="", description="API key for the provider")
    base_url: str = Field(default="", description="Base URL for the provider")

    def __init__(self, **data):
        super().__init__(**data)
        if not self.api_key or not self.base_url:
            self._set_provider_defaults()

    def _set_provider_defaults(self):
        """Set default values based on the provider."""
        provider_configs = {
            AIProvider.GROQ: {
                "api_key": os.getenv("GROQ_API_KEY", ""),
                "base_url": "https://api.groq.com/openai/v1",
                "model_name": "llama3-8b-8192"
            },
            AIProvider.HUGGINGFACE: {
                "api_key": os.getenv("HUGGINGFACE_API_KEY", ""),
                "base_url": "https://api-inference.huggingface.co/models",
                "model_name": "microsoft/DialoGPT-medium"
            },
            AIProvider.TOGETHER: {
                "api_key": os.getenv("TOGETHER_API_KEY", ""),
                "base_url": "https://api.together.xyz/v1",
                "model_name": "meta-llama/Llama-2-7b-chat-hf"
            },
            AIProvider.GOOGLE: {
                "api_key": os.getenv("GOOGLE_API_KEY", ""),
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "model_name": "gemini-pro"
            },
            AIProvider.OLLAMA: {
                "api_key": "",  # Ollama doesn't need API key
                "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                "model_name": "llama2"
            },
            AIProvider.OPENROUTER: {
                "api_key": os.getenv("OPENROUTER_API_KEY", ""),
                "base_url": "https://openrouter.ai/api/v1",
                "model_name": "microsoft/wizardlm-2-8x22b"
            },
            AIProvider.GROK: {
                "api_key": os.getenv("XAI_API_KEY", ""),
                "base_url": "https://api.x.ai/v1",
                "model_name": "grok-beta"
            }
        }

        config = provider_configs.get(self.provider, {})
        if not self.api_key:
            self.api_key = config.get("api_key", "")
        if not self.base_url:
            self.base_url = config.get("base_url", "")
        if self.model_name == "llama3-8b-8192":  # Default value
            self.model_name = config.get("model_name", self.model_name)


class GenericAILLM:
    """Generic AI LLM wrapper for multiple providers with LangChain compatibility."""

    def __init__(self, config: AIConfig):
        self.config = config
        self.headers = self._get_headers()

    def _get_headers(self) -> Dict[str, str]:
        """Get headers based on the provider."""
        base_headers = {"Content-Type": "application/json"}

        if self.config.provider == AIProvider.GROQ:
            base_headers["Authorization"] = f"Bearer {self.config.api_key}"
        elif self.config.provider == AIProvider.HUGGINGFACE:
            base_headers["Authorization"] = f"Bearer {self.config.api_key}"
        elif self.config.provider == AIProvider.TOGETHER:
            base_headers["Authorization"] = f"Bearer {self.config.api_key}"
        elif self.config.provider == AIProvider.GOOGLE:
            # Google uses API key in URL params
            pass
        elif self.config.provider == AIProvider.OLLAMA:
            # Ollama doesn't need authorization
            pass
        elif self.config.provider == AIProvider.OPENROUTER:
            base_headers["Authorization"] = f"Bearer {self.config.api_key}"
            base_headers["HTTP-Referer"] = "https://github.com/kushal45/CustomLangGraphChatBot"
        elif self.config.provider == AIProvider.GROK:
            base_headers["Authorization"] = f"Bearer {self.config.api_key}"

        return base_headers

    def invoke(self, messages: List[Dict[str, str]]) -> str:
        """Invoke AI API with messages."""
        if self.config.provider != AIProvider.OLLAMA and not self.config.api_key:
            raise ValueError(f"API key is required for {self.config.provider.value}")

        # Convert LangChain message format to standard format
        formatted_messages = []
        for message in messages:
            if hasattr(message, 'content'):
                formatted_messages.append({
                    "role": "user" if message.__class__.__name__ == "HumanMessage" else "assistant",
                    "content": message.content
                })
            elif isinstance(message, dict):
                formatted_messages.append(message)
            else:
                formatted_messages.append({"role": "user", "content": str(message)})

        return self._make_request(formatted_messages)

    def _make_request(self, messages: List[Dict[str, str]]) -> str:
        """Make API request based on provider."""
        if self.config.provider == AIProvider.GOOGLE:
            return self._google_request(messages)
        elif self.config.provider == AIProvider.HUGGINGFACE:
            return self._huggingface_request(messages)
        else:
            return self._openai_compatible_request(messages)

    def _openai_compatible_request(self, messages: List[Dict[str, str]]) -> str:
        """Make OpenAI-compatible API request (Groq, Together, Ollama, OpenRouter, Grok)."""
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }

        try:
            response = requests.post(
                f"{self.config.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            raise Exception(f"{self.config.provider.value} API request failed: {str(e)}")
        except KeyError as e:
            raise Exception(f"Unexpected {self.config.provider.value} API response format: {str(e)}")

    def __or__(self, other):
        """Support for LangChain pipe operator."""
        return AIChain(self, other)


    def _google_request(self, messages: List[Dict[str, str]]) -> str:
        """Make Google Gemini API request."""
        # Google Gemini has a different format
        text_content = messages[-1]["content"] if messages else ""

        url = f"{self.config.base_url}/models/{self.config.model_name}:generateContent"
        payload = {
            "contents": [{
                "parts": [{"text": text_content}]
            }],
            "generationConfig": {
                "temperature": self.config.temperature,
                "maxOutputTokens": self.config.max_tokens
            }
        }

        try:
            response = requests.post(
                f"{url}?key={self.config.api_key}",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]

        except requests.exceptions.RequestException as e:
            raise Exception(f"Google API request failed: {str(e)}")
        except KeyError as e:
            raise Exception(f"Unexpected Google API response format: {str(e)}")

    def _huggingface_request(self, messages: List[Dict[str, str]]) -> str:
        """Make Hugging Face Inference API request."""
        text_content = messages[-1]["content"] if messages else ""

        url = f"{self.config.base_url}/{self.config.model_name}"
        payload = {
            "inputs": text_content,
            "parameters": {
                "temperature": self.config.temperature,
                "max_new_tokens": self.config.max_tokens
            }
        }

        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "")
            return str(result)

        except requests.exceptions.RequestException as e:
            raise Exception(f"Hugging Face API request failed: {str(e)}")
        except KeyError as e:
            raise Exception(f"Unexpected Hugging Face API response format: {str(e)}")


class AIChain:
    """Chain wrapper for AI LLM to support LangChain patterns."""

    def __init__(self, llm: GenericAILLM, parser):
        self.llm = llm
        self.parser = parser

    def invoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the chain with inputs."""
        # Format the prompt with inputs
        if hasattr(self.parser, 'prompt'):
            formatted_prompt = self.parser.prompt.format(**inputs)
        else:
            # Assume inputs contain the formatted message
            formatted_prompt = str(inputs)

        # Call AI provider
        response = self.llm.invoke([{"role": "user", "content": formatted_prompt}])

        # Parse the response
        if hasattr(self.parser, 'parse'):
            return self.parser.parse(response)
        else:
            # Try to parse as JSON
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {"raw_response": response}


def get_ai_config() -> AIConfig:
    """Get AI configuration from environment variables."""
    # Try to determine the best available provider
    provider = AIProvider.GROQ  # Default to Groq

    # Check for available API keys and set provider accordingly
    if os.getenv("GROQ_API_KEY"):
        provider = AIProvider.GROQ
    elif os.getenv("HUGGINGFACE_API_KEY"):
        provider = AIProvider.HUGGINGFACE
    elif os.getenv("TOGETHER_API_KEY"):
        provider = AIProvider.TOGETHER
    elif os.getenv("GOOGLE_API_KEY"):
        provider = AIProvider.GOOGLE
    elif os.getenv("OPENROUTER_API_KEY"):
        provider = AIProvider.OPENROUTER
    elif os.getenv("XAI_API_KEY"):
        provider = AIProvider.GROK
    else:
        # Try Ollama as fallback (no API key needed)
        provider = AIProvider.OLLAMA

    # Allow override via environment variable
    env_provider = os.getenv("AI_PROVIDER", "").lower()
    if env_provider in [p.value for p in AIProvider]:
        provider = AIProvider(env_provider)

    return AIConfig(provider=provider)


class CodeReviewTool(BaseTool, LoggedBaseTool):
    """AI-powered code review tool with multiple provider support."""

    name: str = "ai_code_review"
    description: str = """
    Perform comprehensive AI-powered code review using configurable AI providers including:
    - Code quality assessment
    - Best practices evaluation
    - Bug detection
    - Performance suggestions
    - Maintainability analysis

    Input should be a JSON object with:
    - code: The code to review
    - language: Programming language (optional, defaults to Python)
    - context: Additional context about the code (optional)
    """

    config: AIConfig = Field(default_factory=get_ai_config)

    def __init__(self, **kwargs):
        BaseTool.__init__(self, **kwargs)
        LoggedBaseTool.__init__(self)
    
    @log_tool_execution
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Perform AI code review using configurable AI provider."""
        try:
            import json
            params = json.loads(query)

            code = params.get("code", "")
            language = params.get("language", "Python")
            context = params.get("context", "")

            self.log_info("Starting AI code review", extra={
                "language": language,
                "code_length": len(code),
                "has_context": bool(context),
                "provider": self.config.provider
            })

            if not code:
                self.log_error("No code provided for review")
                return {"error": "No code provided for review"}

            # Initialize AI LLM
            llm = GenericAILLM(self.config)
            
            # Create prompt for Grok
            prompt_text = f"""
You are an expert code reviewer. Analyze the following {language} code and provide a comprehensive review.

Code to review:
```{language}
{code}
```

Additional context: {context or "No additional context provided"}

Please provide your review in the following JSON format:
{{
    "overall_score": <score from 1-10>,
    "summary": "<brief summary of code quality>",
    "strengths": ["<list of code strengths>"],
    "issues": [
        {{
            "severity": "<HIGH|MEDIUM|LOW>",
            "category": "<category like 'Performance', 'Security', 'Style', etc.>",
            "description": "<detailed description>",
            "suggestion": "<specific improvement suggestion>",
            "line_reference": "<line number or range if applicable>"
        }}
    ],
    "suggestions": [
        {{
            "category": "<category>",
            "description": "<improvement suggestion>",
            "impact": "<expected impact>"
        }}
    ],
    "best_practices": ["<list of best practices to follow>"],
    "maintainability_score": <score from 1-10>,
    "readability_score": <score from 1-10>,
    "performance_notes": ["<performance-related observations>"]
}}

Respond only with valid JSON, no additional text.
"""

            self.log_debug("Sending code review request to AI provider", extra={
                "provider": self.config.provider,
                "prompt_length": len(prompt_text)
            })

            # Execute review with AI provider
            response = llm.invoke([{"role": "user", "content": prompt_text}])

            self.log_debug("Received AI response", extra={
                "response_length": len(response),
                "provider": self.config.provider
            })

            # Parse JSON response
            try:
                result = json.loads(response)
                self.log_debug("Successfully parsed AI response as JSON")
            except json.JSONDecodeError:
                self.log_warning("Failed to parse AI response as JSON, attempting extraction", extra={
                    "provider": self.config.provider
                })
                # If JSON parsing fails, try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                        self.log_debug("Successfully extracted JSON from AI response")
                    except json.JSONDecodeError:
                        self.log_error("Failed to extract valid JSON from AI response", extra={
                            "provider": self.config.provider,
                            "response_preview": response[:200]
                        })
                        return {"error": f"Failed to parse {self.config.provider.value} response as JSON", "raw_response": response}
                else:
                    self.log_error("No JSON found in AI response", extra={
                        "provider": self.config.provider,
                        "response_preview": response[:200]
                    })
                    return {"error": f"Failed to parse {self.config.provider.value} response as JSON", "raw_response": response}
            
            final_result = {
                "tool": "ai_code_review",
                "language": language,
                "review": result
            }

            self.log_info("AI code review completed successfully", extra={
                "provider": self.config.provider,
                "language": language,
                "overall_score": result.get("overall_score"),
                "issues_count": len(result.get("issues", [])),
                "suggestions_count": len(result.get("suggestions", [])),
                "has_performance_notes": bool(result.get("performance_notes"))
            })

            return final_result

        except Exception as e:
            # Use locals().get() to safely access language variable
            language_info = locals().get('language', 'unknown')
            self.log_error("AI code review failed", extra={
                "error": str(e),
                "provider": self.config.provider,
                "language": language_info
            })
            return {"error": f"AI code review failed: {str(e)}"}


class DocumentationGeneratorTool(BaseTool):
    """AI tool for generating code documentation with multiple provider support."""

    name: str = "ai_documentation_generator"
    description: str = """
    Generate comprehensive documentation for code using configurable AI providers including:
    - Function/class docstrings
    - API documentation
    - Usage examples
    - Parameter descriptions

    Input should be a JSON object with:
    - code: The code to document
    - language: Programming language (optional, defaults to Python)
    - doc_style: Documentation style (google, numpy, sphinx, etc.)
    """

    config: AIConfig = Field(default_factory=get_ai_config)
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Generate documentation for code."""
        try:
            import json
            params = json.loads(query)
            
            code = params.get("code", "")
            language = params.get("language", "Python")
            doc_style = params.get("doc_style", "google")
            
            if not code:
                return {"error": "No code provided for documentation"}
            
            # Initialize AI LLM
            llm = GenericAILLM(self.config)
            
            # Create prompt for Grok
            prompt_text = f"""
You are an expert technical writer. Generate comprehensive documentation for the following {language} code.
Use {doc_style} style for docstrings and documentation.

Code to document:
```{language}
{code}
```

Please provide documentation in the following JSON format:
{{
    "overview": "<brief overview of what the code does>",
    "documented_code": "<the original code with added docstrings and comments>",
    "api_documentation": {{
        "functions": [
            {{
                "name": "<function_name>",
                "description": "<what the function does>",
                "parameters": [
                    {{
                        "name": "<param_name>",
                        "type": "<param_type>",
                        "description": "<param_description>",
                        "required": <true/false>
                    }}
                ],
                "returns": {{
                    "type": "<return_type>",
                    "description": "<return_description>"
                }},
                "raises": ["<list of exceptions that might be raised>"],
                "examples": ["<usage examples>"]
            }}
        ],
        "classes": [
            {{
                "name": "<class_name>",
                "description": "<what the class does>",
                "attributes": ["<list of important attributes>"],
                "methods": ["<list of important methods>"]
            }}
        ]
    }},
    "usage_examples": ["<practical usage examples>"],
    "notes": ["<additional notes or considerations>"]
}}

Respond only with valid JSON, no additional text.
"""

            # Execute documentation generation with Grok
            response = llm.invoke([{"role": "user", "content": prompt_text}])

            # Parse JSON response
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    return {"error": f"Failed to parse {self.config.provider.value} response as JSON", "raw_response": response}
            
            return {
                "tool": "ai_documentation_generator",
                "language": language,
                "doc_style": doc_style,
                "documentation": result
            }
            
        except Exception as e:
            return {"error": f"Documentation generation failed: {str(e)}"}


class RefactoringSuggestionTool(BaseTool):
    """AI tool for suggesting code refactoring improvements with multiple provider support."""

    name: str = "ai_refactoring_suggestions"
    description: str = """
    Analyze code and suggest refactoring improvements using configurable AI providers including:
    - Code structure improvements
    - Design pattern applications
    - Performance optimizations
    - Maintainability enhancements

    Input should be a JSON object with:
    - code: The code to analyze for refactoring
    - language: Programming language (optional, defaults to Python)
    - focus_areas: Specific areas to focus on (optional)
    """

    config: AIConfig = Field(default_factory=get_ai_config)
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Generate refactoring suggestions using configurable AI provider."""
        try:
            import json
            params = json.loads(query)

            code = params.get("code", "")
            language = params.get("language", "Python")
            focus_areas = params.get("focus_areas", [])

            if not code:
                return {"error": "No code provided for refactoring analysis"}

            # Initialize AI LLM
            llm = GenericAILLM(self.config)

            focus_text = f"Focus particularly on: {', '.join(focus_areas)}" if focus_areas else ""

            # Create prompt for Grok
            prompt_text = f"""
You are an expert software architect and refactoring specialist. Analyze the following {language} code and suggest comprehensive refactoring improvements.

{focus_text}

Code to analyze:
```{language}
{code}
```

Please provide refactoring suggestions in the following JSON format:
{{
    "refactoring_score": <current code quality score 1-10>,
    "potential_score": <potential score after refactoring 1-10>,
    "priority_suggestions": [
        {{
            "priority": "<HIGH|MEDIUM|LOW>",
            "category": "<category like 'Structure', 'Performance', 'Maintainability'>",
            "current_issue": "<description of current issue>",
            "suggested_improvement": "<detailed refactoring suggestion>",
            "benefits": ["<list of benefits>"],
            "effort_estimate": "<LOW|MEDIUM|HIGH>"
        }}
    ],
    "design_patterns": ["<applicable design patterns>"],
    "performance_improvements": ["<performance optimization suggestions>"],
    "maintainability_improvements": ["<maintainability suggestions>"]
}}

Respond only with valid JSON, no additional text.
"""

            # Execute refactoring analysis with Grok
            response = llm.invoke([{"role": "user", "content": prompt_text}])

            # Parse JSON response
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    return {"error": f"Failed to parse {self.config.provider.value} response as JSON", "raw_response": response}

            return {
                "tool": "ai_refactoring_suggestions",
                "language": language,
                "focus_areas": focus_areas,
                "suggestions": result
            }

        except Exception as e:
            return {"error": f"Refactoring analysis failed: {str(e)}"}

class AITestGeneratorTool(BaseTool):
    """AI tool for generating unit tests with multiple provider support."""

    name: str = "ai_test_generator"
    description: str = """
    Generate comprehensive unit tests for code using configurable AI providers including:
    - Test cases for different scenarios
    - Edge case testing
    - Mock usage where appropriate
    - Test documentation

    Input should be a JSON object with:
    - code: The code to generate tests for
    - language: Programming language (optional, defaults to Python)
    - test_framework: Testing framework to use (pytest, unittest, etc.)
    """

    config: AIConfig = Field(default_factory=get_ai_config)

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Generate unit tests for code using configurable AI provider."""
        try:
            import json
            params = json.loads(query)

            code = params.get("code", "")
            language = params.get("language", "Python")
            test_framework = params.get("test_framework", "pytest")

            if not code:
                return {"error": "No code provided for test generation"}

            # Initialize AI LLM
            llm = GenericAILLM(self.config)

            # Create prompt for Grok
            prompt_text = f"""
You are an expert test engineer. Generate comprehensive unit tests for the following {language} code using {test_framework} framework.

Code to test:
```{language}
{code}
```

Please provide test generation results in the following JSON format:
{{
    "test_code": "<complete test code with all test cases>",
    "test_cases": [
        {{
            "test_name": "<test function name>",
            "description": "<what this test verifies>",
            "test_type": "<unit|integration|edge_case>",
            "coverage_area": "<what part of code it covers>"
        }}
    ],
    "coverage_analysis": {{
        "estimated_coverage": "<percentage estimate>",
        "covered_functions": ["<list of functions covered>"],
        "uncovered_areas": ["<areas that might need additional tests>"]
    }},
    "setup_requirements": ["<any setup or dependencies needed>"],
    "edge_cases": ["<list of edge cases covered>"],
    "additional_test_suggestions": ["<suggestions for additional tests>"]
}}

Respond only with valid JSON, no additional text.
"""

            # Execute test generation with Grok
            response = llm.invoke([{"role": "user", "content": prompt_text}])

            # Parse JSON response
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    return {"error": f"Failed to parse {self.config.provider.value} response as JSON", "raw_response": response}

            return {
                "tool": "ai_test_generator",
                "language": language,
                "test_framework": test_framework,
                "tests": result
            }

        except Exception as e:
            return {"error": f"Test generation failed: {str(e)}"}


# Tool instances for easy import
code_review_tool = CodeReviewTool()
documentation_generator_tool = DocumentationGeneratorTool()
refactoring_suggestion_tool = RefactoringSuggestionTool()
test_generator_tool = AITestGeneratorTool()

# List of all AI analysis tools
AI_ANALYSIS_TOOLS = [
    code_review_tool,
    documentation_generator_tool,
    refactoring_suggestion_tool,
    test_generator_tool
]
