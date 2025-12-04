#!/usr/bin/env python3
# src/main.py
"""Minimal HH helper bot.
Authenticates via OAuth2, checks for resumes' next available update and publishes them if it's due.
"""

import os
import logging
import argparse
from dotenv import load_dotenv
from typing import Optional
from hh_client import fetch_resume, publish_resume, resume_due, load_resumes_from_json


BASE = "https://api.hh.ru"
DEFAULT_THRESHOLD_HOURS = 4
LOG = logging.getLogger(__name__)


class BooleanAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values.lower() in ("yes", "true", "t", "1"):
            setattr(namespace, self.dest, True)
        elif values.lower() in ("no", "false", "f", "0"):
            setattr(namespace, self.dest, False)
        else:
            raise argparse.ArgumentTypeError(f"Unsupported boolean value: {values}")


# -------------------- CLI --------------------
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--resume-ids", type=str, required=True, help="Path to a JSON file containing a list of resume IDs.")
    p.add_argument("--dry-run", dest="dry_run", action=BooleanAction,
                   type=str,
                   choices=["yes", "no", "true", "false", "t", "f", "1", "0"],
                   help="Toggle dry run. True for dry, False for real write.")
    p.add_argument("--threshold-hours", type=int, default=None, help="Hours threshold for resume update")
    return p.parse_args()


# -------------------- _env helpers --------------------
def _env(k: str, default: Optional[str] = None) -> Optional[str]:
    load_dotenv()
    return os.getenv(k, default)


def _env_int(k: str, default: int) -> int:
    """
    Read integer environment var (or return default).
    Accepts default as int and returns int. Avoids type problems and parsing boilerplate.
    """
    val = os.getenv(k)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        # if env is malformed, fallback to default
        return default


def main():
    args = parse_args()

    dry_env = _env("HH_DRY_RUN", "1")
    if args.dry_run is None:
        dry = dry_env != "0"
    else:
        dry = args.dry_run

    client_id = _env("HH_CLIENT_ID")
    client_secret = _env("HH_CLIENT_SECRET")
    if not all([client_id, client_secret]):
        raise SystemExit("Missing HH credentials in env")

    if args.threshold_hours is not None:
        thr = args.threshold_hours
    else:
        thr = _env_int("HH_UPDATE_THRESHOLD_HOURS", DEFAULT_THRESHOLD_HOURS)

    resumes = load_resumes_from_json(args.resume_ids)
    for resume in resumes:
        try:
            resume_id = resume["id"]
            name = resume["name"]
            resume = fetch_resume(resume_id)
            due, hours = resume_due(resume, thr)
            print(f"resume last updated {hours}h ago; due={due} (resume_id: {resume_id}, name: {name})")

            if due and not dry:
                publish_resume(resume_id)
                print(f"updated_at: {resume.get('updated_at')} (resume_id: {resume_id}), name: {name})")
        except Exception as e:
            print(f"Error processing resume {resume}: {e}")


if __name__ == "__main__":
    main()
