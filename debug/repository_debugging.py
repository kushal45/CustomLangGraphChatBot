"""
Enhanced debugging utilities for repository fetching and validation.
Provides comprehensive debugging support for start_review_node.
"""

import json
import pprint
from typing import Dict, Any, List, Optional
from datetime import datetime
from logging_config import get_logger

logger = get_logger(__name__)

class RepositoryDebugger:
    """Comprehensive debugging utilities for repository operations."""
    
    def __init__(self):
        self.debug_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.breakpoint_history = []
        
    def debug_breakpoint(self, step_name: str, state: Dict[str, Any], 
                        context: Optional[Dict[str, Any]] = None) -> None:
        """
        Strategic debugging breakpoint with comprehensive state inspection.
        
        Args:
            step_name: Name of the debugging step
            state: Current state dictionary
            context: Additional context information
        """
        breakpoint_data = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.debug_session_id,
            "step_name": step_name,
            "state_snapshot": self._create_state_snapshot(state),
            "context": context or {}
        }
        
        self.breakpoint_history.append(breakpoint_data)
        
        # Log the breakpoint
        logger.debug(f"🔍 DEBUG BREAKPOINT: {step_name}", extra={
            "debug_session": self.debug_session_id,
            "step": step_name,
            "state_keys": list(state.keys()) if state else [],
            "context": context
        })
        
        # This is where the actual breakpoint occurs
        # Developers can inspect variables in the debugger here
        print(f"\n🔍 DEBUG BREAKPOINT: {step_name}")
        print(f"📊 State Keys: {list(state.keys()) if state else []}")
        if context:
            print(f"🔧 Context: {context}")
        
        # Breakpoint for debugger - developers can step through here
        breakpoint()  # This will pause execution in the debugger
        
    def inspect_repository_url(self, repository_url: str) -> Dict[str, Any]:
        """Inspect and validate repository URL format."""
        inspection = {
            "url": repository_url,
            "is_valid": False,
            "url_type": "unknown",
            "parsed_components": {},
            "validation_errors": []
        }
        
        if not repository_url:
            inspection["validation_errors"].append("URL is empty or None")
            return inspection
            
        # Basic URL validation
        if repository_url.startswith("https://github.com/"):
            inspection["url_type"] = "github_https"
            inspection["is_valid"] = True
            
            # Parse GitHub URL components
            parts = repository_url.replace("https://github.com/", "").split("/")
            if len(parts) >= 2:
                inspection["parsed_components"] = {
                    "owner": parts[0],
                    "repo": parts[1].replace(".git", ""),
                    "full_path": "/".join(parts)
                }
        elif repository_url.startswith("git@github.com:"):
            inspection["url_type"] = "github_ssh"
            inspection["is_valid"] = True
        else:
            inspection["validation_errors"].append("Unsupported URL format")
            
        return inspection
        
    def inspect_github_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect GitHub API response for debugging."""
        inspection = {
            "response_type": "unknown",
            "success": response.get("success", False),
            "has_result": "result" in response,
            "result_structure": {},
            "error_analysis": {},
            "data_quality": {}
        }
        
        if inspection["success"]:
            result = response.get("result", {})
            inspection["result_structure"] = {
                "keys": list(result.keys()),
                "has_file_structure": "file_structure" in result,
                "file_count": len(result.get("file_structure", [])),
                "repo_metadata": {
                    "name": result.get("name"),
                    "language": result.get("language"),
                    "size": result.get("size"),
                    "stars": result.get("stars")
                }
            }
            
            # Analyze data quality
            inspection["data_quality"] = {
                "has_name": bool(result.get("name")),
                "has_language": bool(result.get("language")),
                "has_files": len(result.get("file_structure", [])) > 0,
                "metadata_completeness": sum([
                    bool(result.get("name")),
                    bool(result.get("language")),
                    bool(result.get("size")),
                    len(result.get("file_structure", [])) > 0
                ]) / 4
            }
        else:
            # Analyze error
            inspection["error_analysis"] = {
                "error_message": response.get("error_message"),
                "error_type": self._classify_error(response.get("error_message", "")),
                "has_error_details": "error_details" in response
            }
            
        return inspection
        
    def inspect_repository_info(self, repo_info: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect extracted repository information."""
        inspection = {
            "basic_info": {
                "name": repo_info.get("name"),
                "language": repo_info.get("language"),
                "size": repo_info.get("size"),
                "stars": repo_info.get("stars")
            },
            "file_analysis": {
                "total_files": len(repo_info.get("file_structure", [])),
                "file_extensions": [],
                "directory_structure": {},
                "language_distribution": {}
            },
            "completeness_score": 0.0
        }
        
        # Analyze file structure
        file_structure = repo_info.get("file_structure", [])
        extensions = []
        directories = set()
        
        for file_info in file_structure:
            if "path" in file_info:
                path = file_info["path"]
                
                # Extract directory
                if "/" in path:
                    directories.add(path.split("/")[0])
                    
                # Extract extension
                if "." in path:
                    ext = "." + path.split(".")[-1]
                    extensions.append(ext)
                    
        inspection["file_analysis"]["file_extensions"] = list(set(extensions))
        inspection["file_analysis"]["directory_structure"] = {
            "top_level_dirs": list(directories),
            "total_directories": len(directories)
        }
        
        # Calculate completeness score
        completeness_factors = [
            bool(repo_info.get("name")),
            bool(repo_info.get("language")),
            len(file_structure) > 0,
            len(extensions) > 0
        ]
        inspection["completeness_score"] = sum(completeness_factors) / len(completeness_factors)
        
        return inspection
        
    def _create_state_snapshot(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create a safe snapshot of the state for debugging."""
        snapshot = {}
        
        for key, value in state.items():
            try:
                # Try to serialize to ensure it's JSON-safe
                json.dumps(value)
                snapshot[key] = value
            except (TypeError, ValueError):
                # If not serializable, store type info
                snapshot[key] = f"<{type(value).__name__}>"
                
        return snapshot
        
    def _classify_error(self, error_message: str) -> str:
        """Classify error type for better debugging."""
        error_lower = error_message.lower()
        
        if "rate limit" in error_lower:
            return "rate_limit"
        elif "authentication" in error_lower or "unauthorized" in error_lower:
            return "authentication"
        elif "not found" in error_lower or "404" in error_lower:
            return "not_found"
        elif "network" in error_lower or "connection" in error_lower:
            return "network"
        elif "timeout" in error_lower:
            return "timeout"
        else:
            return "unknown"
            
    def print_debug_summary(self) -> None:
        """Print a comprehensive debug summary."""
        print(f"\n{'='*60}")
        print(f"🔍 DEBUG SESSION SUMMARY: {self.debug_session_id}")
        print(f"{'='*60}")
        print(f"📊 Total Breakpoints: {len(self.breakpoint_history)}")
        
        for i, bp in enumerate(self.breakpoint_history, 1):
            print(f"\n{i}. {bp['step_name']} ({bp['timestamp']})")
            print(f"   State Keys: {list(bp['state_snapshot'].keys())}")
            if bp['context']:
                print(f"   Context: {bp['context']}")
                
        print(f"\n{'='*60}")

# Global debugger instance
repo_debugger = RepositoryDebugger()
