"""Simple API tests with mocked dependencies to isolate hanging issues."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import time

# Create a simple test API without complex dependencies
def create_test_app():
    """Create a simple test FastAPI app."""
    app = FastAPI(title="Test API", version="1.0.0")
    
    @app.get("/health")
    async def simple_health():
        return {"status": "healthy", "timestamp": time.time()}
    
    @app.get("/")
    async def root():
        return {"message": "Test API", "version": "1.0.0"}
    
    return app


@pytest.mark.integration
def test_simple_api():
    """Test a simple API without complex dependencies."""
    app = create_test_app()
    client = TestClient(app)
    
    # Test health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✅ Simple health endpoint works")
    
    # Test root endpoint
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Test API"
    print("✅ Simple root endpoint works")


@pytest.mark.integration
def test_api_with_mocked_monitoring():
    """Test the actual API with mocked monitoring system."""
    
    # Mock all the problematic dependencies
    with patch('monitoring.monitoring') as mock_monitoring, \
         patch('error_tracking.error_tracker') as mock_error_tracker, \
         patch('logging_config.initialize_logging') as mock_init_logging, \
         patch('logging_config.get_logger') as mock_get_logger:
        
        # Setup mocks
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        mock_monitoring.get_health_status.return_value = {
            "status": "healthy",
            "error_rate": 0.0,
            "uptime_seconds": 100,
            "total_requests": 10,
            "active_requests": 0
        }
        
        # Import API after mocking
        from api import app
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/health")
        print(f"Health endpoint status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            print("✅ Health endpoint with mocked monitoring works")
        else:
            print(f"❌ Health endpoint failed with status {response.status_code}")
            print(f"Response: {response.text}")


@pytest.mark.integration
def test_api_middleware_isolation():
    """Test if the middleware is causing the hang."""
    
    with patch('monitoring.monitoring') as mock_monitoring, \
         patch('error_tracking.error_tracker') as mock_error_tracker:
        
        # Mock the monitoring system to avoid locks
        mock_monitoring.system_metrics = Mock()
        mock_monitoring.system_metrics.active_requests = 0
        mock_monitoring.system_metrics.peak_active_requests = 0
        mock_monitoring.record_api_request = Mock()
        mock_monitoring.get_health_status.return_value = {
            "status": "healthy",
            "error_rate": 0.0,
            "uptime_seconds": 100,
            "total_requests": 10,
            "active_requests": 0
        }
        
        # Import and test
        from api import app
        client = TestClient(app)
        
        print("Testing with mocked middleware...")
        response = client.get("/health")
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API works with mocked middleware")
        else:
            print(f"❌ API still fails: {response.text}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
