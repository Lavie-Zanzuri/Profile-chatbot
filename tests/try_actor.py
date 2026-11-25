"""Stage 2 manual check for the Actor (no Critic yet).

Run from the project root:  python -m tests.try_actor
Runs 4 questions: an existing fact, a follow-up, missing info and a revision.
"""
from src.actor import generate


def show(title: str, question: str, answer: str) -> None:
    print(f"\n=== {title} ===")
    print(f"Q: {question}")
    print(f"A: {answer}")


def main() -> None:
    history = []

    # 1. Existing information
    q1 = "איפה עשית התמחות ומה עשית שם?"
    a1 = generate(q1, history)
    show("1. Existing info", q1, a1)
    history += [{"role": "user", "content": q1}, {"role": "assistant", "content": a1}]

    # 2. Follow-up that relies on the previous answer
    q2 = "וכמה זמן זה נמשך?"
    a2 = generate(q2, history)
    show("2. Follow-up", q2, a2)

    # 3. Missing information
    q3 = "מה הממוצע שלך בתואר?"
    a3 = generate(q3, [])
    show("3. Missing info", q3, a3)

    # 4. Revision with a fake rejected draft + feedback
    q4 = "באילו חברות עבדת?"
    bad = "עבדתי ב-TracePCB וגם שנתיים כמפתח Backend בחברת Wix."
    fb = ("The claim about working at Wix is not supported by the sources. "
          "Remove it and mention only employers that appear in the sources.")
    a4 = generate(q4, [], rejected_answer=bad, feedback=fb)
    show("4. Revision", q4, a4)
    print(f"   (rejected draft was: {bad})")


if __name__ == "__main__":
    main()
