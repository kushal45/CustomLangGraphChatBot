"""Fixed API integration tests with proper monitoring mocks."""

import pytest
from unittest.mock import Mock, patch
import sys

# Mock the monitoring system BEFORE any imports
def setup_monitoring_mocks():
    """Set up monitoring mocks before importing API."""
    # Create proper mocks
    mock_monitoring = Mock()
    mock_error_tracker = Mock()
    
    # Create a proper mock for system_metrics with numeric values
    mock_system_metrics = Mock()
    mock_system_metrics.active_requests = 0
    mock_system_metrics.peak_active_requests = 0
    mock_system_metrics.total_requests = 0
    mock_system_metrics.total_errors = 0
    mock_system_metrics.unique_clients = set()
    
    mock_monitoring.system_metrics = mock_system_metrics
    mock_monitoring.record_api_request = Mock()
    mock_monitoring.get_health_status.return_value = {
        "status": "healthy",
        "error_rate": 0.0,
        "uptime_seconds": 100,
        "total_requests": 10,
        "active_requests": 0
    }
    mock_monitoring.get_system_metrics_summary.return_value = {
        "total_requests": 10,
        "total_errors": 0,
        "error_rate": 0.0,
        "uptime_seconds": 100,
        "active_requests": 0,
        "peak_active_requests": 5,
        "unique_clients": 3
    }
    mock_monitoring.get_api_metrics_summary.return_value = {}
    mock_monitoring.get_tool_metrics_summary.return_value = {}
    mock_monitoring.get_recent_events.return_value = []
    
    # Mock error tracker
    mock_error_tracker.get_error_summary.return_value = {
        "time_period_hours": 24,
        "total_errors": 0,
        "errors_by_severity": {},
        "errors_by_category": {},
        "top_error_sources": [],
        "error_rate_per_hour": 0.0
    }
    
    # Patch the modules
    sys.modules['monitoring'] = Mock()
    sys.modules['monitoring'].monitoring = mock_monitoring
    sys.modules['error_tracking'] = Mock()
    sys.modules['error_tracking'].error_tracker = mock_error_tracker
    
    return mock_monitoring, mock_error_tracker

# Set up mocks before importing
mock_monitoring, mock_error_tracker = setup_monitoring_mocks()

# Now import the API
from fastapi.testclient import TestClient
from api import app, ReviewRequest


@pytest.mark.integration
class TestAPIFixed:
    """Fixed API integration tests."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_health_endpoint_fixed(self):
        """Test health endpoint with proper mocking."""
        response = self.client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "service" in data
        assert data["service"] == "CustomLangGraphChatBot API"
        print("✅ Health endpoint works with fixed mocking")
    
    def test_root_endpoint_fixed(self):
        """Test root endpoint."""
        response = self.client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["message"] == "CustomLangGraphChatBot API"
        print("✅ Root endpoint works")
    
    def test_review_endpoint_validation_fixed(self):
        """Test review endpoint validation."""
        # Test with missing data
        response = self.client.post("/review", json={})
        assert response.status_code == 422
        print("✅ Review endpoint validation works")
    
    def test_review_endpoint_with_mock_workflow(self):
        """Test review endpoint with mocked workflow."""
        from unittest.mock import AsyncMock

        with patch('api.create_review_workflow') as mock_workflow:
            # Create proper mock chain for async workflow
            mock_workflow_graph = Mock()
            mock_compiled_workflow = AsyncMock()

            # Mock final state with proper analysis_results structure
            mock_final_state = {
                "analysis_results": {
                    "static_analysis": {},
                    "ai_analysis": {},
                    "security_analysis": {},
                    "complexity_analysis": None,
                    "overall_score": 8.5,
                    "summary": "Test analysis completed",
                    "recommendations": ["Add more tests"]
                },
                "current_step": "completed",
                "error_message": None
            }

            mock_compiled_workflow.ainvoke.return_value = mock_final_state
            mock_workflow_graph.compile.return_value = mock_compiled_workflow
            mock_workflow.return_value = mock_workflow_graph

            request_data = {"repository_url": "https://github.com/test/repo"}
            response = self.client.post("/review", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert "report" in data
            assert data["report"]["overall_score"] == 8.5
            print("✅ Review endpoint with workflow mock works")
    
    def test_metrics_endpoint_fixed(self):
        """Test metrics endpoint."""
        response = self.client.get("/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "system" in data
        assert "api" in data
        assert "tools" in data
        print("✅ Metrics endpoint works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
