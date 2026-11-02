# python MLAppDev/sprint_3/seed.py
# (run from the repo root, or run `python seed.py` inside this folder)

import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).with_name("data")
DB_PATH = DATA_DIR / "app.db"

SCHEMA = """
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    user_name TEXT NOT NULL,
    country TEXT NOT NULL,
    city TEXT NOT NULL,
    role TEXT NOT NULL
);
"""

# Fake customers used by the example
USERS = [
    (1, "Ana Torres", "Mexico", "Mexico City", "owner"),
    (2, "Luis Mendez", "Spain", "Madrid", "billing_manager"),
    (3, "Priya Nair", "India", "Bengaluru", "agent"),
    (4, "Emma Chen", "Singapore", "Singapore", "admin"),
    (5, "Diego Ruiz", "Germany", "Berlin", "contractor"),
]


def create_db() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT INTO users (user_id, user_name, country, city, role) VALUES (?, ?, ?, ?, ?)",
            USERS,
        )
        conn.commit()
    finally:
        conn.close()


create_db()
print(f"User database ready at {DB_PATH} ({len(USERS)} users)")
