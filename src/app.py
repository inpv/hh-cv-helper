#!/usr/bin/env python3
# app.py

from flask import Flask, redirect, request, session
import secrets, os
from hh_client import auth_url, exchange_code_for_token

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", secrets.token_hex(24))


@app.route("/")
def index():
    return '<a href="/login">Authorize HeadHunter (one-time)</a>'


@app.route("/login")
def login():
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    return redirect(auth_url(state))


@app.route("/callback")
def callback():
    if error := request.args.get("error"):
        return f"Error: {error} {request.args.get('error_description')}", 400
    code = request.args.get("code")
    state = request.args.get("state")
    if not code or state != session.get("oauth_state"):
        return "Missing code or bad state", 400
    try:
        exchange_code_for_token(code)
    except Exception as e:
        return f"Token exchange failed: {e}", 500
    return "OK — tokens saved. You can close this page."


if __name__ == "__main__":
    # For initial use only — bind to localhost
    app.run("localhost", 5000, debug=False)
