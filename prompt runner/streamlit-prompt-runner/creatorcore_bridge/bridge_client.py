"""
CreatorCore Bridge Client

This module provides a unified client for communicating with CreatorCore services
as part of the backend alignment sprint integration.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests
from requests.adapters import HTTPAdapter, Retry

logger = logging.getLogger('creatorcore_bridge.bridge_client')

# Local fallback paths
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
BRIDGE_LOGS_PATH = REPORTS_DIR / "creatorcore_bridge_logs.json"


class CreatorCoreBridge:
    """
    Unified bridge client for CreatorCore integration.

    Provides methods to:
    - Send logs to CreatorCore
    - Send feedback to CreatorCore
    - Fetch context for prompt warming
    """

    def __init__(self, base_url: Optional[str] = None, timeout: int = 10):
        """
        Initialize the CreatorCore bridge client.

        Args:
            base_url: Override the default CreatorCore base URL
            timeout: Request timeout in seconds
        """
        default_base = os.environ.get('CREATORCORE_BASE_URL', 'http://localhost:5001')
        self.base_url = base_url or default_base
        self.timeout = timeout
        self._session = self._create_session()
        self.log_endpoint = f"{self.base_url}/core/log"
        self.feedback_endpoint = f"{self.base_url}/core/feedback"
        self.context_endpoint = f"{self.base_url}/core/context"

        logger.info(f"Initialized CreatorCore Bridge with base URL: {self.base_url}")

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()

        # Configure retry strategy
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=('GET', 'POST'),
            raise_on_status=False  # Handle status codes manually
        )

        adapter = HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        return session

    def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        Make an HTTP request with error handling and logging.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            Response data or error information
        """
        try:
            # Set default timeout if not provided
            kwargs.setdefault('timeout', self.timeout)

            logger.debug(f"Making {method} request to {url}")
            response = self._session.request(method, url, **kwargs)

            # Log the request
            self._log_request(method, url, response.status_code, kwargs.get('json'))

            if response.status_code >= 200 and response.status_code < 300:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {"success": True, "raw_response": response.text}
            else:
                error_msg = f"Request failed with status {response.status_code}"
                logger.warning(f"{error_msg}: {response.text}")
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": response.status_code,
                    "response": response.text
                }

        except requests.RequestException as e:
            error_msg = f"Request exception: {str(e)}"
            logger.warning(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "exception_type": type(e).__name__
            }

    def _log_request(self, method: str, url: str, status_code: int, payload: Any = None) -> None:
        """Log bridge requests for debugging and monitoring."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "method": method,
            "url": url,
            "status_code": status_code,
            "payload": payload
        }

        try:
            # Append to local log file
            if BRIDGE_LOGS_PATH.exists():
                with open(BRIDGE_LOGS_PATH, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            else:
                logs = []

            logs.append(log_entry)

            with open(BRIDGE_LOGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to log bridge request: {e}")

    def send_log(self, case_id: str, prompt: str, output: Dict[str, Any],
                 metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a prompt and output log to CreatorCore.

        Args:
            case_id: Unique identifier for the case/session
            prompt: The original user prompt
            output: The generated output/response
            metadata: Additional metadata (city, model, etc.)

        Returns:
            Response from CreatorCore or error information
        """
        payload = {
            "case_id": case_id,
            "event": "prompt_processed",
            "prompt": prompt,
            "output": output,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        if metadata:
            payload["metadata"] = metadata

        response = self._make_request("POST", self.log_endpoint, json=payload)

        if response.get("success"):
            logger.info(f"Successfully sent log for case {case_id} to CreatorCore")
        else:
            logger.warning(f"Failed to send log for case {case_id}: {response.get('error')}")

        return response

    def send_feedback(self, case_id: str, feedback: Union[int, str],
                     prompt: Optional[str] = None, output: Optional[Dict[str, Any]] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send user feedback to CreatorCore.

        Args:
            case_id: Unique identifier for the case/session
            feedback: Feedback value (1 for positive, -1 for negative, or "up"/"down")
            prompt: Original prompt (optional, for context)
            output: Original output (optional, for context)
            metadata: Additional metadata

        Returns:
            Response from CreatorCore or error information
        """
        # Normalize feedback format
        if isinstance(feedback, str):
            if feedback.lower() in ("up", "positive", "good"):
                feedback_value = 1
            elif feedback.lower() in ("down", "negative", "bad"):
                feedback_value = -1
            else:
                logger.warning(f"Unknown feedback string: {feedback}, defaulting to 0")
                feedback_value = 0
        elif isinstance(feedback, int):
            feedback_value = max(-1, min(1, feedback))  # Clamp to -1, 0, 1
        else:
            logger.warning(f"Invalid feedback type: {type(feedback)}, defaulting to 0")
            feedback_value = 0

        payload = {
            "case_id": case_id,
            "feedback": feedback_value,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        # Add optional context
        if prompt:
            payload["prompt"] = prompt
        if output:
            payload["output"] = output
        if metadata:
            payload["metadata"] = metadata

        response = self._make_request("POST", self.feedback_endpoint, json=payload)

        if response.get("success"):
            logger.info(f"Successfully sent feedback ({feedback_value}) for case {case_id}")
        else:
            logger.warning(f"Failed to send feedback for case {case_id}: {response.get('error')}")

        return response

    def get_context(self, user_id: str, limit: int = 3) -> Dict[str, Any]:
        """
        Fetch recent interaction context for prompt warming.

        Args:
            user_id: User identifier to fetch context for
            limit: Number of recent interactions to fetch (default: 3)

        Returns:
            Context data or error information
        """
        params = {"user_id": user_id, "limit": limit}

        response = self._make_request("GET", self.context_endpoint, params=params)

        if response.get("success"):
            context_data = response.get("context", [])
            logger.info(f"Successfully fetched {len(context_data)} context items for user {user_id}")
            return {
                "success": True,
                "user_id": user_id,
                "context": context_data,
                "count": len(context_data)
            }
        else:
            logger.warning(f"Failed to fetch context for user {user_id}: {response.get('error')}")
            return response

    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the CreatorCore bridge connection.

        Returns:
            Health status information
        """
        try:
            # Try to fetch context with a dummy user_id to test connectivity
            response = self._make_request("GET", f"{self.base_url}/core/status", timeout=5)

            return {
                "bridge_connected": response.get("success", False),
                "base_url": self.base_url,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "details": response
            }
        except Exception as e:
            return {
                "bridge_connected": False,
                "base_url": self.base_url,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": str(e)
            }


# Convenience functions for backward compatibility and easy usage
_default_bridge: Optional[CreatorCoreBridge] = None

def get_bridge() -> CreatorCoreBridge:
    """Get or create the default CreatorCore bridge instance."""
    global _default_bridge
    if _default_bridge is None:
        _default_bridge = CreatorCoreBridge()
    return _default_bridge

def log_to_core(case_id: str, prompt: str, output: Dict[str, Any],
               metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience function to log to CreatorCore."""
    return get_bridge().send_log(case_id, prompt, output, metadata)

def send_feedback_to_core(case_id: str, feedback: Union[int, str],
                         prompt: Optional[str] = None, output: Optional[Dict[str, Any]] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience function to send feedback to CreatorCore."""
    return get_bridge().send_feedback(case_id, feedback, prompt, output, metadata)

def get_user_context(user_id: str, limit: int = 3) -> Dict[str, Any]:
    """Convenience function to get user context from CreatorCore."""
    return get_bridge().get_context(user_id, limit)
