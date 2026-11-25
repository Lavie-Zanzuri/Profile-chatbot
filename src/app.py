"""Gradio chat UI (Hebrew, RTL).

Every question goes through the Actor -> Critic -> revision loop (src/loop.py).
Only the user messages and the final message of each question are shown and
kept in the conversation history; drafts and feedback go to the audit log
(a JSON file in logs/ and a separate panel in the UI).

Run from the project root:  python -m src.app
"""
from __future__ import annotations

import gradio as gr

from src import config
from src.actor import History
from src.audit_log import AuditLog
from src.background import load_background
from src.loop import QuestionResult, handle_question

BACKGROUND = load_background()
AUDIT_LOG = AuditLog()  # one file per app run: logs/session_<timestamp>.json

CSS = """
.gradio-container { direction: rtl; }
textarea { direction: rtl; text-align: right; }
"""

STATUS_LABELS = {
    "approved": "✅ אושרה",
    "max_attempts": "⛔ מיצוי ניסיונות",
    "technical_error": "⚠️ שגיאה טכנית",
}


def answer_question(question: str, history: History) -> QuestionResult:
    """Run the full loop for one question and record it in the audit log."""
    scenario_id = f"ui-{len(AUDIT_LOG.records) + 1}"
    result = handle_question(question, history, background=BACKGROUND, scenario_id=scenario_id)
    AUDIT_LOG.record(result, critic="llm", source="ui")
    print(f"[{result.status}] {question!r} -> {len(result.attempts)} attempt(s). Log: {AUDIT_LOG.path}")
    return result


def audit_summary() -> str:
    """Short table of the session for the audit panel."""
    if not AUDIT_LOG.records:
        return "עדיין אין שאלות ביומן."
    rows = ["| # | שאלה | מצב סיום | ניסיונות |", "|---|---|---|---|"]
    for r in AUDIT_LOG.records:
        q = r["question"].replace("|", "/")
        rows.append(f"| {r['scenario_id']} | {q} | {STATUS_LABELS.get(r['status'], r['status'])} | {r['num_attempts']} |")
    return "\n".join(rows) + f"\n\nקובץ היומן: `{AUDIT_LOG.path.name}` (בתיקייה logs)"


def on_submit(message: str, history: History):
    """Handle one user message.

    `history` is kept in gr.State as plain {"role", "content"} dicts and holds
    only user messages and final messages. It is the history sent to the model.
    """
    message = (message or "").strip()
    if not message:
        return "", history, history, audit_summary(), AUDIT_LOG.records

    reply = answer_question(message, history).message
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ]
    return "", history, history, audit_summary(), AUDIT_LOG.records


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Lavie Zanzuri – Profile Chat") as demo:
        gr.Markdown(
            "## צ'אט עם לביא זנזורי\n"
            "שאלו על לימודים, ניסיון, מיומנויות או פרויקטים. "
            "התשובות מבוססות על פרופיל ה-LinkedIn ועל סיכום אישי בלבד.  \n"
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

        with gr.Accordion("יומן בדיקה (טיוטות, החלטות ומשוב)", open=False):
            summary_md = gr.Markdown(audit_summary(), rtl=True)
            log_json = gr.JSON(label="רשומות מלאות", value=[])

        outputs = [textbox, chatbot, history_state, summary_md, log_json]
        textbox.submit(on_submit, [textbox, history_state], outputs)
        send_btn.click(on_submit, [textbox, history_state], outputs)
        # A new conversation clears the chat; the audit log of the session is kept.
        clear_btn.click(lambda: ("", [], []), None, [textbox, chatbot, history_state])
    return demo


if __name__ == "__main__":
    build_ui().launch(css=CSS)
