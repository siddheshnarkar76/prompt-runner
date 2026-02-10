"""Core Bridge API utilities.

This module provides helpers to communicate with the Core/Bridge service.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import requests
from requests.adapters import HTTPAdapter, Retry

logger = logging.getLogger('core_bridge.core_api')

# Core API configuration - points to MCP server
CORE_API_BASE = os.environ.get('CORE_API_BASE', 'http://localhost:5001')
CORE_LOG_ENDPOINT = f'{CORE_API_BASE}/core/log'
CORE_FEEDBACK_ENDPOINT = f'{CORE_API_BASE}/core/feedback'
CORE_CONTEXT_ENDPOINT = f'{CORE_API_BASE}/core/context'
CORE_STATUS_ENDPOINT = f'{CORE_API_BASE}/system/health'

_session: Optional[requests.Session] = None


def _attach_ids(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize logging payload with run_id, trace_id, timestamp."""
    body = dict(payload or {})
    if not body.get('run_id'):
        body['run_id'] = f"run_{uuid4().hex[:10]}"
    body.setdefault('trace_id', body.get('run_id'))
    body.setdefault('timestamp', datetime.utcnow().isoformat() + 'Z')
    return body


def _build_session() -> requests.Session:
    """Build a requests session with retry logic."""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=('GET', 'POST')
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def _get_session() -> requests.Session:
    """Get or create the global session."""
    global _session
    if _session is None:
        _session = _build_session()
    return _session


def post_run_log(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send a run log payload to the Core bridge.
    
    Args:
        payload: Dictionary containing log data (prompt, output, feedback, etc.)
        
    Returns:
        Response JSON from Core API
        
    Raises:
        requests.RequestException: If the request fails
    """
    session = _get_session()
    body = _attach_ids(payload)
    
    try:
        response = session.post(CORE_LOG_ENDPOINT, json=body, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.warning(f"Failed to post log to Core: {e}")
        # Still append to local log even if Core is unavailable
        append_local_core_log(body)
        raise


def get_core_status() -> Dict[str, Any]:
    """Fetch the Core service health status.
    
    Returns:
        Status dictionary with 'status', 'integration_ready', etc.
        
    Raises:
        requests.RequestException: If the request fails
    """
    session = _get_session()
    try:
        response = session.get(CORE_STATUS_ENDPOINT, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.warning(f"Failed to get Core status from {CORE_STATUS_ENDPOINT}: {e}")
        return {
            'status': 'unavailable',
            'integration_ready': False,
            'error': str(e)
        }


def post_core_feedback(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send feedback to Core API.
    
    Args:
        payload: Dictionary containing feedback data (case_id, feedback, etc.)
        
    Returns:
        Response JSON from Core API
        
    Raises:
        requests.RequestException: If the request fails
    """
    session = _get_session()
    body = _attach_ids(payload)
    
    try:
        response = session.post(CORE_FEEDBACK_ENDPOINT, json=body, timeout=5)
        response.raise_for_status()
        logger.info(f"Successfully posted feedback to Core: {payload.get('case_id')}")
        return response.json()
    except requests.RequestException as e:
        logger.warning(f"Failed to post feedback to Core: {e}")
        # Still append to local log even if Core is unavailable
        append_local_core_log({'type': 'feedback_sync_failed', **body})
        raise


def get_core_context(session_id: str, limit: int = 10) -> Dict[str, Any]:
    """Retrieve historical context from Core API.
    
    Args:
        session_id: Session identifier
        limit: Maximum number of entries to retrieve
        
    Returns:
        Context dictionary with historical entries
    """
    session = _get_session()
    try:
        params = {'session_id': session_id, 'limit': limit}
        response = session.get(CORE_CONTEXT_ENDPOINT, params=params, timeout=5)
        response.raise_for_status()
        logger.info(f"Retrieved context for session {session_id}")
        return response.json()
    except requests.RequestException as e:
        logger.warning(f"Failed to get Core context: {e}")
        return {
            'success': False,
            'session_id': session_id,
            'entries': [],
            'error': str(e)
        }


def append_local_core_log(entry: Dict[str, Any], report_path: str = 'reports/core_sync.json') -> None:
    """Append a log entry to the local core_sync.json file.
    
    Args:
        entry: Log entry dictionary
        report_path: Path to the core_sync.json file
    """
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    data: List[Dict[str, Any]] = []
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, IOError):
            data = []
    
    data.append(_attach_ids(entry))
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    logger.info(f"Logged entry to {report_path}")


def sync_run_log(payload: Dict[str, Any]) -> None:
    """Sync a run log to both Core API and local file.
    
    This is the main function to use for logging user interactions.
    It tries to send to Core, but always saves locally as backup.
    
    Args:
        payload: Dictionary containing log data
    """
    # Always save locally first
    append_local_core_log(payload)
    
    # Try to sync to Core (non-blocking if it fails)
    try:
        post_run_log(payload)
        logger.info("Successfully synced log to Core")
    except requests.RequestException:
        logger.warning("Core sync failed, but log saved locally")
