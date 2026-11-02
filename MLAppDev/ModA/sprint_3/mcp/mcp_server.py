# uvicorn MLAppDev.sprint_3.mcp.mcp_server:app --reload --port 8000
# (run from the repo root, or run `uvicorn mcp_server:app --reload --port 8000` inside this folder)

import sqlite3
from pathlib import Path

import requests
from mcp.server import MCPServer

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "app.db"

mcp = MCPServer("city-weather")


@mcp.tool()
def get_city(user_id: int) -> dict:
    """Look up the city of a user in the database. Takes the numeric user_id.

    Use this when you need the city of the current user, for example when the
    question asks about the weather today without naming a city.
    If the user has not given you a user_id, ask them for it first.
    Never guess an id.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT user_id, user_name, country, city FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else {"error": f"user {user_id} not found"}


@mcp.tool()
def get_weather(city: str) -> dict:
    """Current temperature in Celsius for a city, from the weather service."""
    response = requests.get(f"https://wttr.in/{city}?format=%t", timeout=20)
    return {"city": city, "temperature": response.text.strip()}


app = mcp.streamable_http_app(streamable_http_path="/mcp", host="127.0.0.1")
