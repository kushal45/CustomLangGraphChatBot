"""Comprehensive unit tests for communication tools."""

import pytest
import json
import os
from unittest.mock import Mock, patch, AsyncMock
from aiohttp import ClientSession

# Import the tools to test
from tools.communication_tools import (
    SlackNotificationTool, EmailNotificationTool, WebhookTool, JiraIntegrationTool,
    CommunicationConfig
)


class TestCommunicationConfig:
    """Test CommunicationConfig configuration class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = CommunicationConfig()
        assert config.timeout == 30
        assert config.max_retries == 3
    
    def test_config_with_tokens(self):
        """Test configuration with various tokens."""
        with patch.dict(os.environ, {
            "SLACK_BOT_TOKEN": "xoxb-test-token",
            "SMTP_PASSWORD": "smtp-password",
            "JIRA_API_TOKEN": "jira-token"
        }):
            config = CommunicationConfig()
            assert config.slack_token == "xoxb-test-token"
            assert config.smtp_password == "smtp-password"
            assert config.jira_token == "jira-token"


class TestSlackNotificationTool:
    """Test SlackNotificationTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = SlackNotificationTool()
        self.sample_message = {
            "channel": "#general",
            "message": "Code review completed successfully!",
            "username": "CodeBot",
            "icon_emoji": ":robot_face:"
        }
    
    @patch('aiohttp.ClientSession.post')
    def test_successful_slack_notification(self, mock_post):
        """Test successful Slack notification."""
        # Mock successful Slack API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ok": True, "ts": "1234567890.123456"})
        mock_post.return_value.__aenter__.return_value = mock_response
        
        query = json.dumps(self.sample_message)
        result = self.tool._run(query)
        
        assert "error" not in result
        assert result["status"] == "success"
        assert result["channel"] == "#general"
        assert "timestamp" in result
    
    @patch('aiohttp.ClientSession.post')
    def test_slack_api_error(self, mock_post):
        """Test handling of Slack API errors."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ok": False, "error": "channel_not_found"})
        mock_post.return_value.__aenter__.return_value = mock_response
        
        query = json.dumps(self.sample_message)
        result = self.tool._run(query)
        
        assert "error" in result
        assert "channel_not_found" in result["error"]
    
    @patch('aiohttp.ClientSession.post')
    def test_slack_network_error(self, mock_post):
        """Test handling of network errors."""
        mock_post.side_effect = Exception("Network error")
        
        query = json.dumps(self.sample_message)
        result = self.tool._run(query)
        
        assert "error" in result
        assert "Network error" in result["error"]
    
    def test_invalid_json_input(self):
        """Test handling of invalid JSON input."""
        result = self.tool._run("invalid json")
        
        assert "error" in result
        assert "Invalid JSON" in result["error"]
    
    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        # Missing channel
        incomplete_message = {"message": "Test message"}
        query = json.dumps(incomplete_message)
        result = self.tool._run(query)
        
        assert "error" in result
        assert "channel" in result["error"]
        
        # Missing message
        incomplete_message = {"channel": "#general"}
        query = json.dumps(incomplete_message)
        result = self.tool._run(query)
        
        assert "error" in result
        assert "message" in result["error"]
    
    def test_no_slack_token(self):
        """Test handling when Slack token is not configured."""
        tool = SlackNotificationTool()
        tool.config.slack_token = ""
        
        query = json.dumps(self.sample_message)
        result = tool._run(query)
        
        assert "error" in result
        assert "Slack token not configured" in result["error"]


class TestEmailNotificationTool:
    """Test EmailNotificationTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = EmailNotificationTool()
        self.sample_email = {
            "to": "developer@example.com",
            "subject": "Code Review Results",
            "body": "Your code review has been completed with 3 issues found.",
            "from": "codebot@example.com"
        }
    
    @patch('smtplib.SMTP')
    def test_successful_email_send(self, mock_smtp):
        """Test successful email sending."""
        # Mock SMTP server
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        query = json.dumps(self.sample_email)
        result = self.tool._run(query)
        
        assert "error" not in result
        assert result["status"] == "success"
        assert result["to"] == "developer@example.com"
        assert result["subject"] == "Code Review Results"
        
        # Verify SMTP methods were called
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()
    
    @patch('smtplib.SMTP')
    def test_smtp_authentication_error(self, mock_smtp):
        """Test handling of SMTP authentication errors."""
        mock_server = Mock()
        mock_server.login.side_effect = Exception("Authentication failed")
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        query = json.dumps(self.sample_email)
        result = self.tool._run(query)
        
        assert "error" in result
        assert "Authentication failed" in result["error"]
    
    @patch('smtplib.SMTP')
    def test_smtp_connection_error(self, mock_smtp):
        """Test handling of SMTP connection errors."""
        mock_smtp.side_effect = Exception("Connection refused")
        
        query = json.dumps(self.sample_email)
        result = self.tool._run(query)
        
        assert "error" in result
        assert "Connection refused" in result["error"]
    
    def test_invalid_json_input(self):
        """Test handling of invalid JSON input."""
        result = self.tool._run("invalid json")
        
        assert "error" in result
        assert "Invalid JSON" in result["error"]
    
    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        # Missing 'to' field
        incomplete_email = {
            "subject": "Test",
            "body": "Test message"
        }
        query = json.dumps(incomplete_email)
        result = self.tool._run(query)
        
        assert "error" in result
        assert "to" in result["error"]
    
    def test_invalid_email_address(self):
        """Test handling of invalid email addresses."""
        invalid_email = self.sample_email.copy()
        invalid_email["to"] = "invalid-email"
        
        query = json.dumps(invalid_email)
        result = self.tool._run(query)
        
        assert "error" in result
        assert "Invalid email address" in result["error"]


class TestWebhookTool:
    """Test WebhookTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = WebhookTool()
        self.sample_webhook = {
            "url": "https://api.example.com/webhook",
            "method": "POST",
            "payload": {
                "event": "code_review_completed",
                "repository": "test/repo",
                "status": "success"
            },
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer token123"
            }
        }
    
    @patch('aiohttp.ClientSession.request')
    def test_successful_webhook_post(self, mock_request):
        """Test successful webhook POST request."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="OK")
        mock_request.return_value.__aenter__.return_value = mock_response
        
        query = json.dumps(self.sample_webhook)
        result = self.tool._run(query)
        
        assert "error" not in result
        assert result["status"] == "success"
        assert result["status_code"] == 200
        assert result["url"] == "https://api.example.com/webhook"
        assert result["method"] == "POST"
    
    @patch('aiohttp.ClientSession.request')
    def test_webhook_get_request(self, mock_request):
        """Test webhook GET request."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="Success")
        mock_request.return_value.__aenter__.return_value = mock_response
        
        get_webhook = {
            "url": "https://api.example.com/status",
            "method": "GET"
        }
        
        query = json.dumps(get_webhook)
        result = self.tool._run(query)
        
        assert "error" not in result
        assert result["method"] == "GET"
        assert result["status_code"] == 200
    
    @patch('aiohttp.ClientSession.request')
    def test_webhook_error_response(self, mock_request):
        """Test handling of webhook error responses."""
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Bad Request")
        mock_request.return_value.__aenter__.return_value = mock_response
        
        query = json.dumps(self.sample_webhook)
        result = self.tool._run(query)
        
        assert "error" in result
        assert "400" in result["error"]
        assert "Bad Request" in result["error"]
    
    @patch('aiohttp.ClientSession.request')
    def test_webhook_network_error(self, mock_request):
        """Test handling of network errors."""
        mock_request.side_effect = Exception("Connection timeout")
        
        query = json.dumps(self.sample_webhook)
        result = self.tool._run(query)
        
        assert "error" in result
        assert "Connection timeout" in result["error"]
    
    def test_invalid_json_input(self):
        """Test handling of invalid JSON input."""
        result = self.tool._run("invalid json")
        
        assert "error" in result
        assert "Invalid JSON" in result["error"]
    
    def test_missing_url(self):
        """Test handling of missing URL."""
        incomplete_webhook = {"method": "POST"}
        query = json.dumps(incomplete_webhook)
        result = self.tool._run(query)
        
        assert "error" in result
        assert "url" in result["error"]
    
    def test_invalid_method(self):
        """Test handling of invalid HTTP method."""
        invalid_webhook = {
            "url": "https://api.example.com/webhook",
            "method": "INVALID"
        }
        query = json.dumps(invalid_webhook)
        result = self.tool._run(query)
        
        assert "error" in result
        assert "Invalid HTTP method" in result["error"]


class TestJiraIntegrationTool:
    """Test JiraIntegrationTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = JiraIntegrationTool()
        self.sample_issue = {
            "action": "create_issue",
            "project_key": "TEST",
            "summary": "Code review found 3 critical issues",
            "description": "Automated code review detected security vulnerabilities",
            "issue_type": "Bug",
            "priority": "High"
        }
    
    @patch('aiohttp.ClientSession.post')
    def test_successful_issue_creation(self, mock_post):
        """Test successful JIRA issue creation."""
        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json = AsyncMock(return_value={
            "id": "12345",
            "key": "TEST-123",
            "self": "https://example.atlassian.net/rest/api/2/issue/12345"
        })
        mock_post.return_value.__aenter__.return_value = mock_response
        
        query = json.dumps(self.sample_issue)
        result = self.tool._run(query)
        
        assert "error" not in result
        assert result["status"] == "success"
        assert result["issue_key"] == "TEST-123"
        assert result["issue_id"] == "12345"
    
    @patch('aiohttp.ClientSession.get')
    def test_successful_issue_retrieval(self, mock_get):
        """Test successful JIRA issue retrieval."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "id": "12345",
            "key": "TEST-123",
            "fields": {
                "summary": "Test issue",
                "status": {"name": "Open"},
                "priority": {"name": "High"}
            }
        })
        mock_get.return_value.__aenter__.return_value = mock_response
        
        get_issue = {
            "action": "get_issue",
            "issue_key": "TEST-123"
        }
        
        query = json.dumps(get_issue)
        result = self.tool._run(query)
        
        assert "error" not in result
        assert result["issue_key"] == "TEST-123"
        assert result["summary"] == "Test issue"
        assert result["status"] == "Open"
    
    def test_no_jira_credentials(self):
        """Test handling when JIRA credentials are not configured."""
        tool = JiraIntegrationTool()
        tool.config.jira_token = ""
        tool.config.jira_email = ""
        
        query = json.dumps(self.sample_issue)
        result = tool._run(query)
        
        assert "error" in result
        assert "JIRA credentials not configured" in result["error"]
    
    def test_invalid_action(self):
        """Test handling of invalid action."""
        invalid_action = {
            "action": "invalid_action",
            "project_key": "TEST"
        }
        
        query = json.dumps(invalid_action)
        result = self.tool._run(query)
        
        assert "error" in result
        assert "Invalid action" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__])
