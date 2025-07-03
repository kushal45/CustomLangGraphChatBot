"""Basic API integration tests to isolate hanging issues."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

# Test with minimal imports to isolate the issue
@pytest.mark.integration
def test_import_api_module():
    """Test that we can import the API module without hanging."""
    try:
        from api import app
        assert app is not None
        print("✅ API module imported successfully")
    except Exception as e:
        pytest.fail(f"Failed to import API module: {e}")


@pytest.mark.integration  
def test_create_test_client():
    """Test that we can create a TestClient without hanging."""
    try:
        from api import app
        client = TestClient(app)
        assert client is not None
        print("✅ TestClient created successfully")
    except Exception as e:
        pytest.fail(f"Failed to create TestClient: {e}")


@pytest.mark.integration
def test_basic_health_endpoint():
    """Test basic health endpoint without complex mocking."""
    try:
        from api import app
        client = TestClient(app)
        
        # Make a simple request
        response = client.get("/health")
        print(f"✅ Health endpoint responded with status: {response.status_code}")
        
        # Basic assertions
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data
        
    except Exception as e:
        pytest.fail(f"Health endpoint test failed: {e}")


@pytest.mark.integration
def test_root_endpoint():
    """Test root endpoint."""
    try:
        from api import app
        client = TestClient(app)
        
        response = client.get("/")
        print(f"✅ Root endpoint responded with status: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "message" in data
        assert data["message"] == "CustomLangGraphChatBot API"
        
    except Exception as e:
        pytest.fail(f"Root endpoint test failed: {e}")


@pytest.mark.integration
def test_review_endpoint_validation():
    """Test review endpoint validation without workflow execution."""
    try:
        from api import app
        client = TestClient(app)
        
        # Test with missing data
        response = client.post("/review", json={})
        print(f"✅ Review validation responded with status: {response.status_code}")
        
        # Should return validation error
        assert response.status_code == 422
        
    except Exception as e:
        pytest.fail(f"Review validation test failed: {e}")


@pytest.mark.integration
def test_review_endpoint_with_mock():
    """Test review endpoint with proper mocking."""
    try:
        # Mock the workflow before importing the API
        with patch('workflow.create_review_workflow') as mock_workflow:
            mock_workflow_instance = Mock()
            mock_final_state = {
                "analysis_results": {"status": "success"},
                "current_step": "completed",
                "error_message": None
            }
            mock_workflow_instance.arun.return_value = mock_final_state
            mock_workflow.return_value = mock_workflow_instance
            
            from api import app
            client = TestClient(app)
            
            request_data = {"repository_url": "https://github.com/test/repo"}
            response = client.post("/review", json=request_data)
            
            print(f"✅ Review endpoint with mock responded with status: {response.status_code}")
            
            assert response.status_code == 200
            data = response.json()
            assert "report" in data
            
    except Exception as e:
        pytest.fail(f"Review endpoint with mock test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
