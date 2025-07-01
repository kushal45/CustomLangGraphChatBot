from langgraph.graph import StateGraph, END
from state import ReviewState
from nodes import start_review_node, analyze_code_node, generate_report_node, error_handler_node

def should_continue(state: ReviewState) -> str:
    if state.get("error_message"):
        return "error_handler"
    # Placeholder: Add real condition
    return "continue"

def create_review_workflow() -> StateGraph:
    """Create the review workflow graph."""
    workflow = StateGraph(ReviewState)
    workflow.add_node("start_review", start_review_node)
    workflow.add_node("analyze_code", analyze_code_node)
    workflow.add_node("generate_report", generate_report_node)
    workflow.add_node("error_handler", error_handler_node)

    workflow.set_entry_point("start_review")
    workflow.add_edge("start_review", "analyze_code")
    workflow.add_conditional_edges(
        "analyze_code",
        should_continue,
        {
            'continue': "generate_report",
            'error': "error_handler"
        }
    )
    workflow.add_edge("generate_report", END)
    workflow.add_edge("error_handler", END)
    return workflow 