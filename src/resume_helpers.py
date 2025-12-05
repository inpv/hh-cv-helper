#!/usr/bin/env python3
# src/resume_helpers.py

import logging
import requests
from typing import Dict, Any, Optional
from api import api_get, api_post

LOG = logging.getLogger("resume_helpers")


def fetch_resume(resume_id: str) -> Dict[str, Any]:
    """
    Fetch a resume by id. Uses api_get so access token handling is automatic.
    Returns parsed JSON as a dict.
    """
    resp = api_get(f"/resumes/{resume_id}")
    return resp.json()


def publish_resume(resume_id: str) -> Dict[str, Any]:
    """
    Call HH API to publish (refresh) the resume's publication date.

    This implements the `POST /resumes/{resume_id}/publish` operation from HH API.
    The function uses api_post() so token handling (refresh) is automatic.

    Returns:
      - Parsed JSON from the API if the response contains JSON, or {} if empty.
    Raises:
      - requests.HTTPError for HTTP error responses (wrapped into RuntimeError with details).
    """
    if not resume_id:
        raise ValueError("resume_id required")

    path = f"/resumes/{resume_id}/publish"

    try:
        # use the library's api_post so get_valid_access_token() is called internally
        resp = api_post(path)
        # Some endpoints return empty body on success; handle both cases.
        if resp.headers.get("Content-Type", "").lower().startswith("application/json") and resp.text:
            return resp.json()
        return {}
    except requests.HTTPError as e:
        # Attach parsed API error body (if present) to make debugging easier.
        resp = e.response
        err_info: Optional[Dict[str, Any]] = None
        if resp is not None:
            try:
                err_info = resp.json()
            except ValueError:
                err_info = {"status": resp.status_code, "body": resp.text}
        # Helpful message for callers
        msg = f"Failed to publish resume {resume_id}: {err_info or str(e)}"
        LOG.exception(msg)
        # Re-raise as RuntimeError to avoid leaking low-level requests objects to the rest of app,
        # but keep original as __cause__ for debugging.
        raise RuntimeError(msg) from e
