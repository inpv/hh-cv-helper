#!/usr/bin/env python3
# src/auth.py

import json, time, os
import logging
import requests
import subprocess
from pathlib import Path
from typing import Dict, Optional

LOG = logging.getLogger("auth")
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": os.getenv("HH_USER_AGENT", "my-hh-bot/1.0")})

# Config (read from env or use defaults)
CLIENT_ID = os.getenv("HH_CLIENT_ID")
CLIENT_SECRET = os.getenv("HH_CLIENT_SECRET")
REDIRECT_URI = os.getenv("HH_REDIRECT_URI", "http://localhost:5000/callback")
TOKENS_PATH = Path(os.getenv("HH_TOKENS_PATH", Path.home() / ".config" / "hh-bot" / "tokens.json"))
TOKEN_URL = "https://api.hh.ru/token"
AUTH_BASE = "https://hh.kz/oauth/authorize"  # user-facing auth page


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
