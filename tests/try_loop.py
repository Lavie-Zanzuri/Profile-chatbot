"""Stage 5 check for the loop.

Run from the project root:  python -m tests.try_loop

Part 1 (no API, fake Actor/Critic): checks the 3 exit paths and that the
revision receives the rejected answer and the feedback.
Part 2 (API): one real question through the full loop.
"""
from src.critic import EvaluationError
from src.evaluation import Evaluation
from src.loop import handle_question


def print_result(title, result) -> None:
    print(f"\n=== {title} ===")
    print(f"status:  {result.status}")
    print(f"message: {result.message}")
    for a in result.attempts:
        decision = a.is_acceptable if a.evaluation_completed else "evaluation not completed"
        print(f"  attempt {a.attempt}: decision={decision}")
        print(f"    candidate: {a.candidate}")
        if a.feedback:
            print(f"    feedback:  {a.feedback}")
        if a.error:
            print(f"    error:     {a.error}")


# ---------- fakes ----------
received = []  # what the fake Actor received on each call


def fake_actor(question, history, rejected_answer=None, feedback=None, **_):
    received.append((rejected_answer, feedback))
    return f"draft #{len(received)}"


def critic_reject_once(question, candidate, history, **_):
    if candidate == "draft #1":
        return Evaluation(is_acceptable=False, feedback="draft #1 invents a fact, remove it")
    return Evaluation(is_acceptable=True, feedback="ok")


def critic_always_reject(question, candidate, history, **_):
    return Evaluation(is_acceptable=False, feedback=f"[MOCK] rejected {candidate}")


def critic_broken(question, candidate, history, **_):
    raise EvaluationError("Critic output failed validation: missing field 'feedback'")


def part1() -> None:
    print("##### Part 1: control flow with fakes (no API) #####")

    received.clear()
    r = handle_question("q", [], generate_fn=fake_actor, evaluate_fn=critic_reject_once)
    print_result("reject then approve (expect approved after 2 attempts)", r)
    print(f"  attempt 2 received: rejected={received[1][0]!r}, feedback={received[1][1]!r}")

    received.clear()
    r = handle_question("q", [], generate_fn=fake_actor, evaluate_fn=critic_always_reject)
    print_result("always reject (expect max_attempts after 3)", r)

    received.clear()
    r = handle_question("q", [], generate_fn=fake_actor, evaluate_fn=critic_broken)
    print_result("invalid critic output (expect technical_error)", r)


def part2() -> None:
    print("\n##### Part 2: real Actor + Critic (API) #####")
    r = handle_question("באילו טכנולוגיות השתמשת בפרויקט ה-Microservices?", [])
    print_result("real question", r)


if __name__ == "__main__":
    part1()
    part2()
