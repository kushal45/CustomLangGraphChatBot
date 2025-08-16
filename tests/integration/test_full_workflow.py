import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from nodes import analyze_code_node, generate_report_node
from state import ReviewState, ReviewStatus

@pytest.mark.asyncio
@patch('tools.github_tools.github_file_content_tool._arun')
@patch('tools.ai_analysis_tools.code_review_tool._arun')
async def test_analysis_and_report_nodes(
    mock_ai_review_arun,
    mock_file_content_arun,
):
    """
    Test the analyze_code_node and generate_report_node in integration.
    """
    # 1. Mock tool behaviors
    async def file_content_side_effect(query):
        import json
        params = json.loads(query)
        if params["file_path"] == "main.py":
            return {"content": "print('hello world')"}
        return {"error": "File not found"}
    mock_file_content_arun.side_effect = file_content_side_effect

    async def ai_review_side_effect(query):
        import json
        params = json.loads(query)
        if "code" in params and params["code"]:
             return {
                "review": {
                    "overall_score": 8,
                    "summary": "AI code review looks good.",
                    "issues": [{"severity": "HIGH", "description": "Critical issue found"}]
                }
            }
        else: # This is for the report summary
            return {
                "review": {
                    "overall_score": 10,
                    "summary": "AI summary looks good.",
                    "issues": []
                }
            }
    mock_ai_review_arun.side_effect = ai_review_side_effect

    # 2. Prepare initial state for analyze_code_node
    # This state would be the output of a successful start_review_node
    initial_state = ReviewState(
        repository_url="https://github.com/test/test-repo",
        repository_info={
            "name": "test-repo",
            "language": "Python",
            "files": [ # Corrected key
                {"name": "main.py", "path": "main.py", "type": "file"}
            ],
            "contents": [ # Keep this for the AI analysis part for now
                {"name": "main.py", "path": "main.py", "type": "file"}
            ]
        },
        analysis_results={
            "static_analysis": {
                "summary": {"total_issues": 5}
            }
        },
        status=ReviewStatus.ANALYZING_CODE,
        current_step="analyze_code"
    )

    # 3. Run analyze_code_node
    # We mock the static analysis part as it's tested elsewhere
    with patch('tools.static_analysis_integration.analyze_repository_with_static_analysis', new=AsyncMock(return_value=initial_state)):
        analysis_result_state = await analyze_code_node(initial_state)

    # 4. Assertions for analyze_code_node
    assert "error" not in analysis_result_state, f"analyze_code_node failed with: {analysis_result_state.get('error')}"
    ai_results = analysis_result_state.get("analysis_results", {}).get("ai_analysis", {})
    assert "main.py" in ai_results
    assert ai_results["main.py"]["review"]["overall_score"] == 8
    mock_file_content_arun.assert_called_once()
    assert mock_ai_review_arun.call_count == 1

    # 5. Run generate_report_node
    report_result_state = await generate_report_node(analysis_result_state)

    # 6. Assertions for generate_report_node
    assert report_result_state.get("status") == ReviewStatus.COMPLETED
    assert report_result_state.get("report_generated") is True
    final_report = report_result_state.get("final_report", {})
    assert "summary" in final_report
    assert "AI summary" in final_report["summary"]
    assert "details" in final_report
    assert "static_analysis" in final_report["details"]
    assert "ai_analysis" in final_report["details"]

    # The AI tool is called once for each file, and once for the summary.
    assert mock_ai_review_arun.call_count == 2
