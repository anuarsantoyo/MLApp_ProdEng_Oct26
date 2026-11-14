# Advanced Course Roadmap (DRAFT)

Masterschool — AI App Development + Product Engineering, advanced portion (Sprints 2-4).

The two courses are merged into one **sequential 8-class course** (8 x 1.5h), teaching the raw skills as standalone tutorials. The arc: secure -> don't leak -> automate -> package -> deploy -> serve -> observe -> present.

Each class is a self-contained tutorial students can revisit as a cheatsheet. This doc is the topic map; the actual lessons are built one at a time.

---

## Class 1 — Admission control: API keys + rate limiting

Two decisions at the front door, before any real work: "do I know who you are?" (authentication) and "have you asked too much?" (rate limiting).

**The two keys (easy to confuse).** A *caller key* is what the customer sends to YOUR service. A *provider key* is what YOUR service sends to OpenRouter/OpenAI. Same idea, opposite direction.

Example — checking who is calling:

```python
from fastapi import FastAPI, Depends, HTTPException, Header

app = FastAPI()
API_KEYS = {"alice-123": "Alice", "bob-456": "Bob"}

def require_key(x_api_key: str = Header(None)):
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="unknown key")
    return x_api_key

@app.get("/secret")
def secret(key: str = Depends(require_key)):
    return {"hello": API_KEYS[key]}
```

Example — limiting how often:

```python
import time
from collections import defaultdict

hits = defaultdict(list)   # key -> recent request timestamps

def rate_limit(key: str = Depends(require_key)):
    now = time.time()
    recent = [t for t in hits[key] if now - t < 60]
    if len(recent) >= 5:                    # max 5 per minute
        raise HTTPException(status_code=429, detail="too many requests")
    recent.append(now)
    hits[key] = recent
    return key
```

The teaching gold: the three-stop sequence. Unknown key -> 401. Known key but out of allowance -> 429. Valid key with allowance left but a bad body -> 422. Order matters: auth runs before limiting, limiting runs before validating the body.

**One thing to remember.** "Admission before validation" — check who and how often before you even look at what they sent.

---

## Class 2 — Secrets: don't leak

A secret (API key, password, token) is still configuration — but configuration that becomes dangerous the moment it leaks. This class covers everything that needs only Python and git (no Docker, no cloud): the three leak paths. "Secrets in the image" lands in Class 4; "secrets in the cloud" in Class 5.

**The core distinction.** Configuration = safe to see (log level, model name, timeout). Secret = must never be committed to git, written into a log, or pasted into a prompt.

How the value gets in (the right way) — environment variables:

```python
import os
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")     # config, has a default
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")  # secret, no default
```

Use a `.env` file locally (loaded with python-dotenv or pydantic-settings), and add `.env` to `.gitignore`.

**Leak 1 — logs.** Log identity and outcome, never the private body:

```python
logger.info(f"got request {request}")            # BAD: the key is inside
logger.info(f"request_id={rid} route=/v1/answer")# GOOD: identity + outcome only
```

**Leak 2 — prompts.** Don't paste raw user input straight into a prompt — the input can contain a key or private text the user typed.

**Leak 3 — git (the surprising one).** Deleting a file does not delete its history:

```bash
echo 'OPENROUTER_API_KEY=sk-secret' > .env
git add .env && git commit -m "wip"   # 1. accidentally committed
rm .env
echo '.env' >> .gitignore
git commit -m "remove .env"           # 2. deleted + ignored

git log --all -p -- .env              # 3. sk-secret is STILL in history
```

`.gitignore` only stops FUTURE commits. A key that was ever committed is still recoverable from history — the honest guidance is: assume it's compromised, rotate the key, and scrub history with `git filter-repo` if the repo is shared.

**One thing to remember.** "A secret leaks the moment it's copied somewhere it shouldn't be — a log, a prompt, or git history."

---

## Class 3 — Automate your checks: CI/CD

CI = a machine runs your tests, linter, and eval gate automatically every time someone pushes or opens a PR.

**The key mental model.** CI is NOT a new testing system. It's automation around commands you already run locally.

```yaml
name: CI
on:
  push:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: ruff check .
      - run: pytest
      - run: python scripts/run_eval.py
```

**Exit codes.** Every command ends returning 0 (success) or non-zero (failure). Any non-zero step fails the job, fails the workflow. The eval gate works in CI precisely because it exits non-zero when the score is too low.

**Order matters.** Cheap fast checks (ruff) go first.

**One thing to remember.** "In Sprint 1 we built the checks; in Sprint 2 we stopped relying on humans to run them."

---

## Class 4 — Docker: image vs container

A container packages your app together with its runtime so it runs identically everywhere — the fix for "works on my machine."

**The single most important distinction:**

    Dockerfile  --build-->  Image  --run-->  Container
    (instructions)        (the artifact)   (running instance)

One image can start many containers. A container is NOT your source code, NOT a venv, NOT a full VM.

Example Dockerfile:

```dockerfile
FROM python:3.12-slim              # base: "what Python do we need?"
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt  # deps
COPY . .                           # application code
EXPOSE 8000                        # the port the app listens on
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t myapp:local .
docker run -p 8000:8000 myapp:local
```

**Callback — secrets in the image.** An image is handed to everyone who pulls it. Don't put a key in the Dockerfile (`ENV OPENROUTER_API_KEY=...`) or `COPY .env .` into the image — that leaks it to everyone with pull access. Keys are injected at run time (see Class 5).

**One thing to remember.** "A container is a portable runtime unit for your service." Build makes the image; run makes the container.

---

## Class 5 — Deploy: registry + Cloud Run

Take the image, store it in a registry (GHCR — "GitHub for images"), and let Cloud Run run it behind a public URL.

The chain: code -> docker build -> image -> docker push -> GHCR -> Cloud Run -> public URL

```bash
docker tag myapp:local ghcr.io/anuar/myapp:v1
docker login ghcr.io -u anuar --password-stdin
docker push ghcr.io/anuar/myapp:v1
```

Image names: `ghcr.io/<owner>/<image>:<tag>` — registry / owner / name / version. The registry path must be lowercase.

Then Cloud Run points at `ghcr.io/anuar/myapp:v1`, port 8000, plus env vars and secrets. It retrieves the image, runs it, and returns a public URL. Verify GET /health and the analyze endpoint against the public URL.

**Same image, different config.** You built the app once; now configure it for the environment it runs in — dev (deterministic provider, DEBUG logging), staging (cheap provider), prod (real provider, INFO logging). Same image + different environment variables = different behavior, with zero code changes and no dev.py/staging.py/prod.py copies.

**Secrets in the cloud.** Ordinary configuration values can be set in the platform directly; secrets go into Cloud Run's secret manager and are referenced by the service — never committed to git, never baked into the image.

**Deploy != rewrite.** Same container, new environment.

**One thing to remember.** "The registry is where building ends and deploying begins."

---

## Class 6 — Serve a trained ML model

Not every AI task needs an LLM. A small classical model (TF-IDF + logistic regression for sentiment) can be saved as a file and served behind a versioned endpoint next to the LLM endpoint.

Train once, save an artifact, load once, reuse:

```python
# training side (run once, offline):
joblib.dump({"version": "1.0.0", "pipeline": pipeline},
            "sentiment_model.joblib")

# serving side:
artifact = joblib.load("sentiment_model.joblib")   # load ONCE at startup
pipeline = artifact["pipeline"]
model_version = artifact["version"]

def predict(text):
    label  = pipeline.predict([text])[0]
    proba  = pipeline.predict_proba([text])[0].max()
    return {"sentiment": label, "confidence": proba,
            "model_version": model_version}
```

**Load once, never per request.**

Versioning — two different "versions" you must not blend:
- `/v1/` = the API version (the contract's version)
- `model_version` = which model artifact produced this prediction

Two paths side by side:

    POST /v1/feedback/analyze    -> LLM/provider -> rich structured analysis
    POST /v1/sentiment/predict   -> scikit-learn -> sentiment + confidence + model_version

**One thing to remember.** "A production AI service doesn't choose between LLMs and classical ML — it exposes both behind clear contracts."

---

## Class 7 — Observe: streaming + structured logging

Two ways of seeing into a service, answering different questions. Streaming answers "when can the caller act?" Logging answers "what happened after the caller left?"

**Streaming** — send chunks as produced:

```python
from fastapi.responses import StreamingResponse

async def generate():
    for chunk in llm_stream(prompt):
        yield chunk          # each chunk reaches the caller immediately

@app.post("/v1/answer/stream")
def stream(payload):
    return StreamingResponse(generate(), media_type="text/event-stream")
```

A stream is a sequence of events (start, delta, delta, complete/error). Partial text is not complete text. A 200 at the start does NOT mean the answer finished. A terminal event proves the outcome.

**Logging** — structured key=value fields, redacting the private parts:

```python
import logging, uuid, time

rid = str(uuid.uuid4())      # request ID: ties one request to its records
start = time.time()
# ... do the work ...
logger.info("request_id=%s route=%s status=%s latency_ms=%d model=%s",
            rid, route, status, (time.time()-start)*1000, model)
```

Log identity and outcome — NOT the user's question text (private), NOT the API key (secret).

**The 10-minute extra:** a log observation ("requests are failing here") can become an evaluation case run through the existing eval gate. Log -> hypothesis -> test.

**One thing to remember.** "Streaming shows progress to the caller; logging shows history to the operator. Different questions — don't swap their evidence."

---

## Class 8 — Capstone: a front door, a proof, and a handoff

Three final things that turn a working API into a presentable project: a tiny UI (static HTML), one end-to-end test, and documentation other humans can use.

**A tiny UI** — a static HTML page that talks to the API. No HTML deep-dive; the point is that the browser is just another HTTP client, sending the same POST + JSON as curl:

```html
<!-- static/index.html -->
<input id="q" placeholder="Question" />
<textarea id="c" placeholder="Context"></textarea>
<button onclick="ask()">Ask</button>
<pre id="out"></pre>
<script>
  async function ask() {
    const r = await fetch("/v1/answer", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({question: q.value, context: c.value})
    });
    out.textContent = JSON.stringify(await r.json(), null, 2);
  }
</script>
```

Serve it in one line:

```python
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

(One-line mention: Streamlit is a Python way to build the same thing when you want a fuller app later.)

**End-to-end test** — exercise UI -> service -> model across the real boundaries; deliberately break one link to prove the test can catch a failure.

**Three docs, three audiences:**

    README     = "how do I run this?"          (a new engineer)
    API docs   = "how do I call each endpoint?" (another developer)
    runbook    = "what do I do when it breaks?" (an on-call operator)

A runbook is a table: symptom -> what to check -> likely cause -> action. Three scenarios are enough.

**Portfolio framing.** Not "I used FastAPI and Docker." Instead:

> "The service turns unstructured customer feedback into structured insights, with automated tests, an evaluation gate, containerization, and deployment making changes safer to ship."

Problem -> solution -> architecture -> evidence it works -> business value -> honest limitations.

**One thing to remember.** "A strong portfolio shows not just what you built, but why it exists, how it works, and how you know it works."

---

## The full arc

Secure -> don't leak -> automate -> package -> deploy -> serve -> observe -> present.
