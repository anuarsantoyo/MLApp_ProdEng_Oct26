# uvicorn ProdEng.06_circuit_breaker.main:app --reload --port 8004
# (run from the repo root, or run `uvicorn main:app --reload --port 8004` inside this folder)
#
# The dependency is the real user database next to this script:
#   ProdEng/06_circuit_breaker/data/app.db
# Delete that file while the server is running to break the dependency for real.
# Restore it with:
#   cp ProdEng/05_user_rag/data/app.db ProdEng/06_circuit_breaker/data/app.db

import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException

DB_PATH = Path(__file__).with_name("data") / "app.db"
FAILURE_THRESHOLD = 3
RECOVERY_TIMEOUT = 10.0  # 30 s in production, 1 s so the demo is quick

# The three states are CLOSED, OPEN and HALF_OPEN.
state = "CLOSED"
failures = 0
opened_at = 0.0

app = FastAPI()


def get_user(user_id: int) -> dict | None:
    # The real dependency. Read-only mode means a missing file raises instead
    # of letting SQLite create an empty database.
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT user_id, user_name, country, role FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


# Example request:
# curl http://127.0.0.1:8004/users/1
@app.get("/users/{user_id}")
def lookup_user(user_id: int):
    global state, failures, opened_at

    # 1. OPEN: reject before touching the database.
    if state == "OPEN":
        if time.perf_counter() - opened_at < RECOVERY_TIMEOUT:
            print("OPEN: request rejected instantly")
            raise HTTPException(status_code=503, detail="circuit open")
        print("OPEN: cooldown expired, moving to HALF_OPEN")
        state = "HALF_OPEN"

    # 2. CLOSED or HALF_OPEN: one real call to the database.
    print(f"{state}: calling the user database...")
    try:
        user = get_user(user_id)
    except sqlite3.Error as error:
        print(f"Database error: {error}")

        # A failed probe reopens at once. A normal failure counts up.
        if state == "HALF_OPEN":
            state = "OPEN"
            opened_at = time.perf_counter()
            print("HALF_OPEN probe failed, circuit is OPEN again")
            raise HTTPException(status_code=503, detail="database unavailable") from error

        failures += 1
        print(f"failure {failures}/{FAILURE_THRESHOLD}")
        if failures >= FAILURE_THRESHOLD:
            state = "OPEN"
            opened_at = time.perf_counter()
            print("Circuit is OPEN")
        raise HTTPException(status_code=503, detail="database unavailable") from error


    state = "CLOSED"
    failures = 0

    if user is None:
        raise HTTPException(status_code=404, detail=f"user {user_id} not found")
    return user
