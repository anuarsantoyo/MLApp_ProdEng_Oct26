"""Testing a REAL LLM with pytest.

Each entry in llm_cases.json becomes one test. We send the prompt to the model
(through OpenRouter, using the standard OpenAI client) and compare its answer
with the expected one.

Setup:  pip install pytest openai python-dotenv
        copy .env.example to .env and add your OPENROUTER_API_KEY
Run:    pytest test_llm.py -v
"""
import json
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # reads OPENROUTER_API_KEY (and optional settings) from the .env file

CASES = json.loads((Path(__file__).parent / "llm_cases.json").read_text())


@pytest.fixture(scope="session")
def client() -> OpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        # Skipped, not failed: no key means "can't run", not "the model is wrong".
        pytest.skip("OPENROUTER_API_KEY is not set (add it to your .env file)")
    return OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    )


def normalize(text: str) -> str:
    """Models often add a full stop or capital letter ('Paris.'), which is not an error."""
    return text.strip().strip(".!\"'").lower()


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_llm_answers_as_expected(client, case):
    # Arrange: the prompt and the expected answer come from the JSON file
    # Act: ask the real model (temperature 0 = as repeatable as possible)
    response = client.chat.completions.create(
        model=os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash-lite"),
        messages=[{"role": "user", "content": case["prompt"]}],
        temperature=0,
        max_tokens=30,
    )
    answer = normalize(response.choices[0].message.content)

    # Assert: a readable message shows exactly what went wrong
    assert answer == case["expected"], (
        f"prompt: {case['prompt']!r}\nexpected: {case['expected']!r}\ngot:      {answer!r}"
    )
