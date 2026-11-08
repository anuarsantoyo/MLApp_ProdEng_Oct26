"""Class 1 — FastAPI service: admission control.

The gates a request passes through, cheapest and most fundamental first:

    401 authentication   -> who are you?
    403 authorization    -> are you allowed? (only your own usage)
    429 rate limit       -> how many / how fast? (requests per minute)
    422 validation       -> is the body well-formed?
    402 quota / credits  -> have you paid? (monthly allowance, then prepaid balance)
    handler             -> the expensive work (simulated here)

Run:
    python create_db.py        # once, to build + seed the database
    python app.py              # starts on http://127.0.0.1:8000

Then open http://127.0.0.1:8000/docs to poke it, or use HTTP from the notebook.
"""
import os
import sqlite3
import hashlib

from fastapi import FastAPI, Depends, HTTPException, Header, Body
from pydantic import BaseModel

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "class1.db")

REQUESTS_PER_MINUTE = 5   # the time-based limit; change this to show the effect


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
        "SELECT k.user_id, u.name, u.plan "
        "FROM api_keys k JOIN users u ON u.user_id = k.user_id "
        "WHERE k.key_hash = ?",
        (sha256(x_api_key),),
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=401, detail="Unknown API key")
    return {"user_id": row["user_id"], "name": row["name"], "plan": row["plan"]}


# --------------------------------------------------------------------------
# GATE 3 — Rate limit (429), sliding 60-second window, per caller
# --------------------------------------------------------------------------
def rate_limit(caller: dict = Depends(require_key)) -> dict:
    """How many / how fast? Count this caller's requests in the last 60s.

    The attempt is recorded BEFORE the body is validated, so a malformed
    request (422) still consumes a slot. That is 'admission before validation'.
    """
    conn = db()
    used = conn.execute(
        "SELECT COUNT(*) AS c FROM request_log "
        "WHERE user_id = ? AND ts > datetime('now', '-60 seconds')",
        (caller["user_id"],),
    ).fetchone()["c"]
    if used >= REQUESTS_PER_MINUTE:
        conn.close()
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit reached: {REQUESTS_PER_MINUTE} requests per minute",
        )
    conn.execute("INSERT INTO request_log(user_id) VALUES (?)", (caller["user_id"],))
    conn.commit()
    conn.close()
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

    # ---- GATE 4a — monthly token allowance (402) ----
    used = conn.execute(
        "SELECT COALESCE(SUM(tokens), 0) AS s FROM usage_events "
        "WHERE user_id = ? AND ts >= datetime('now', 'start of month')",
        (uid,),
    ).fetchone()["s"]
    allowance = conn.execute(
        "SELECT tokens_per_period AS t FROM subscription WHERE user_id = ?", (uid,)
    ).fetchone()["t"]
    if used + body.tokens > allowance:
        conn.close()
        raise HTTPException(
            status_code=402,
            detail=f"Monthly token quota exceeded: {used}/{allowance} used this month",
        )

    # ---- GATE 4b — prepaid credits (402), atomic spend ----
    cur = conn.execute(
        "UPDATE credits SET balance = balance - ? "
        "WHERE user_id = ? AND balance >= ?",
        (body.tokens, uid, body.tokens),
    )
    if cur.rowcount == 0:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=402, detail="Insufficient credits — please top up")

    # ---- HANDLER — the (simulated) expensive work ----
    conn.execute("INSERT INTO usage_events(user_id, tokens) VALUES (?, ?)",
                 (uid, body.tokens))
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
# GATE 2 — Authorization (403): you may only read your own usage
# --------------------------------------------------------------------------
@app.get("/v1/usage/{user_id}")
def usage(user_id: str, caller: dict = Depends(require_key)):
    if user_id != caller["user_id"]:
        raise HTTPException(status_code=403, detail="You may only view your own usage")
    conn = db()
    used = conn.execute(
        "SELECT COALESCE(SUM(tokens), 0) AS s FROM usage_events "
        "WHERE user_id = ? AND ts >= datetime('now', 'start of month')",
        (user_id,),
    ).fetchone()["s"]
    allowance = conn.execute(
        "SELECT tokens_per_period AS t FROM subscription WHERE user_id = ?", (user_id,)
    ).fetchone()["t"]
    credits = conn.execute(
        "SELECT balance AS b FROM credits WHERE user_id = ?", (user_id,)
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
    conn.execute("UPDATE credits SET balance = balance + ? WHERE user_id = ?",
                 (body.amount, caller["user_id"]))
    conn.commit()
    balance = conn.execute(
        "SELECT balance AS b FROM credits WHERE user_id = ?", (caller["user_id"],)
    ).fetchone()["b"]
    conn.close()
    return {"user_id": caller["user_id"], "credits": balance}


# --------------------------------------------------------------------------
# TEACHING HELPER (not production): reset the demo state between scenes
# --------------------------------------------------------------------------
@app.post("/_reset")
def reset():
    conn = db()
    conn.execute("DELETE FROM request_log")
    conn.execute("DELETE FROM usage_events")
    conn.execute("UPDATE credits SET balance = 1000 WHERE user_id = 'alice'")
    conn.execute("UPDATE credits SET balance = 600  WHERE user_id = 'bob'")
    conn.commit()
    conn.close()
    return {"reset": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
