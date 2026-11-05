"""The same evaluation gate, but scoring a REAL model instead of keyword rules."""
import json
import os
import sys
from pathlib import Path

import httpx

from classifier import classify
from llm_classifier import classify_llm

HERE = Path(__file__).parent
THRESHOLD = 0.8


def load_dotenv(path: Path) -> None:
    """Tiny .env reader so we need no extra package. Real env variables win."""
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def main() -> int:
    for folder in (HERE, HERE.parent, Path.cwd()):
        load_dotenv(folder / ".env")
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY not found (set it in .env or the environment).")
        return 2  # 2 = could not run the evaluation, which is different from a quality failure

    cases = json.loads((HERE / "eval_cases.json").read_text())
    llm_passed = keyword_passed = 0
    print(f"model: {os.environ.get('OPENROUTER_MODEL', 'openai/gpt-4.1-mini')}\n")
    print(f"{'sentence':<32}{'expected':<10}{'keywords':<10}{'LLM'}")
    try:
        for case in cases:
            keyword_label = classify(case["text"])
            llm_label = classify_llm(case["text"])
            keyword_passed += keyword_label == case["expected"]
            llm_passed += llm_label == case["expected"]
            print(f"{case['text']:<32}{case['expected']:<10}{keyword_label:<10}{llm_label}")
    except (httpx.HTTPError, KeyError, IndexError) as exc:
        print(f"\nProvider problem, evaluation could not finish: {type(exc).__name__}: {exc}")
        return 2

    score = llm_passed / len(cases)
    print(f"\nkeyword score: {keyword_passed / len(cases):.3f}")
    print(f"LLM score:     {score:.3f} ({llm_passed}/{len(cases)}), threshold={THRESHOLD}")
    return 0 if score >= THRESHOLD else 1


if __name__ == "__main__":
    sys.exit(main())
