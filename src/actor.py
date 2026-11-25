"""The Actor: generates a candidate answer on Lavie's behalf.

Every call receives the background sources, the conversation history and the
user's question. On a revision it also receives the rejected answer and the
Critic's feedback.
"""
from __future__ import annotations

from openai import OpenAI

from src import config
from src.background import load_background

ACTOR_PROMPT_FILE = config.PROMPTS_DIR / "actor_system.txt"

# History format (same as Gradio "messages"): [{"role": "user"|"assistant", "content": str}, ...]
History = list[dict[str, str]]


def build_instructions(background: str) -> str:
    """System prompt for the Actor: role + rules + background sources."""
    system_prompt = ACTOR_PROMPT_FILE.read_text(encoding="utf-8").strip()
    return f"{system_prompt}\n\n## Background sources\n{background}"


def build_input(
    question: str,
    history: History,
    rejected_answer: str | None = None,
    feedback: str | None = None,
) -> list[dict[str, str]]:
    """Conversation messages sent to the Actor.

    Order: previous turns, then the current question, then (on a revision)
    the rejected draft and the Critic's feedback.
    """
    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": question})

    if rejected_answer is not None:
        messages.append({"role": "assistant", "content": rejected_answer})
        messages.append({
            "role": "user",
            "content": (
                "[REVISION REQUEST]\n"
                "A reviewer rejected your previous answer to the question above.\n\n"
                f"Reviewer feedback:\n{feedback}\n\n"
                "Write a corrected answer to the same question that fixes every issue "
                "in the feedback. Output only the new answer."
            ),
        })
    return messages


def generate(
    question: str,
    history: History,
    rejected_answer: str | None = None,
    feedback: str | None = None,
    *,
    client: OpenAI | None = None,
    background: str | None = None,
    model: str | None = None,
) -> str:
    """Return a candidate answer. Raises on API errors (handled by the loop)."""
    client = client or OpenAI(api_key=config.require_api_key())
    background = background if background is not None else load_background()

    response = client.responses.create(
        model=model or config.ACTOR_MODEL,
        instructions=build_instructions(background),
        input=build_input(question, history, rejected_answer, feedback),
    )
    answer = response.output_text.strip()
    if not answer:
        raise ValueError("Actor returned an empty answer")
    return answer
