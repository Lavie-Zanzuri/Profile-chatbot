"""Run the 5 required scenarios and save their logs.

Run from the project root:  python -m tests.run_scenarios
Optional: python -m tests.run_scenarios 4   (run only scenario 4)

Output (logs/scenarios/):
  scenario_<N>.json   full audit log of each scenario (input, attempts, final output)
  summary.md          expected vs. actual for every scenario,
                      LLM results and the mock control-flow test shown separately

Scenarios 1-4 use the real Actor and Critic (language model).
Scenario 4 injects a flawed first draft; the Critic and the revision are real.
Scenario 5 uses a MOCK Critic that always rejects (control-flow test).
"""
from __future__ import annotations

import sys
from datetime import datetime

from src import config
from src.audit_log import AuditLog
from src.background import load_background
from src.loop import APPROVED, MAX_ATTEMPTS, handle_question
from src.mock_critic import always_reject

OUT_DIR = config.LOGS_DIR / "scenarios"
BACKGROUND = load_background()


def turn(question, history, scenario_id, **kwargs):
    """Run one question and return (result, updated displayed history)."""
    result = handle_question(
        question, history, background=BACKGROUND, scenario_id=scenario_id, **kwargs
    )
    history = history + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": result.message},
    ]
    return result, history


# ---------------------------------------------------------------- scenarios
def scenario_1():
    log = AuditLog(OUT_DIR / "scenario_1.json")
    q = "באיזו חברה עשית התמחות ומה עשית שם?"
    r, _ = turn(q, [], "S1")
    log.record(r, critic="llm",
               supporting_source="linkedin.txt, Experience: 'TracePCB – Software Engineer Intern', "
                                 "July 2026 – September 2026, and its 3 bullets")
    ok = r.status == APPROVED and "TracePCB" in r.message
    return log, "Approved answer supported by the profile", ok


def scenario_2():
    log = AuditLog(OUT_DIR / "scenario_2.json")
    r1, history = turn("ספר לי בקצרה על הפרויקט Escape the Query Room", [], "S2-turn1")
    log.record(r1, critic="llm", turn=1)
    r2, _ = turn("באילו טכנולוגיות השתמשת בו?", history, "S2-turn2")
    log.record(r2, critic="llm", turn=2,
               context_check="'בו' must refer to Escape the Query Room (React, Flask, Gemini API)")
    keeps_context = any(t in r2.message for t in ("React", "Flask", "Gemini"))
    ok = r1.status == APPROVED and r2.status == APPROVED and keeps_context
    return log, "Second turn relies on the first answer and keeps the context", ok


def scenario_3():
    log = AuditLog(OUT_DIR / "scenario_3.json")
    q = "מה הממוצע שלך בתואר?"
    r, _ = turn(q, [], "S3")
    log.record(r, critic="llm",
               note="GPA does not appear in linkedin.txt or summary.txt")
    says_missing = any(w in r.message for w in ("אין לי מידע", "אין מידע", "לא מופיע", "אין במקורות"))
    ok = r.status == APPROVED and says_missing
    return log, "States that the information is missing, invents nothing", ok


FLAWED_DRAFT = (
    "עבדתי כמתמחה ב-TracePCB, ולפני כן עבדתי שנתיים כמפתח Backend בחברת Wix, "
    "שם הובלתי צוות של חמישה מפתחים."
)


def scenario_4():
    log = AuditLog(OUT_DIR / "scenario_4.json")
    q = "באילו חברות עבדת?"
    r, _ = turn(q, [], "S4", forced_first_draft=FLAWED_DRAFT)
    log.record(r, critic="llm",
               note="Attempt 1 is an injected flawed test draft (invented Wix job). "
                    "Critic and revisions use the language model.")
    a = r.attempts
    ok = (
        len(a) >= 2
        and a[0].evaluation_completed and a[0].is_acceptable is False
        and r.status == APPROVED
        and "Wix" not in r.message
    )
    return log, "Draft with invented fact rejected with reasons, revised and re-evaluated", ok


def scenario_5():
    log = AuditLog(OUT_DIR / "scenario_5.json")
    q = "ספר לי על ההתמחות שלך"
    r, _ = turn(q, [], "S5", evaluate_fn=always_reject)
    log.record(r, critic="mock",
               note="CONTROL-FLOW TEST: mock Critic rejects every answer. Not a language-model evaluation.")
    ok = (
        r.status == MAX_ATTEMPTS
        and len(r.attempts) == config.MAX_ATTEMPTS
        and all(x.is_acceptable is False for x in r.attempts)
    )
    return log, f"{config.MAX_ATTEMPTS} rejected attempts, stop, end message", ok


SCENARIOS = {
    1: ("Existing information", scenario_1),
    2: ("Follow-up question", scenario_2),
    3: ("Detail not in the sources", scenario_3),
    4: ("Rejection and improvement", scenario_4),
    5: ("Exhausting the attempts (MOCK critic)", scenario_5),
}


# ---------------------------------------------------------------- summary
def write_summary(rows) -> None:
    lines = [
        "# Scenario results",
        "",
        f"Run: {datetime.now().isoformat(timespec='seconds')}  ",
        f"Actor: `{config.ACTOR_MODEL}` · Critic: `{config.CRITIC_MODEL}` · "
        f"Max attempts: {config.MAX_ATTEMPTS}",
        "",
    ]
    sections = [
        ("## Language-model results (scenarios 1–4)", "llm"),
        ("## Mock control-flow test (scenario 5)", "mock"),
    ]
    for header, kind in sections:
        selected = [row for row in rows if row["kind"] == kind]
        if not selected:
            continue
        lines += [header, "", "| # | Scenario | Expected | Status | Attempts | Matches expectation |",
                  "|---|---|---|---|---|---|"]
        for row in selected:
            lines.append(
                f"| {row['n']} | {row['name']} | {row['expected']} | {row['status']} | "
                f"{row['attempts']} | {'✅ yes' if row['ok'] else '❌ no'} |"
            )
        lines.append("")
        for row in selected:
            lines.append(f"### Scenario {row['n']}: {row['name']}")
            for rec in row["records"]:
                lines.append(f"- **Question:** {rec['question']}")
                for att in rec["attempts"]:
                    tag = " (injected test draft)" if att.get("injected_draft") else ""
                    lines.append(f"  - Attempt {att['attempt']}{tag}: **{att['decision']}**")
                    lines.append(f"    - Candidate: {att['candidate']}")
                    if att["feedback"]:
                        lines.append(f"    - Feedback: {att['feedback']}")
                    if att["error"]:
                        lines.append(f"    - Error: {att['error']}")
                lines.append(f"  - **Shown to user ({rec['status']}):** {rec['message']}")
            lines.append(f"- Log file: `logs/scenarios/scenario_{row['n']}.json`")
            lines.append("")
    (OUT_DIR / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    only = {int(x) for x in sys.argv[1:]} or set(SCENARIOS)
    rows = []
    for n, (name, fn) in SCENARIOS.items():
        if n not in only:
            continue
        print(f"\n▶ Scenario {n}: {name}")
        log, expected, ok = fn()
        last = log.records[-1]
        rows.append({
            "n": n, "name": name, "expected": expected, "ok": ok,
            "status": " / ".join(r["status"] for r in log.records),
            "attempts": " / ".join(str(r["num_attempts"]) for r in log.records),
            "kind": log.records[0]["critic"], "records": log.records,
        })
        for rec in log.records:
            print(f"   Q: {rec['question']}")
            for att in rec["attempts"]:
                print(f"     #{att['attempt']} {att['decision']}: {att['feedback'] or att['error']}")
            print(f"   -> [{rec['status']}] {rec['message']}")
        print(f"   matches expectation: {'YES' if ok else 'NO'}  (log: {log.path.name})")
    write_summary(rows)
    print(f"\nSummary written to {OUT_DIR / 'summary.md'}")


if __name__ == "__main__":
    main()
