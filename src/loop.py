"""Actor -> Critic -> revision loop for a single user question.

Exit paths:
  approved        the Critic accepted a candidate -> shown to the user
  max_attempts    all attempts were rejected      -> a "no approved answer" message
  technical_error a model call failed or the evaluation output was invalid
                  -> an error message; the evaluation is recorded as not completed
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Callable

from src import config
from src.actor import History, generate
from src.critic import evaluate
from src.evaluation import Evaluation

APPROVED = "approved"
MAX_ATTEMPTS = "max_attempts"
TECHNICAL_ERROR = "technical_error"

MSG_MAX_ATTEMPTS = (
    "לא התקבלה תשובה מאושרת במסגרת מגבלת {n} הניסיונות. "
    "אפשר לנסח את השאלה מחדש או לשאול שאלה אחרת."
)
MSG_TECHNICAL_ERROR = "⚠️ אירעה שגיאה טכנית והטיפול בשאלה הופסק. ({reason})"


@dataclass
class AttemptRecord:
    attempt: int
    candidate: str | None                 # None if generation itself failed
    evaluation_completed: bool
    is_acceptable: bool | None = None     # None when the evaluation was not completed
    feedback: str | None = None
    error: str | None = None
    injected_draft: bool = False          # True if this candidate was a forced test draft


@dataclass
class QuestionResult:
    question: str
    status: str                           # APPROVED / MAX_ATTEMPTS / TECHNICAL_ERROR
    message: str                          # what is shown to the user
    attempts: list[AttemptRecord] = field(default_factory=list)
    scenario_id: str | None = None
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict:
        return asdict(self)


def handle_question(
    question: str,
    history: History,
    *,
    generate_fn: Callable[..., str] = generate,
    evaluate_fn: Callable[..., Evaluation] = evaluate,
    max_attempts: int | None = None,
    background: str | None = None,
    scenario_id: str | None = None,
    forced_first_draft: str | None = None,
) -> QuestionResult:
    """Run the loop for one question. The attempt counter starts at 1 for every question.

    forced_first_draft: test hook (scenario 4). If given, it replaces the Actor's
    first draft; the Critic and all later revisions still use the language model.
    """
    max_attempts = max_attempts or config.MAX_ATTEMPTS
    attempts: list[AttemptRecord] = []
    rejected_answer: str | None = None
    feedback: str | None = None

    def stop_with_error(reason: str) -> QuestionResult:
        return QuestionResult(
            question=question,
            status=TECHNICAL_ERROR,
            message=MSG_TECHNICAL_ERROR.format(reason=reason.split(":")[0]),
            attempts=attempts,
            scenario_id=scenario_id,
            error=reason,
        )

    for n in range(1, max_attempts + 1):
        # 1 / 4. Generate (first draft, or a revision using the rejected answer + feedback)
        injected = n == 1 and forced_first_draft is not None
        try:
            if injected:
                candidate = forced_first_draft
            else:
                candidate = generate_fn(
                    question, history, rejected_answer, feedback, background=background
                )
        except Exception as exc:
            reason = f"Actor call failed: {type(exc).__name__}: {exc}"
            attempts.append(AttemptRecord(n, None, evaluation_completed=False, error=reason))
            return stop_with_error(reason)

        # 2. Evaluate + validate against Evaluation (done inside evaluate_fn)
        try:
            ev = evaluate_fn(question, candidate, history, background=background)
            if not isinstance(ev, Evaluation):
                raise TypeError(f"expected Evaluation, got {type(ev).__name__}")
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            attempts.append(AttemptRecord(
                n, candidate, evaluation_completed=False, error=reason, injected_draft=injected
            ))
            return stop_with_error(reason)

        attempts.append(AttemptRecord(
            n, candidate, evaluation_completed=True,
            is_acceptable=ev.is_acceptable, feedback=ev.feedback, injected_draft=injected,
        ))

        # 3. Approved -> done
        if ev.is_acceptable:
            return QuestionResult(question, APPROVED, candidate, attempts, scenario_id)

        # 4. Rejected -> pass the rejected answer and the feedback to the next attempt
        rejected_answer, feedback = candidate, ev.feedback

    # 5. All attempts rejected
    return QuestionResult(
        question, MAX_ATTEMPTS, MSG_MAX_ATTEMPTS.format(n=max_attempts), attempts, scenario_id
    )
