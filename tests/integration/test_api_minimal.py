"""Minimal API test to identify the exact hanging issue."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.integration
def test_import_monitoring_module():
    """Test importing the monitoring module directly."""
    try:
        import monitoring
        print("✅ Monitoring module imported successfully")
        print(f"Monitoring module: {monitoring}")
        print(f"Monitoring.monitoring: {monitoring.monitoring}")
    except Exception as e:
        print(f"❌ Failed to import monitoring: {e}")
        pytest.fail(f"Failed to import monitoring: {e}")


@pytest.mark.integration
def test_import_error_tracking_module():
    """Test importing the error_tracking module directly."""
    try:
        import error_tracking
        print("✅ Error tracking module imported successfully")
        print(f"Error tracking module: {error_tracking}")
        print(f"Error tracking.error_tracker: {error_tracking.error_tracker}")
    except Exception as e:
        print(f"❌ Failed to import error_tracking: {e}")
        pytest.fail(f"Failed to import error_tracking: {e}")


@pytest.mark.integration
def test_import_logging_config_module():
    """Test importing the logging_config module directly."""
    try:
        import logging_config
        print("✅ Logging config module imported successfully")
        print(f"Logging config module: {logging_config}")
    except Exception as e:
        print(f"❌ Failed to import logging_config: {e}")
        pytest.fail(f"Failed to import logging_config: {e}")


@pytest.mark.integration
def test_create_monitoring_system():
    """Test creating a monitoring system instance."""
    try:
        from monitoring import MonitoringSystem
        monitoring_system = MonitoringSystem()
        print("✅ MonitoringSystem created successfully")
        print(f"System metrics: {monitoring_system.system_metrics}")
    except Exception as e:
        print(f"❌ Failed to create MonitoringSystem: {e}")
        pytest.fail(f"Failed to create MonitoringSystem: {e}")


@pytest.mark.integration
def test_monitoring_health_status():
    """Test getting health status from monitoring system."""
    try:
        from monitoring import monitoring
        health_status = monitoring.get_health_status()
        print("✅ Health status retrieved successfully")
        print(f"Health status: {health_status}")
    except Exception as e:
        print(f"❌ Failed to get health status: {e}")
        pytest.fail(f"Failed to get health status: {e}")


@pytest.mark.integration
def test_fastapi_import():
    """Test importing FastAPI components."""
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        print("✅ FastAPI basic functionality works")
    except Exception as e:
        print(f"❌ FastAPI test failed: {e}")
        pytest.fail(f"FastAPI test failed: {e}")


@pytest.mark.integration
def test_api_import_step_by_step():
    """Test importing API components step by step."""
    try:
        print("Step 1: Importing FastAPI...")
        from fastapi import FastAPI
        print("✅ FastAPI imported")
        
        print("Step 2: Importing Pydantic...")
        from pydantic import BaseModel
        print("✅ Pydantic imported")
        
        print("Step 3: Importing workflow...")
        from workflow import create_review_workflow
        print("✅ Workflow imported")
        
        print("Step 4: Importing state...")
        from state import ReviewState
        print("✅ State imported")
        
        print("Step 5: Importing logging_config...")
        from logging_config import get_logger, initialize_logging
        print("✅ Logging config imported")
        
        print("Step 6: Importing monitoring...")
        from monitoring import monitoring
        print("✅ Monitoring imported")
        
        print("Step 7: Importing error_tracking...")
        from error_tracking import error_tracker
        print("✅ Error tracking imported")
        
        print("All imports successful!")
        
    except Exception as e:
        print(f"❌ Import failed at step: {e}")
        pytest.fail(f"Import failed: {e}")


@pytest.mark.integration
def test_api_import_and_health():
    """Test importing the actual API and calling health endpoint."""
    try:
        print("Importing API...")
        from api import app
        print("✅ API imported successfully")

        print("Creating TestClient...")
        from fastapi.testclient import TestClient
        client = TestClient(app)
        print("✅ TestClient created")

        print("Calling health endpoint...")
        response = client.get("/health")
        print(f"✅ Health endpoint responded with status: {response.status_code}")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        print(f"Health response: {data}")

    except Exception as e:
        print(f"❌ API test failed: {e}")
        pytest.fail(f"API test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
