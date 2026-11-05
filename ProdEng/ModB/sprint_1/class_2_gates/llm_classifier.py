"""The same job as classifier.py, but done by a real LLM through OpenRouter."""
import os

import httpx

VALID_LABELS = {"positive", "negative", "neutral"}
PROMPT = (
    "Classify the sentiment of this sentence as exactly one word: "
    "positive, negative or neutral. Reply with that one word only.\n\nSentence: {text}"
)


def classify_llm(text: str) -> str:
    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
        json={
            "model": os.environ.get("OPENROUTER_MODEL", "openai/gpt-4.1-mini"),
            "messages": [{"role": "user", "content": PROMPT.format(text=text)}],
            "temperature": 0,
        },
        timeout=20,
    )
    response.raise_for_status()
    reply = response.json()["choices"][0]["message"]["content"]
    label = reply.strip().strip(".!").lower()
    # LLMs sometimes answer with extra words. An unexpected reply counts as a miss.
    return label if label in VALID_LABELS else f"INVALID({reply.strip()[:30]})"
