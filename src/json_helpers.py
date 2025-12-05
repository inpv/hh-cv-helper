#!/usr/bin/env python3
# src/json_helpers.py

import json
from typing import List


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
