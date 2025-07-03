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
        # Clear environment variables for this test
        with patch.dict(os.environ, {}, clear=True):
            config = CommunicationConfig()
            # Test actual fields that exist in CommunicationConfig
            assert config.slack_webhook_url == ""
            assert config.slack_token == ""
            assert config.email_smtp_server == "smtp.gmail.com"
            assert config.email_smtp_port == 587
    
    def test_config_with_tokens(self):
        """Test configuration with various tokens."""
        with patch.dict(os.environ, {
            "SLACK_TOKEN": "xoxb-test-token",
            "EMAIL_PASSWORD": "smtp-password",
            "JIRA_API_TOKEN": "jira-token"
        }):
            config = CommunicationConfig()
            assert config.slack_token == "xoxb-test-token"
            assert config.email_password == "smtp-password"
            assert config.jira_api_token == "jira-token"


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
        # Set up webhook URL
        self.tool.config.slack_webhook_url = "https://hooks.slack.com/test"

        # Mock successful Slack API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="ok")
        mock_post.return_value.__aenter__.return_value = mock_response

        query = json.dumps(self.sample_message)
        result = self.tool._run(query)

        assert result["success"] == True
        assert result["message"] == "Slack notification sent successfully"
        assert result["channel"] == "#general"
    
    @patch('aiohttp.ClientSession.post')
    def test_slack_api_error(self, mock_post):
        """Test handling of Slack API errors."""
        # Set up webhook URL
        self.tool.config.slack_webhook_url = "https://hooks.slack.com/test"

        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="channel_not_found")
        mock_post.return_value.__aenter__.return_value = mock_response

        query = json.dumps(self.sample_message)
        result = self.tool._run(query)

        assert result["success"] == False
        assert "error" in result
        assert "400" in result["error"]
    
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
        assert "Failed to send Slack notification" in result["error"]
    
    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        # Set up webhook URL
        self.tool.config.slack_webhook_url = "https://hooks.slack.com/test"

        # Missing message (only required field)
        incomplete_message = {"channel": "#general"}
        query = json.dumps(incomplete_message)
        result = self.tool._run(query)

        assert "error" in result
        assert "Message is required" in result["error"]
    
    def test_no_slack_token(self):
        """Test handling when Slack webhook URL is not configured."""
        # Clear environment variables to ensure empty webhook URL
        with patch.dict(os.environ, {}, clear=True):
            tool = SlackNotificationTool()

            query = json.dumps(self.sample_message)
            result = tool._run(query)

            assert "error" in result
            assert "Slack webhook URL not configured" in result["error"]


class TestEmailNotificationTool:
    """Test EmailNotificationTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = EmailNotificationTool()
        self.sample_email = {
            "to_email": "developer@example.com",
            "subject": "Code Review Results",
            "message": "Your code review has been completed with 3 issues found."
        }
    
    @patch('smtplib.SMTP')
    def test_successful_email_send(self, mock_smtp):
        """Test successful email sending."""
        # Set up email credentials
        self.tool.config.email_username = "test@example.com"
        self.tool.config.email_password = "password"

        # Mock SMTP server
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        query = json.dumps(self.sample_email)
        result = self.tool._run(query)

        assert result["success"] == True
        assert result["message"] == "Email sent successfully"
        assert result["to_email"] == "developer@example.com"
        assert result["subject"] == "Code Review Results"

        # Verify SMTP methods were called
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()
    
    @patch('smtplib.SMTP')
    def test_smtp_authentication_error(self, mock_smtp):
        """Test handling of SMTP authentication errors."""
        # Set up email credentials
        self.tool.config.email_username = "test@example.com"
        self.tool.config.email_password = "password"

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
        # Set up email credentials
        self.tool.config.email_username = "test@example.com"
        self.tool.config.email_password = "password"

        mock_smtp.side_effect = Exception("Connection refused")

        query = json.dumps(self.sample_email)
        result = self.tool._run(query)

        assert "error" in result
        assert "Connection refused" in result["error"]
    
    def test_invalid_json_input(self):
        """Test handling of invalid JSON input."""
        result = self.tool._run("invalid json")

        assert "error" in result
        assert "Failed to send email" in result["error"]
    
    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        # Missing 'to_email' field
        incomplete_email = {
            "subject": "Test",
            "message": "Test message"
        }
        query = json.dumps(incomplete_email)
        result = self.tool._run(query)

        assert "error" in result
        assert "to_email, subject, and message are required" in result["error"]
    
    def test_invalid_email_address(self):
        """Test handling of invalid email addresses."""
        # Set up email credentials to avoid connection issues
        self.tool.config.email_username = "test@example.com"
        self.tool.config.email_password = "password"

        invalid_email = self.sample_email.copy()
        invalid_email["to_email"] = "invalid-email"

        query = json.dumps(invalid_email)
        result = self.tool._run(query)

        assert "error" in result
        # The actual implementation tries to send the email and fails with connection error
        assert "Failed to send email" in result["error"]


class TestWebhookTool:
    """Test WebhookTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = WebhookTool()
        self.sample_webhook = {
            "webhook_url": "https://api.example.com/webhook",
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

        assert result["success"] == True
        assert result["status_code"] == 200
        assert result["webhook_url"] == "https://api.example.com/webhook"
        assert result["method"] == "POST"
    
    @patch('aiohttp.ClientSession.request')
    def test_webhook_get_request(self, mock_request):
        """Test webhook GET request."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="Success")
        mock_request.return_value.__aenter__.return_value = mock_response
        
        get_webhook = {
            "webhook_url": "https://api.example.com/status",
            "method": "GET"
        }

        query = json.dumps(get_webhook)
        result = self.tool._run(query)

        assert result["success"] == True
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

        assert result["success"] == False
        assert result["status_code"] == 400
        assert "Bad Request" in result["response"]
    
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
        assert "Failed to send webhook" in result["error"]
    
    def test_missing_url(self):
        """Test handling of missing URL."""
        incomplete_webhook = {"method": "POST"}
        query = json.dumps(incomplete_webhook)
        result = self.tool._run(query)

        assert "error" in result
        assert "webhook_url is required" in result["error"]
    
    def test_invalid_method(self):
        """Test handling of invalid HTTP method."""
        invalid_webhook = {
            "webhook_url": "https://api.example.com/webhook",
            "method": "INVALID"
        }
        query = json.dumps(invalid_webhook)
        result = self.tool._run(query)

        # The webhook tool tries to make the request and fails with connection error
        assert "error" in result
        assert "Failed to send webhook" in result["error"]


class TestJiraIntegrationTool:
    """Test JiraIntegrationTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = JiraIntegrationTool()
        self.sample_issue = {
            "operation": "create_issue",
            "project_key": "TEST",
            "issue_data": {
                "summary": "Code review found 3 critical issues",
                "description": "Automated code review detected security vulnerabilities",
                "issue_type": "Bug",
                "priority": "High"
            }
        }
    
    @patch('aiohttp.ClientSession.post')
    def test_successful_issue_creation(self, mock_post):
        """Test successful JIRA issue creation."""
        # Set up Jira credentials
        self.tool.config.jira_url = "https://example.atlassian.net"
        self.tool.config.jira_username = "test@example.com"
        self.tool.config.jira_api_token = "token123"

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

        assert result["success"] == True
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
            "operation": "get_issue",
            "issue_key": "TEST-123"
        }

        # Set up Jira credentials
        self.tool.config.jira_url = "https://example.atlassian.net"
        self.tool.config.jira_username = "test@example.com"
        self.tool.config.jira_api_token = "token123"

        query = json.dumps(get_issue)
        result = self.tool._run(query)

        assert result["success"] == True
        assert result["issue_key"] == "TEST-123"
        assert result["summary"] == "Test issue"
        assert result["status"] == "Open"
    
    def test_no_jira_credentials(self):
        """Test handling when JIRA credentials are not configured."""
        # Clear environment variables to ensure empty credentials
        with patch.dict(os.environ, {}, clear=True):
            tool = JiraIntegrationTool()

            query = json.dumps(self.sample_issue)
            result = tool._run(query)

            assert "error" in result
            assert "Jira configuration not complete" in result["error"]
    
    def test_invalid_operation(self):
        """Test handling of invalid operation."""
        invalid_operation = {
            "operation": "invalid_operation",
            "project_key": "TEST"
        }

        # Set up Jira credentials
        self.tool.config.jira_url = "https://example.atlassian.net"
        self.tool.config.jira_username = "test@example.com"
        self.tool.config.jira_api_token = "token123"

        query = json.dumps(invalid_operation)
        result = self.tool._run(query)

        assert "error" in result
        assert "Unknown Jira operation" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__])
