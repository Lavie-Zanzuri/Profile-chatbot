"""Gradio chat UI (Hebrew, RTL).

Every question goes through the Actor -> Critic -> revision loop (src/loop.py).
Only the user messages and the final message of each question are shown and
kept in the conversation history; drafts and feedback go to the audit log.

Run from the project root:  python -m src.app
"""
from __future__ import annotations

import gradio as gr

from src import config
from src.actor import History
from src.background import load_background
from src.loop import QuestionResult, handle_question

BACKGROUND = load_background()

CSS = """
.gradio-container { direction: rtl; }
textarea { direction: rtl; text-align: right; }
"""


def answer_question(question: str, history: History) -> QuestionResult:
    """Run the full loop for one question."""
    result = handle_question(question, history, background=BACKGROUND)
    # Console trace until the audit log is added in stage 6
    print(f"[{result.status}] {question!r} -> {len(result.attempts)} attempt(s)")
    for a in result.attempts:
        print(f"   #{a.attempt} acceptable={a.is_acceptable} feedback={a.feedback} error={a.error}")
    return result


def on_submit(message: str, history: History):
    """Handle one user message.

    `history` is kept in gr.State as plain {"role", "content"} dicts and holds
    only user messages and final answers. It is the history sent to the model.
    """
    message = (message or "").strip()
    if not message:
        return "", history, history

    reply = answer_question(message, history).message

    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ]
    return "", history, history


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Lavie Zanzuri – Profile Chat") as demo:
        gr.Markdown(
            "## צ'אט עם לביא זנזורי\n"
            "שאלו על לימודים, ניסיון, מיומנויות או פרויקטים. "
            f"התשובות מבוססות על פרופיל ה-LinkedIn ועל סיכום אישי בלבד.  \n"
            f"<small>Actor: {config.ACTOR_MODEL} · Critic: {config.CRITIC_MODEL}</small>",
            rtl=True,
        )
        history_state = gr.State([])
        chatbot = gr.Chatbot(label="שיחה", rtl=True, height=480)
        with gr.Row():
            textbox = gr.Textbox(
                placeholder="כתבו שאלה ולחצו Enter...",
                show_label=False,
                scale=5,
                rtl=True,
            )
            send_btn = gr.Button("שליחה", variant="primary", scale=1)
        clear_btn = gr.Button("שיחה חדשה")

        outputs = [textbox, chatbot, history_state]
        textbox.submit(on_submit, [textbox, history_state], outputs)
        send_btn.click(on_submit, [textbox, history_state], outputs)
        clear_btn.click(lambda: ("", [], []), None, outputs)
    return demo


if __name__ == "__main__":
    build_ui().launch(css=CSS)
