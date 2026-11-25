"""Central configuration: loads settings from the .env file."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
PROMPTS_DIR = ROOT_DIR / "prompts"
LOGS_DIR = ROOT_DIR / "logs"

load_dotenv(ROOT_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ACTOR_MODEL = os.getenv("ACTOR_MODEL", "gpt-5.4-mini")
CRITIC_MODEL = os.getenv("CRITIC_MODEL", "gpt-5.4-mini")
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "3"))


def require_api_key() -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and set your key."
        )
    return OPENAI_API_KEY
