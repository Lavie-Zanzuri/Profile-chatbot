"""Mock Critic for the control-flow test (scenario 5).

It does NOT call a language model. It rejects every candidate, so the loop must
stop after the last attempt. Results produced with it are marked critic="mock"
in the logs and must not be presented as language-model results.
"""
from src.evaluation import Evaluation


def always_reject(question, candidate, history, **_) -> Evaluation:
    return Evaluation(
        is_acceptable=False,
        feedback="[MOCK CRITIC] Control-flow test: every answer is rejected on purpose.",
    )
