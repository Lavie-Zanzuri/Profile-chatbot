"""Structured result of the Critic, validated with Pydantic."""
from pydantic import BaseModel, ConfigDict, Field


class Evaluation(BaseModel):
    """The Critic's decision about one candidate answer."""

    # strict: "true" (string) or 1 is NOT accepted as a bool.
    # forbid: unexpected extra fields make validation fail.
    model_config = ConfigDict(strict=True, extra="forbid")

    is_acceptable: bool = Field(
        description="True if the answer meets all the criteria, otherwise False."
    )
    feedback: str = Field(
        min_length=1,
        description=(
            "Short justification. When rejecting: the exact problem "
            "(which claim or which missing part) and a practical instruction for fixing it."
        ),
    )


# JSON Schema sent to the model (OpenAI strict structured outputs).
EVALUATION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "is_acceptable": {"type": "boolean"},
        "feedback": {"type": "string"},
    },
    "required": ["is_acceptable", "feedback"],
    "additionalProperties": False,
}
