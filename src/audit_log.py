"""Audit log: one JSON file with a record per user question.

Each record has the scenario id, the question, the final status, the message
shown to the user and every attempt (number, candidate, decision, feedback).
Drafts and feedback live only here, never in the displayed chat history.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src import config
from src.loop import QuestionResult


def attempt_decision(attempt: dict) -> str:
    """Human-readable decision: accepted / rejected / not_completed."""
    if not attempt["evaluation_completed"]:
        return "not_completed"
    return "accepted" if attempt["is_acceptable"] else "rejected"


class AuditLog:
    def __init__(self, path: Path | str | None = None):
        if path is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = config.LOGS_DIR / f"session_{stamp}.json"
        self.path = Path(path)
        self.records: list[dict] = []

    def record(self, result: QuestionResult, **extra) -> dict:
        """Add one question's result and rewrite the JSON file."""
        entry = result.to_dict()
        for attempt in entry["attempts"]:
            attempt["decision"] = attempt_decision(attempt)
        entry["num_attempts"] = len(entry["attempts"])
        entry.update(extra)  # e.g. critic="mock", note="..."
        self.records.append(entry)
        self.save()
        return entry

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        meta = {
            "actor_model": config.ACTOR_MODEL,
            "critic_model": config.CRITIC_MODEL,
            "max_attempts": config.MAX_ATTEMPTS,
        }
        payload = {"meta": meta, "records": self.records}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
