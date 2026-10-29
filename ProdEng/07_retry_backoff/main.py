# uvicorn ProdEng.07_retry_backoff.main:app --reload --port 8005
# (run from the repo root, or run `uvicorn main:app --reload --port 8005` inside this folder)
#
# Setup (once):
#   cp ProdEng/05_user_rag/data/app.db ProdEng/07_retry_backoff/data/app.db
#
# The dependency is the real user database next to this script:
#   ProdEng/07_retry_backoff/data/app.db
# Move it away while the server is running to break the dependency for real:
#   mv ProdEng/07_retry_backoff/data/app.db ProdEng/07_retry_backoff/data/app.db.bak
# Restore it with:
#   mv ProdEng/07_retry_backoff/data/app.db.bak ProdEng/07_retry_backoff/data/app.db

import random
import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException

DB_PATH = Path(__file__).with_name("data") / "app.db"
MAX_ATTEMPTS = 4
BASE_DELAY = 0.5  # seconds
JITTER_RATIO = 0.5  # add up to 50% of the backoff

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


def get_user_with_retry(user_id: int) -> dict | None:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            user = get_user(user_id)
            print(f"user {user_id} attempt {attempt} succeeded")
            return user
        except sqlite3.Error as error:
            if attempt == MAX_ATTEMPTS:
                print(f"user {user_id} attempt {attempt} failed, giving up: {error}")
                raise

            # Exponential backoff: 0.5 s, 1 s, 2 s.
            backoff = BASE_DELAY * attempt
            # Jitter spreads out clients that failed at the same moment.
            jitter = random.uniform(0, backoff * JITTER_RATIO)
            delay = backoff + jitter
            print(
                f"user {user_id} attempt {attempt} failed: {error} | "
                f"backoff {backoff:.2f}s + jitter {jitter:.2f}s = {delay:.2f}s"
            )
            # This is a blocking sleep so the demo is easy to watch.
            # A production service would use an async client and a retry library.
            time.sleep(delay)


# Example request:
# curl http://127.0.0.1:8005/users/1
@app.get("/users/{user_id}")
def lookup_user(user_id: int):
    try:
        user = get_user_with_retry(user_id)
    except sqlite3.Error as error:
        raise HTTPException(
            status_code=503,
            detail=f"database unavailable after {MAX_ATTEMPTS} attempts",
        ) from error

    # A missing user is not a dependency failure, so it is never retried.
    if user is None:
        raise HTTPException(status_code=404, detail=f"user {user_id} not found")
    return user
