#!/usr/bin/env python3
# src/hh_client.py
# Core OAuth + HH API helpers.

import json, time, os
import logging
import requests
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List

LOG = logging.getLogger("hh_client")
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": os.getenv("HH_USER_AGENT", "my-hh-bot/1.0")})

# Config (read from env or use defaults)
CLIENT_ID = os.getenv("HH_CLIENT_ID")
CLIENT_SECRET = os.getenv("HH_CLIENT_SECRET")
REDIRECT_URI = os.getenv("HH_REDIRECT_URI", "http://localhost:5000/callback")
TOKENS_PATH = Path(os.getenv("HH_TOKENS_PATH", Path.home() / ".config" / "hh-bot" / "tokens.json"))
TOKEN_URL = "https://api.hh.ru/token"
AUTH_BASE = "https://hh.kz/oauth/authorize"  # user-facing auth page
PREFIX = "https://"


def ensure_token_dir() -> None:
    TOKENS_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        TOKENS_PATH.chmod(0o600)
    except OSError:
        pass


def auth_url(state: str, scope: str = "resume:read resume:edit") -> str:
    q = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": scope,
        "state": state,
    }
    return AUTH_BASE + "?" + "&".join(f"{k}={requests.utils.requote_uri(v)}" for k, v in q.items())


def save_tokens(tokens: Dict) -> None:
    ensure_token_dir()
    tokens = dict(tokens)
    tokens["obtained_at"] = int(time.time())
    TOKENS_PATH.write_text(json.dumps(tokens, indent=2))
    TOKENS_PATH.chmod(0o600)
    LOG.info("Saved tokens to %s", TOKENS_PATH)


def load_tokens() -> Optional[Dict]:
    if not TOKENS_PATH.exists():
        return None
    try:
        return json.loads(TOKENS_PATH.read_text())
    except json.JSONDecodeError:
        LOG.warning("Could not decode tokens file.  Deleting it.")
        TOKENS_PATH.unlink(missing_ok=True)
        return None


def exchange_code_for_token(code: str) -> Dict:
    """Exchange authorization code for tokens (authorization_code grant)."""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    }
    r = _SESSION.post(TOKEN_URL, data=data, timeout=10)
    r.raise_for_status()
    tokens = r.json()
    save_tokens(tokens)
    return tokens


def refresh_with_refresh_token(refresh_token: str) -> Dict:
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    r = _SESSION.post(TOKEN_URL, data=data, timeout=10)
    r.raise_for_status()
    tokens = r.json()
    save_tokens(tokens)
    return tokens


def _needs_refresh(tokens: Dict, margin: int = 60) -> bool:
    expires_in = int(tokens.get("expires_in", 0))
    obtained = int(tokens.get("obtained_at", int(time.time())))
    return time.time() > (obtained + expires_in - margin)


def get_valid_access_token() -> str:
    """
    Return an access_token. If missing, raises. If expired or near expiry, refreshes automatically.
    """
    tokens = load_tokens()
    if not tokens:
        LOG.info("No tokens found. Launching app.py...")
        try:
            subprocess.Popen(["python", "app.py"])
        except FileNotFoundError:
            raise RuntimeError("app.py not found.  Ensure it's in the correct directory.")

        # Wait up to 60 seconds for tokens to be saved
        timeout = 60
        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(1)  # Poll every second
            tokens = load_tokens()
            if tokens:
                break
        else:
            raise RuntimeError("Failed to obtain tokens after launching app.py. Please check app.py and authorization flow.")

    if _needs_refresh(tokens):
        if "refresh_token" not in tokens:
            raise RuntimeError("No refresh_token present; re-authorize.")
        tokens = refresh_with_refresh_token(tokens["refresh_token"])

    return tokens["access_token"]


# -------------------- JSON loader --------------------
def load_resumes_from_json(file_path: str) -> List[dict]:
    try:
        with open(file_path, "r") as f:
            resume_ids = json.load(f)
            if not isinstance(resume_ids, list):
                raise ValueError("resumes.json must contain a list of resume IDs.")
    except FileNotFoundError:
        raise FileNotFoundError(f"Resume IDs file not found: {file_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON format in {file_path}")
    except ValueError as e:
        raise ValueError(str(e))

    return resume_ids


# Simple api helpers:
def api_get(path: str, params: dict = None) -> requests.Response:
    access = get_valid_access_token()
    headers = {"Authorization": f"Bearer {access}"}
    url = path if path.startswith(PREFIX) else f"https://api.hh.ru{path}"
    try:
        r = _SESSION.get(url, headers=headers, params=params, timeout=10)
    except requests.exceptions.RequestException as e:
        LOG.error(f"Request failed: {e}")
        raise  # Re-raise the exception to be handled by the caller

    if r.status_code == 401:
        # try one refresh then retry once
        LOG.info("Got 401 — trying refresh and retry.")
        tokens = load_tokens()
        if tokens and "refresh_token" in tokens:
            refresh_with_refresh_token(tokens["refresh_token"])
            access = get_valid_access_token()
            headers["Authorization"] = f"Bearer {access}"
            r = _SESSION.get(url, headers=headers, params=params, timeout=10)
    r.raise_for_status()
    return r


def api_post(path: str, data=None, json_body=None) -> requests.Response:
    access = get_valid_access_token()
    headers = {"Authorization": f"Bearer {access}"}
    url = path if path.startswith(PREFIX) else f"https://api.hh.ru{path}"
    try:
        r = _SESSION.post(url, headers=headers, data=data, json=json_body, timeout=10)
    except requests.exceptions.RequestException as e:
        LOG.error(f"Request failed: {e}")
        raise

    if r.status_code == 401:
        LOG.info("api_post received 401 — attempting refresh and retry")
        tokens = load_tokens()
        if tokens and "refresh_token" in tokens:
            refresh_with_refresh_token(tokens["refresh_token"])
            access = get_valid_access_token()
            headers["Authorization"] = f"Bearer {access}"
            r = _SESSION.post(url, headers=headers, data=data, json=json_body, timeout=10)
    r.raise_for_status()
    return r


# --- resume helpers (use directly from main.py without explicit token handling) ---

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


# --- time helpers used for "due" logic ---

def iso_to_hours(iso_z: str) -> int:
    """
    Convert an ISO 8601 timestamp (Z or offset) to number of whole hours
    elapsed since that timestamp (in UTC).
    Example input: "2025-11-22T12:34:56Z" or "2025-11-22T12:34:56+03:00"
    """
    dt = datetime.fromisoformat(iso_z.replace("Z", "+00:00")).astimezone(timezone.utc)
    return int((datetime.now(timezone.utc) - dt).total_seconds() // 3600)


def resume_due(resume_json: Dict[str, Any], threshold_hours: int) -> Tuple[bool, int]:
    """
    Return (is_due, hours_since_update).
    `is_due` is True when hours since `updated_at` >= threshold_hours.
    """
    updated = resume_json.get("updated_at")
    if not updated:
        raise ValueError("resume missing 'updated_at'")
    hours = iso_to_hours(updated)
    return hours >= threshold_hours, hours
