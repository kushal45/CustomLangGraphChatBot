"""Communication and notification tools for LangGraph workflow."""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional
from langchain.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field
import aiohttp
import asyncio
from .logging_utils import log_tool_execution, log_api_call, LoggedBaseTool
from logging_config import get_logger

logger = get_logger(__name__)


class CommunicationConfig(BaseModel):
    """Configuration for communication tools."""
    slack_webhook_url: str = Field(default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL", ""))
    slack_token: str = Field(default_factory=lambda: os.getenv("SLACK_TOKEN", ""))
    email_smtp_server: str = Field(default_factory=lambda: os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com"))
    email_smtp_port: int = Field(default_factory=lambda: int(os.getenv("EMAIL_SMTP_PORT", "587")))
    email_username: str = Field(default_factory=lambda: os.getenv("EMAIL_USERNAME", ""))
    email_password: str = Field(default_factory=lambda: os.getenv("EMAIL_PASSWORD", ""))
    jira_url: str = Field(default_factory=lambda: os.getenv("JIRA_URL", ""))
    jira_username: str = Field(default_factory=lambda: os.getenv("JIRA_USERNAME", ""))
    jira_api_token: str = Field(default_factory=lambda: os.getenv("JIRA_API_TOKEN", ""))


class SlackNotificationTool(BaseTool):
    """Tool for sending Slack notifications."""
    
    name: str = "slack_notification"
    description: str = """
    Send notifications to Slack channels or users.
    
    Input should be a JSON object with:
    - message: The message to send
    - channel: Slack channel or user (optional, uses webhook default)
    - username: Bot username (optional)
    - icon_emoji: Bot emoji icon (optional)
    - attachments: Rich message attachments (optional)
    """
    
    config: CommunicationConfig = Field(default_factory=CommunicationConfig)
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Send Slack notification."""
        return asyncio.run(self._arun(query, run_manager))
    
    async def _arun(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Send Slack notification asynchronously."""
        try:
            params = json.loads(query)
            
            message = params.get("message", "")
            channel = params.get("channel", "")
            username = params.get("username", "Code Review Bot")
            icon_emoji = params.get("icon_emoji", ":robot_face:")
            attachments = params.get("attachments", [])
            
            if not message:
                return {"error": "Message is required"}
            
            if not self.config.slack_webhook_url:
                return {"error": "Slack webhook URL not configured"}
            
            # Prepare payload
            payload = {
                "text": message,
                "username": username,
                "icon_emoji": icon_emoji
            }
            
            if channel:
                payload["channel"] = channel
            
            if attachments:
                payload["attachments"] = attachments
            
            # Send to Slack
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.slack_webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        return {
                            "success": True,
                            "message": "Slack notification sent successfully",
                            "channel": channel or "default"
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"Slack API error: {response.status} - {error_text}"
                        }
                        
        except Exception as e:
            return {"error": f"Failed to send Slack notification: {str(e)}"}


class EmailNotificationTool(BaseTool):
    """Tool for sending email notifications."""
    
    name: str = "email_notification"
    description: str = """
    Send email notifications.
    
    Input should be a JSON object with:
    - to_email: Recipient email address
    - subject: Email subject
    - message: Email message (plain text or HTML)
    - is_html: Whether message is HTML (optional, default: False)
    - cc_emails: List of CC email addresses (optional)
    """
    
    config: CommunicationConfig = Field(default_factory=CommunicationConfig)
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Send email notification."""
        try:
            params = json.loads(query)
            
            to_email = params.get("to_email", "")
            subject = params.get("subject", "")
            message = params.get("message", "")
            is_html = params.get("is_html", False)
            cc_emails = params.get("cc_emails", [])
            
            if not all([to_email, subject, message]):
                return {"error": "to_email, subject, and message are required"}
            
            if not all([self.config.email_username, self.config.email_password]):
                return {"error": "Email credentials not configured"}
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config.email_username
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            
            # Attach message body
            if is_html:
                msg.attach(MIMEText(message, 'html'))
            else:
                msg.attach(MIMEText(message, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.config.email_smtp_server, self.config.email_smtp_port) as server:
                server.starttls()
                server.login(self.config.email_username, self.config.email_password)
                
                recipients = [to_email] + cc_emails
                server.send_message(msg, to_addrs=recipients)
            
            return {
                "success": True,
                "message": "Email sent successfully",
                "to_email": to_email,
                "subject": subject
            }
            
        except Exception as e:
            return {"error": f"Failed to send email: {str(e)}"}


class WebhookTool(BaseTool):
    """Tool for sending webhook notifications."""
    
    name: str = "webhook_notification"
    description: str = """
    Send HTTP webhook notifications to external services.
    
    Input should be a JSON object with:
    - webhook_url: The webhook URL to send to
    - payload: The data to send (JSON object)
    - method: HTTP method (optional, default: POST)
    - headers: Additional headers (optional)
    """
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Send webhook notification."""
        return asyncio.run(self._arun(query, run_manager))
    
    async def _arun(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Send webhook notification asynchronously."""
        try:
            params = json.loads(query)
            
            webhook_url = params.get("webhook_url", "")
            payload = params.get("payload", {})
            method = params.get("method", "POST").upper()
            headers = params.get("headers", {})
            
            if not webhook_url:
                return {"error": "webhook_url is required"}
            
            # Set default headers
            default_headers = {"Content-Type": "application/json"}
            default_headers.update(headers)
            
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    webhook_url,
                    json=payload,
                    headers=default_headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response_text = await response.text()
                    
                    return {
                        "success": response.status < 400,
                        "status_code": response.status,
                        "response": response_text[:500],  # Limit response size
                        "webhook_url": webhook_url,
                        "method": method
                    }
                    
        except Exception as e:
            return {"error": f"Failed to send webhook: {str(e)}"}


class JiraIntegrationTool(BaseTool):
    """Tool for creating and managing Jira issues."""
    
    name: str = "jira_integration"
    description: str = """
    Create and manage Jira issues for code review findings.
    
    Input should be a JSON object with:
    - operation: The operation to perform (create_issue, update_issue, get_issue)
    - project_key: Jira project key
    - issue_data: Issue data (for create/update operations)
    - issue_key: Issue key (for update/get operations)
    """
    
    config: CommunicationConfig = Field(default_factory=CommunicationConfig)
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Perform Jira operations."""
        return asyncio.run(self._arun(query, run_manager))
    
    async def _arun(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Perform Jira operations asynchronously."""
        try:
            params = json.loads(query)
            
            operation = params.get("operation", "")
            project_key = params.get("project_key", "")
            issue_data = params.get("issue_data", {})
            issue_key = params.get("issue_key", "")
            
            if not all([self.config.jira_url, self.config.jira_username, self.config.jira_api_token]):
                return {"error": "Jira configuration not complete"}
            
            # Prepare authentication
            auth = aiohttp.BasicAuth(self.config.jira_username, self.config.jira_api_token)
            headers = {"Content-Type": "application/json"}
            
            async with aiohttp.ClientSession(auth=auth) as session:
                if operation == "create_issue":
                    return await self._create_jira_issue(session, headers, project_key, issue_data)
                elif operation == "update_issue":
                    return await self._update_jira_issue(session, headers, issue_key, issue_data)
                elif operation == "get_issue":
                    return await self._get_jira_issue(session, headers, issue_key)
                else:
                    return {"error": f"Unknown Jira operation: {operation}"}
                    
        except Exception as e:
            return {"error": f"Jira operation failed: {str(e)}"}
    
    async def _create_jira_issue(self, session, headers, project_key, issue_data):
        """Create a new Jira issue."""
        url = f"{self.config.jira_url}/rest/api/2/issue"
        
        # Prepare issue payload
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": issue_data.get("summary", "Code Review Issue"),
                "description": issue_data.get("description", ""),
                "issuetype": {"name": issue_data.get("issue_type", "Bug")},
                "priority": {"name": issue_data.get("priority", "Medium")}
            }
        }
        
        # Add assignee if provided
        if issue_data.get("assignee"):
            payload["fields"]["assignee"] = {"name": issue_data["assignee"]}
        
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status == 201:
                result = await response.json()
                return {
                    "success": True,
                    "issue_key": result.get("key"),
                    "issue_id": result.get("id"),
                    "url": f"{self.config.jira_url}/browse/{result.get('key')}"
                }
            else:
                error_text = await response.text()
                return {"success": False, "error": f"Failed to create issue: {error_text}"}
    
    async def _update_jira_issue(self, session, headers, issue_key, issue_data):
        """Update an existing Jira issue."""
        url = f"{self.config.jira_url}/rest/api/2/issue/{issue_key}"
        
        # Prepare update payload
        payload = {"fields": {}}
        
        if issue_data.get("summary"):
            payload["fields"]["summary"] = issue_data["summary"]
        
        if issue_data.get("description"):
            payload["fields"]["description"] = issue_data["description"]
        
        if issue_data.get("priority"):
            payload["fields"]["priority"] = {"name": issue_data["priority"]}
        
        async with session.put(url, json=payload, headers=headers) as response:
            if response.status == 204:
                return {
                    "success": True,
                    "issue_key": issue_key,
                    "message": "Issue updated successfully"
                }
            else:
                error_text = await response.text()
                return {"success": False, "error": f"Failed to update issue: {error_text}"}
    
    async def _get_jira_issue(self, session, headers, issue_key):
        """Get Jira issue details."""
        url = f"{self.config.jira_url}/rest/api/2/issue/{issue_key}"
        
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                issue = await response.json()
                fields = issue.get("fields", {})
                
                return {
                    "success": True,
                    "issue_key": issue.get("key"),
                    "summary": fields.get("summary"),
                    "description": fields.get("description"),
                    "status": fields.get("status", {}).get("name"),
                    "priority": fields.get("priority", {}).get("name"),
                    "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
                    "created": fields.get("created"),
                    "updated": fields.get("updated")
                }
            else:
                error_text = await response.text()
                return {"success": False, "error": f"Failed to get issue: {error_text}"}


# Tool instances for easy import
slack_notification_tool = SlackNotificationTool()
email_notification_tool = EmailNotificationTool()
webhook_tool = WebhookTool()
jira_integration_tool = JiraIntegrationTool()

# List of all communication tools
COMMUNICATION_TOOLS = [
    slack_notification_tool,
    email_notification_tool,
    webhook_tool,
    jira_integration_tool
]
