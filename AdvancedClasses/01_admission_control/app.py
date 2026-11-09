"""Class 1 — FastAPI service: admission control.

The gates a request passes through, cheapest and most fundamental first:

    POST /v1/analyze:    401 auth -> 429 rate limit -> 422 validation
                         -> 402 monthly quota -> 402 credits -> handler
    GET  /v1/usage/{id}: 401 auth -> 403 authorization (only your own)

Run:
    python create_db.py        # once, to build + seed the database
    uvicorn app:app --reload   # starts on http://127.0.0.1:8000

Then open http://127.0.0.1:8000/docs to poke it, or use HTTP from the notebook.
"""
import os
import sqlite3
import hashlib
import time
from collections import defaultdict

from fastapi import FastAPI, Depends, HTTPException, Header, Body
from pydantic import BaseModel

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "class1.db")

REQUESTS_PER_MINUTE = 5   # the time-based limit; change this to show the effect

# in-memory rate-limit state: user_id -> recent request timestamps
rate_hits = defaultdict(list)


# --------------------------------------------------------------------------
# Database helpers
# --------------------------------------------------------------------------
def db() -> sqlite3.Connection:
    if not os.path.exists(DB):
        raise RuntimeError("Database not found. Run `python create_db.py` first.")
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


app = FastAPI(title="Class 1 — Admission control")


# --------------------------------------------------------------------------
# Request bodies
# --------------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    question: str          # required -> a missing one gives 422
    tokens: int = 100      # simulated cost of this call, in tokens


class TopUpRequest(BaseModel):
    amount: int


# --------------------------------------------------------------------------
# GATE 1 — Authentication (401)
# --------------------------------------------------------------------------
def require_key(x_api_key: str = Header(default=None)) -> dict:
    """Who are you? Look up the hash of the presented key."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    conn = db()
    row = conn.execute(
        "SELECT user_id, name FROM users WHERE key_hash = ?",
        (sha256(x_api_key),),
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=401, detail="Unknown API key")
    return {"user_id": row["user_id"], "name": row["name"]}


# --------------------------------------------------------------------------
# GATE 2 — Rate limit (429), sliding 60-second window, per caller
# --------------------------------------------------------------------------
def rate_limit(caller: dict = Depends(require_key)) -> dict:
    """How many / how fast? A sliding 60-second window, kept in memory.

    The attempt is recorded BEFORE the body is validated, so a malformed
    request (422) still consumes a slot. 'Admission before validation'.

    In memory on purpose: rate limits are transient. Real systems keep this
    in Redis (a shared in-memory store), not a database.
    """
    now = time.time()
    recent = [t for t in rate_hits[caller["user_id"]] if now - t < 10]
    if len(recent) >= REQUESTS_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit reached: {REQUESTS_PER_MINUTE} requests per minute",
        )
    recent.append(now)
    rate_hits[caller["user_id"]] = recent
    return caller


# --------------------------------------------------------------------------
# The main endpoint: all gates, then work
# --------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/analyze")
def analyze(caller: dict = Depends(rate_limit), body: AnalyzeRequest = Body(...)):
    """Gates in order: 401 -> 429 -> 422 -> 402 -> handler."""
    conn = db()
    uid = caller["user_id"]

    # ---- GATE 3 — monthly token allowance (402) ----
    used = conn.execute(
        "SELECT COALESCE(SUM(tokens), 0) AS s FROM usage "
        "WHERE user_id = ? AND ts >= datetime('now', 'start of month')",
        (uid,),
    ).fetchone()["s"]
    allowance = conn.execute(
        "SELECT monthly_tokens AS t FROM users WHERE user_id = ?", (uid,)
    ).fetchone()["t"]
    if used + body.tokens > allowance:
        conn.close()
        raise HTTPException(
            status_code=402,
            detail=f"Monthly token quota exceeded: {used}/{allowance} used this month",
        )

    # ---- GATE 4 — prepaid credits (402), atomic spend ----
    cur = conn.execute(
        "UPDATE users SET credits = credits - ? "
        "WHERE user_id = ? AND credits >= ?",
        (body.tokens, uid, body.tokens),
    )
    if cur.rowcount == 0:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=402, detail="Insufficient credits — please top up")

    # ---- HANDLER — the (simulated) expensive work ----
    conn.execute("INSERT INTO usage(user_id, tokens) VALUES (?, ?)", (uid, body.tokens))
    conn.commit()
    remaining = allowance - used - body.tokens
    conn.close()
    return {
        "owner": caller["name"],
        "question": body.question,
        "tokens_charged": body.tokens,
        "monthly_remaining": remaining,
    }


# --------------------------------------------------------------------------
# GATE 5 — Authorization (403): you may only read your own usage
# --------------------------------------------------------------------------
@app.get("/v1/usage/{user_id}")
def usage(user_id: str, caller: dict = Depends(require_key)):
    if user_id != caller["user_id"]:
        raise HTTPException(status_code=403, detail="You may only view your own usage")
    conn = db()
    used = conn.execute(
        "SELECT COALESCE(SUM(tokens), 0) AS s FROM usage "
        "WHERE user_id = ? AND ts >= datetime('now', 'start of month')",
        (user_id,),
    ).fetchone()["s"]
    allowance = conn.execute(
        "SELECT monthly_tokens AS t FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()["t"]
    credits = conn.execute(
        "SELECT credits AS b FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()["b"]
    conn.close()
    return {
        "user_id": user_id,
        "monthly_used": used,
        "monthly_allowance": allowance,
        "credits": credits,
    }


# --------------------------------------------------------------------------
# Top up credits (the "add paid tokens" simulation)
# --------------------------------------------------------------------------
@app.post("/v1/credits/topup")
def topup(body: TopUpRequest, caller: dict = Depends(require_key)):
    conn = db()
    conn.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?",
                 (body.amount, caller["user_id"]))
    conn.commit()
    balance = conn.execute(
        "SELECT credits AS b FROM users WHERE user_id = ?", (caller["user_id"],)
    ).fetchone()["b"]
    conn.close()
    return {"user_id": caller["user_id"], "credits": balance}


# --------------------------------------------------------------------------
# TEACHING HELPER (not production): reset the demo state between scenes
# --------------------------------------------------------------------------
@app.post("/_reset")
def reset():
    rate_hits.clear()
    conn = db()
    conn.execute("DELETE FROM usage")
    conn.execute("UPDATE users SET credits = 1000 WHERE user_id = 'alice'")
    conn.execute("UPDATE users SET credits = 600  WHERE user_id = 'bob'")
    conn.commit()
    conn.close()
    return {"reset": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
