from langgraph.graph import StateGraph, END
from state import ReviewState
from nodes import start_review_node, analyze_code_node, generate_report_node, error_handler_node
from logging_config import get_logger

logger = get_logger(__name__)

def should_continue(state: ReviewState) -> str:
    """Determine the next step in the workflow based on state."""
    logger.debug("Evaluating workflow continuation", extra={
        "state_keys": list(state.keys()) if state else [],
        "current_step": state.get("current_step"),
        "has_error": bool(state.get("error_message"))
    })

    if state.get("error_message"):
        logger.info("Routing to error handler due to error message", extra={
            "error_message": state.get("error_message")
        })
        return "error_handler"

    # Placeholder: Add real condition
    logger.debug("Continuing with normal workflow")
    return "continue"

def create_review_workflow() -> StateGraph:
    """Create the review workflow graph."""
    logger.info("Creating review workflow graph")

    try:
        workflow = StateGraph(ReviewState)

        # Add nodes
        logger.debug("Adding workflow nodes")
        workflow.add_node("start_review", start_review_node)
        workflow.add_node("analyze_code", analyze_code_node)
        workflow.add_node("generate_report", generate_report_node)
        workflow.add_node("error_handler", error_handler_node)

        # Set entry point and edges
        logger.debug("Configuring workflow edges")
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

        logger.info("Review workflow graph created successfully", extra={
            "nodes": ["start_review", "analyze_code", "generate_report", "error_handler"],
            "entry_point": "start_review"
        })

        return workflow

    except Exception as e:
        logger.error("Failed to create review workflow graph", extra={
            "error": str(e),
            "error_type": type(e).__name__
        }, exc_info=True)
        raise