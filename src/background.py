"""Loads the background sources (LinkedIn profile + personal summary)."""
from src.config import DATA_DIR

SOURCES = {
    "LinkedIn": "linkedin.txt",
    "Summary": "summary.txt",
}


def load_background() -> str:
    """Return all background sources as one labeled text block.

    Each source is wrapped in a labeled section so the Actor and the Critic
    can refer to where a fact came from.
    """
    parts = []
    for label, filename in SOURCES.items():
        path = DATA_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Background file not found: {path}")
        text = path.read_text(encoding="utf-8").strip()
        parts.append(f"<source name=\"{label}\" file=\"{filename}\">\n{text}\n</source>")
    return "\n\n".join(parts)


if __name__ == "__main__":
    background = load_background()
    print(background)
    print(f"\n--- {len(background)} characters loaded ---")
