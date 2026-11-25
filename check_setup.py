"""Stage 0 check: verifies the key loads and both configured models respond.

Run:  python check_setup.py
Cost: two tiny calls (well under one cent).
"""
from openai import OpenAI

from src import config


def main() -> None:
    client = OpenAI(api_key=config.require_api_key())
    print("API key loaded (not printed).")

    for role, model in [("Actor", config.ACTOR_MODEL), ("Critic", config.CRITIC_MODEL)]:
        try:
            resp = client.responses.create(
                model=model,
                input="ענה במילה אחת: מה בירת צרפת?",
                max_output_tokens=50,
            )
            print(f"[OK] {role} model '{model}' answered: {resp.output_text.strip()}")
            if resp.usage:
                print(f"     tokens: in={resp.usage.input_tokens}, out={resp.usage.output_tokens}")
        except Exception as exc:  # show a clear message instead of a long traceback
            print(f"[FAIL] {role} model '{model}': {type(exc).__name__}: {exc}")
            print("       If the model name is not found, change it in .env.")


if __name__ == "__main__":
    main()
