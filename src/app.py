"""Gradio chat UI (Hebrew, RTL).

Stage 3: the UI calls the Actor directly. In stage 5 the call is replaced by
the Actor -> Critic -> revision loop.

Run from the project root:  python -m src.app
"""
from __future__ import annotations

import gradio as gr

from src import config
from src.actor import History, generate
from src.background import load_background

BACKGROUND = load_background()

CSS = """
.gradio-container { direction: rtl; }
textarea { direction: rtl; text-align: right; }
"""


def answer_question(question: str, history: History) -> str:
    """Produce the final answer shown to the user (stage 3: Actor only)."""
    return generate(question, history, background=BACKGROUND)


def on_submit(message: str, history: History):
    """Handle one user message.

    `history` is kept in gr.State as plain {"role", "content"} dicts and holds
    only user messages and final answers. It is the history sent to the model.
    """
    message = (message or "").strip()
    if not message:
        return "", history, history

    try:
        reply = answer_question(message, history)
    except Exception as exc:  # stage 5 replaces this with the loop's error handling
        reply = f"⚠️ אירעה שגיאה טכנית ולא התקבלה תשובה. ({type(exc).__name__})"

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
            f"<small>מודל: {config.ACTOR_MODEL}</small>",
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
