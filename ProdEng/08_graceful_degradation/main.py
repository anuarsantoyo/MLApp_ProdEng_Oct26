# uvicorn ProdEng.08_graceful_degradation.main:app --reload --port 8006
# (run from the repo root, or run `uvicorn main:app --reload --port 8006` inside this folder)
#
# Setup (once):
#   cp ProdEng/05_user_rag/data/app.db ProdEng/08_graceful_degradation/data/app.db
#
# The dependency is the real user database next to this script:
#   ProdEng/08_graceful_degradation/data/app.db
# Move it away while the server is running to break the dependency for real:
#   mv ProdEng/08_graceful_degradation/data/app.db ProdEng/08_graceful_degradation/data/app.db.bak
# Restore it with:
#   mv ProdEng/08_graceful_degradation/data/app.db.bak ProdEng/08_graceful_degradation/data/app.db

import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

DB_PATH = Path(__file__).with_name("data") / "app.db"
FAILURE_THRESHOLD = 3
RECOVERY_TIMEOUT = 1.0  # 30 s in production, 1 s so the demo is quick

# The three states are CLOSED, OPEN and HALF_OPEN.
state = "CLOSED"
failures = 0
opened_at = 0.0

# The fallback for graceful degradation. It starts empty and is filled by
# successful reads, so it only contains data this process has actually seen.
users_cache: dict[int, dict] = {}

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


def database_is_healthy() -> bool:
    # Health checks test the dependency directly, not the breaker or the cache.
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        try:
            conn.execute("SELECT 1 FROM users LIMIT 1").fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return False
    return True


def user_response(user: dict, source: str) -> dict:
    return {
        "user": user,
        "source": source,
        "degraded": source == "cache",
    }


def cached_user(user_id: int) -> dict | None:
    cached = users_cache.get(user_id)
    if cached is not None:
        print(f"Serving user {user_id} from cache")
    return cached


# Example request:
# curl http://127.0.0.1:8006/health
@app.get("/health")
def health():
    database_ok = database_is_healthy()
    body = {
        "status": "ok" if database_ok else "degraded",
        "database": "ok" if database_ok else "unavailable",
        "circuit": state,
    }
    if not database_ok:
        print("Health: database unavailable")
        return JSONResponse(status_code=503, content=body)
    return body


# Example request:
# curl http://127.0.0.1:8006/users/1
@app.get("/users/{user_id}")
def lookup_user(user_id: int):
    global state, failures, opened_at

    # 1. OPEN: do not touch the database. Serve the fallback if we have it.
    if state == "OPEN":
        if time.perf_counter() - opened_at < RECOVERY_TIMEOUT:
            print("OPEN: request rejected instantly")
            cached = cached_user(user_id)
            if cached is not None:
                return user_response(cached, "cache")
            raise HTTPException(status_code=503, detail="circuit open and no cached user")
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
        else:
            failures += 1
            print(f"failure {failures}/{FAILURE_THRESHOLD}")
            if failures >= FAILURE_THRESHOLD:
                state = "OPEN"
                opened_at = time.perf_counter()
                print("Circuit is OPEN")

        cached = cached_user(user_id)
        if cached is not None:
            return user_response(cached, "cache")
        raise HTTPException(
            status_code=503, detail="database unavailable and no cached user"
        ) from error

    # 3. Success: the database answered, so close the circuit and refresh the cache.
    if state == "HALF_OPEN":
        print("Probe succeeded, circuit is CLOSED")
    state = "CLOSED"
    failures = 0

    if user is None:
        raise HTTPException(status_code=404, detail=f"user {user_id} not found")

    users_cache[user_id] = user
    return user_response(user, "database")
