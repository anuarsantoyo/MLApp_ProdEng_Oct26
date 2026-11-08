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
DROP TABLE IF EXISTS usage_events;
DROP TABLE IF EXISTS credits;
DROP TABLE IF EXISTS subscription;
DROP TABLE IF EXISTS api_keys;
DROP TABLE IF EXISTS users;

-- who can call
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    name    TEXT NOT NULL,
    plan    TEXT NOT NULL
);

-- caller keys (store the hash, never the key)
CREATE TABLE api_keys (
    key_hash TEXT PRIMARY KEY,
    user_id  TEXT NOT NULL REFERENCES users(user_id)
);

-- monthly plan: how many tokens you may spend per billing period
CREATE TABLE subscription (
    user_id           TEXT PRIMARY KEY REFERENCES users(user_id),
    tokens_per_period INTEGER NOT NULL
);

-- prepaid balance (the "top up" simulation)
CREATE TABLE credits (
    user_id TEXT PRIMARY KEY REFERENCES users(user_id),
    balance INTEGER NOT NULL
);

-- a ledger: every successful call records how many tokens it cost
CREATE TABLE usage_events (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    tokens  INTEGER NOT NULL,
    ts      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- every request that reaches the rate limiter (even ones that later fail)
CREATE TABLE request_log (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    ts      TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# user_id, name, plan, plaintext_key, tokens_per_period, credits
USERS = [
    ("alice", "Alice", "pro",  "alice-123", 5000, 1000),
    ("bob",   "Bob",   "free", "bob-456",   2000,  600),
]


def create() -> None:
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)
    for user_id, name, plan, key, allowance, credit in USERS:
        conn.execute("INSERT INTO users(user_id, name, plan) VALUES (?, ?, ?)",
                     (user_id, name, plan))
        conn.execute("INSERT INTO api_keys(key_hash, user_id) VALUES (?, ?)",
                     (sha256(key), user_id))
        conn.execute("INSERT INTO subscription(user_id, tokens_per_period) VALUES (?, ?)",
                     (user_id, allowance))
        conn.execute("INSERT INTO credits(user_id, balance) VALUES (?, ?)",
                     (user_id, credit))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    create()
    print(f"Created {DB}\n")
    print("Seeded callers (send these keys in the x-api-key header):\n")
    print(f"  {'name':<6} {'key':<12} {'plan':<10} {'monthly tokens':<16} credits")
    for user_id, name, plan, key, allowance, credit in USERS:
        print(f"  {name:<6} {key:<12} {plan:<10} {allowance:<16} {credit}")
    print(f"\nRate limit in the app: computed live (see app.py, REQUESTS_PER_MINUTE).")
