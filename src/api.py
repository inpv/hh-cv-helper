#!/usr/bin/env python3
# src/api.py

import os
import logging
import requests
from auth import get_valid_access_token, load_tokens, refresh_with_refresh_token

LOG = logging.getLogger("api")
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": os.getenv("HH_USER_AGENT", "my-hh-bot/1.0")})
PREFIX = "https://"



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
