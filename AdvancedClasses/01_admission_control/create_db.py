"""Class 1 — create and seed the SQLite database.

Run this first. It drops and recreates the tables, then seeds two callers
(Alice and Bob) with hashed API keys, a monthly token allowance, and a
prepaid credit balance.

    python create_db.py
"""
import os
import sqlite3
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "class1.db")

# In real life you store a HASH of the key, never the key itself.
def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

SCHEMA = """
DROP TABLE IF EXISTS request_log;
DROP TABLE IF EXISTS usage;
DROP TABLE IF EXISTS users;

-- who can call: their key (hashed), their monthly allowance, their balance
CREATE TABLE users (
    user_id        TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    key_hash       TEXT NOT NULL,      -- SHA-256 of the key, never the key itself
    monthly_tokens INTEGER NOT NULL,   -- allowance per month
    credits        INTEGER NOT NULL    -- prepaid balance (top-up)
);

-- a ledger: every successful call records how many tokens it cost
CREATE TABLE usage (
    user_id TEXT NOT NULL,
    tokens  INTEGER NOT NULL,
    ts      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- every request that reaches the rate limiter (even ones that later fail)
CREATE TABLE request_log (
    user_id TEXT NOT NULL,
    ts      TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# user_id, name, plaintext_key, monthly_tokens, credits
USERS = [
    ("alice", "Alice", "alice-123", 5000, 1000),
    ("bob",   "Bob",   "bob-456",   2000,  600),
]


def create() -> None:
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)
    for user_id, name, key, monthly, credits in USERS:
        conn.execute(
            "INSERT INTO users(user_id, name, key_hash, monthly_tokens, credits) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, name, sha256(key), monthly, credits),
        )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    create()
    print(f"Created {DB}\n")
    print("Seeded callers (send these keys in the x-api-key header):\n")
    print(f"  {'name':<6} {'key':<12} {'monthly tokens':<16} credits")
    for user_id, name, key, monthly, credits in USERS:
        print(f"  {name:<6} {key:<12} {monthly:<16} {credits}")
    print("\nRate limit: see app.py (REQUESTS_PER_MINUTE).")
