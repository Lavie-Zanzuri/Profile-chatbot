"""Stage 4 manual check for the Critic.

Run from the project root:  python -m tests.try_critic

Part 1 (no API): Pydantic validation of good and broken outputs.
Part 2 (API): the Critic judges a good, a fabricated and a "missing info" answer.
"""
from src.critic import EvaluationError, evaluate, parse_evaluation


def part1_validation() -> None:
    print("=== Part 1: schema validation (no API) ===")
    samples = {
        "valid": '{"is_acceptable": true, "feedback": "Supported by the sources."}',
        "missing field": '{"is_acceptable": true}',
        "wrong type": '{"is_acceptable": "yes", "feedback": "ok"}',
        "extra field": '{"is_acceptable": true, "feedback": "ok", "score": 5}',
        "not JSON": "The answer looks good, I approve it.",
        "empty": "",
    }
    for name, raw in samples.items():
        try:
            ev = parse_evaluation(raw)
            print(f"[VALID]   {name}: is_acceptable={ev.is_acceptable}")
        except EvaluationError as exc:
            print(f"[INVALID] {name}: {str(exc)[:90]}")


def part2_critic() -> None:
    print("\n=== Part 2: Critic decisions (API) ===")
    cases = [
        (
            "good answer (expect True)",
            "איפה עשית התמחות?",
            "עשיתי התמחות ב-TracePCB כ-Software Engineer Intern, מיולי עד ספטמבר 2026. "
            "בניתי שם אוטומציות מבוססות AI שחיברו את monday.com API עם Claude Code.",
        ),
        (
            "fabricated fact (expect False)",
            "באילו חברות עבדת?",
            "עבדתי ב-TracePCB כמתמחה, ולפני כן שנתיים כמפתח Backend בחברת Wix.",
        ),
        (
            "honest missing info (expect True)",
            "מה הממוצע שלך בתואר?",
            "אין לי מידע על ממוצע הציונים שלי במקורות שעומדים לרשותי. "
            "אני יכול לספר שאני סטודנט שנה רביעית למדעי המחשב ברייכמן.",
        ),
    ]
    for title, question, candidate in cases:
        try:
            ev = evaluate(question, candidate, history=[])
            print(f"\n[{title}]\n  is_acceptable = {ev.is_acceptable}\n  feedback = {ev.feedback}")
        except EvaluationError as exc:
            print(f"\n[{title}]\n  TECHNICAL ERROR (evaluation not completed): {exc}")


if __name__ == "__main__":
    part1_validation()
    part2_critic()
