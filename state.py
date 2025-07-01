from typing import TypedDict, List, Optional, Dict, Any
from langchain_core.messages import BaseMessage

class ReviewState(TypedDict):
    """State for the ReviewState workflow."""
    messages: List[BaseMessage]
    repository_url: str
    analysis_results: Optional[Dict[str, Any]]
    current_step: str
    error_message: Optional[str] 