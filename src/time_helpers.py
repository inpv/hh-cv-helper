#!/usr/bin/env python3
# src/time_helpers.py

from typing import Dict, Any, Tuple
from datetime import datetime, timezone


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
