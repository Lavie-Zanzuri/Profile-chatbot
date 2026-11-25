"""The Critic: evaluates a candidate answer and returns a validated Evaluation.

The model is asked for JSON that matches EVALUATION_JSON_SCHEMA, and the raw
text is then validated with Pydantic. Any failure (API error, empty output,
invalid JSON, missing field, wrong type) raises EvaluationError. A failure is
never treated as an approval.
"""
from __future__ import annotations

from openai import OpenAI
from pydantic import ValidationError

from src import config
from src.actor import History
from src.background import load_background
from src.evaluation import EVALUATION_JSON_SCHEMA, Evaluation

CRITIC_PROMPT_FILE = config.PROMPTS_DIR / "critic_system.txt"

# How many previous messages (user + assistant) the Critic sees.
RELEVANT_HISTORY_MESSAGES = 6


class EvaluationError(Exception):
    """The evaluation could not be completed (technical failure, not a content decision)."""


def format_history(history: History) -> str:
    recent = history[-RELEVANT_HISTORY_MESSAGES:]
    if not recent:
        return "(no previous messages)"
    names = {"user": "User", "assistant": "Assistant"}
    return "\n".join(f"{names.get(m['role'], m['role'])}: {m['content']}" for m in recent)


def build_user_evaluator(
    question: str, candidate: str, history: History, background: str
) -> str:
    """The User Evaluator message: everything the Critic needs to judge the answer."""
    return (
        "## Background sources\n"
        f"{background}\n\n"
        "## Relevant conversation history\n"
        f"{format_history(history)}\n\n"
        "## Current user question\n"
        f"{question}\n\n"
        "## Candidate answer to evaluate\n"
        f"{candidate}\n\n"
        "Evaluate the candidate answer according to the criteria and return the result."
    )


def parse_evaluation(raw: str) -> Evaluation:
    """Validate the raw model output against the Evaluation schema."""
    if not raw or not raw.strip():
        raise EvaluationError("Critic returned empty output")
    try:
        return Evaluation.model_validate_json(raw)
    except ValidationError as exc:
        raise EvaluationError(f"Critic output failed validation: {exc.errors()}") from exc


def evaluate(
    question: str,
    candidate: str,
    history: History,
    *,
    client: OpenAI | None = None,
    background: str | None = None,
    model: str | None = None,
) -> Evaluation:
    """Return a validated Evaluation, or raise EvaluationError."""
    background = background if background is not None else load_background()
    try:
        client = client or OpenAI(api_key=config.require_api_key())
        response = client.responses.create(
            model=model or config.CRITIC_MODEL,
            instructions=CRITIC_PROMPT_FILE.read_text(encoding="utf-8").strip(),
            input=build_user_evaluator(question, candidate, history, background),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "Evaluation",
                    "schema": EVALUATION_JSON_SCHEMA,
                    "strict": True,
                }
            },
        )
        raw = response.output_text
    except EvaluationError:
        raise
    except Exception as exc:  # API / network errors
        raise EvaluationError(f"Critic call failed: {type(exc).__name__}: {exc}") from exc

    return parse_evaluation(raw)
