# ILLUSTRATIVE ONLY: no real authentication, no real database, no tests.
#
# Run it from the repo root:
#   uvicorn MLAppDev.ModB.Sprint1.server:app --reload --port 8010
# or from inside this folder (and from the repo root with --app-dir MLAppDev/ModB/Sprint1):
#   uvicorn server:app --reload --port 8010
#
# Then, in another terminal, run the client that handles every status:
# open MLAppDev/ModB/Sprint1/app.ipynb and run the cells in order.
#
# The point of this file is the status code, not the code around it.
# Every endpoint is two or three lines and its comment says which status it
# produces and when that status is the correct answer.
#
# Statuses covered:
#   200 OK                    GET /items/1
#   201 Created               POST /items
#   202 Accepted              POST /jobs
#   400 Bad Request           GET /divide?b=0
#   401 Unauthorized          GET /admin
#   402 Payment Required      GET /checkout?price=50  (custom exception handler)
#   403 Forbidden             GET /admin?token=ana
#   404 Not Found             GET /items/99
#   405 Method Not Allowed    POST /items/1  (only GET exists)
#   409 Conflict              POST /orders?item_name=keyboard
#   418 I'm a teapot          GET /teapot
#   422 Unprocessable Entity  POST /items with a bad body (FastAPI does it for us)
#   429 Too Many Requests     GET /limited  (more than 3 calls in 2 seconds)
#   500 Internal Server Error GET /boom  (unhandled exception)
#   502 Bad Gateway           POST /ask with model not/a-real-model
#   503 Service Unavailable   GET /dependency
#   504 Gateway Timeout       GET /upstream-slow

import math
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
from pydantic import BaseModel

# The .env lives at the repo root: ModB/Sprint1 -> ModB -> MLAppDev -> repo root
ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")
API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"
CHAT_MODEL = "google/gemini-2.5-flash-lite"

app = FastAPI(title="HTTP status playground")

# Fake data. Enough to make the statuses real instead of hardcoded responses.
ITEMS = {
    1: {"name": "keyboard", "price": 40.0},
    2: {"name": "mouse", "price": 20.0},
}
STOCK = {"keyboard": 0, "mouse": 5}

# Rate limiting, the simple version: 3 calls per 2 seconds, per process.
LIMIT = 3
WINDOW = 2.0  # seconds
window_start = time.perf_counter()
limited_calls = 0


class Item(BaseModel):
    name: str
    price: float


# ---------------------------------------------------------------- 2xx success

# 201 Created: the item now exists, and the Location header points to it.
# Example request:
# curl -i -X POST http://127.0.0.1:8010/items -H "Content-Type: application/json" -d '{"name": "monitor", "price": 150}'
@app.post("/items", status_code=201)
def create_item(item: Item, response: Response):
    item_id = len(ITEMS) + 1
    ITEMS[item_id] = item.model_dump()
    response.headers["Location"] = f"/items/{item_id}"
    return {"item_id": item_id, **ITEMS[item_id]}


# 202 Accepted: we took the job but it is not finished. 200 would be a lie here.
# Example request:
# curl -i -X POST http://127.0.0.1:8010/jobs
@app.post("/jobs", status_code=202)
def start_job():
    return {"job_id": 42, "status": "queued"}


# ------------------------------------------------------------ 4xx: the client

# 200 when it exists, 404 when it does not. The detail is for the human reading it.
# Example request:
# curl -i http://127.0.0.1:8010/items/1
@app.get("/items/{item_id}")
def read_item(item_id: int):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail=f"item {item_id} not found")
    return {"item_id": item_id, **ITEMS[item_id]}


# 422 Unprocessable Entity: nothing to write. FastAPI checks the body against the
# Item model and answers 422 by itself, with one entry per bad field.
# Example request (the POST /items endpoint above, with price missing):
# curl -i -X POST http://127.0.0.1:8010/items -H "Content-Type: application/json" -d '{"name": "monitor"}'


# 401 without a token, 403 with a valid but non-admin token.
# 401 means "I do not know who you are". 403 means "I know you, and no".
# Example requests:
# curl -i http://127.0.0.1:8010/admin
# curl -i "http://127.0.0.1:8010/admin?token=ana"
@app.get("/admin")
def admin(token: str | None = None):
    if token is None:
        # The header tells the client how to authenticate.
        raise HTTPException(
            status_code=401,
            detail="missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if token != "admin":
        raise HTTPException(status_code=403, detail="you are not an admin")
    return {"message": "welcome, admin"}


# 409 Conflict: the request is valid, but it clashes with the current state.
# Example request:
# curl -i -X POST "http://127.0.0.1:8010/orders?item_name=keyboard"
@app.post("/orders")
def create_order(item_name: str = "keyboard"):
    if STOCK.get(item_name, 0) <= 0:
        raise HTTPException(status_code=409, detail=f"{item_name} is out of stock")
    STOCK[item_name] -= 1
    return {"item_name": item_name, "left": STOCK[item_name]}


# 400 Bad Request: the input passed validation but breaks a business rule.
# 422 would be wrong here, the types are fine, dividing by zero is the problem.
# Example request:
# curl -i "http://127.0.0.1:8010/divide?b=0"
@app.get("/divide")
def divide(a: float = 1.0, b: float = 1.0):
    if b == 0:
        raise HTTPException(status_code=400, detail="b cannot be zero")
    return {"result": a / b}


# 429 Too Many Requests, plus Retry-After so the client knows how long to wait.
# Example request (call it four times in a row):
# curl -i http://127.0.0.1:8010/limited
@app.get("/limited")
def limited():
    global limited_calls, window_start

    now = time.perf_counter()
    if now - window_start >= WINDOW:  # new window, the counter starts again
        window_start = now
        limited_calls = 0
    limited_calls += 1

    if limited_calls > LIMIT:
        wait = math.ceil(window_start + WINDOW - now)
        raise HTTPException(
            status_code=429,
            detail=f"more than {LIMIT} calls in {WINDOW}s",
            headers={"Retry-After": str(wait)},
        )
    return {"call": limited_calls, "limit": LIMIT}


# 418: any code you like exists, this one is a joke from the HTTP spec.
# Example request:
# curl -i http://127.0.0.1:8010/teapot
@app.get("/teapot")
def teapot():
    raise HTTPException(status_code=418, detail="I'm a teapot")


# ------------------------------------------------------------ 5xx: the server

# 500: no HTTPException, just a crash. FastAPI logs the traceback and the client
# only sees "Internal Server Error", never the internals.
# Example request:
# curl -i http://127.0.0.1:8010/boom
@app.get("/boom")
def boom():
    return 1 / 0


# 503: a dependency we need is down. It is temporary, so the client may retry.
# Example request:
# curl -i http://127.0.0.1:8010/dependency
@app.get("/dependency")
def dependency():
    raise HTTPException(status_code=503, detail="dependency is down")


# 504: we waited for something upstream and it never answered.
# Simulated with a sleep so the demo is not flaky.
# Example request:
# curl -i http://127.0.0.1:8010/upstream-slow
@app.get("/upstream-slow")
def upstream_slow():
    time.sleep(1)
    raise HTTPException(status_code=504, detail="upstream did not answer in time")


# ------------------------- turning a domain error into a status code (402)

class InsufficientFunds(Exception):
    def __init__(self, balance: float, price: float):
        self.balance = balance
        self.price = price


# One handler for one error type. The body here is ours, not FastAPI's {"detail": ...}
@app.exception_handler(InsufficientFunds)
def insufficient_funds_handler(request: Request, error: InsufficientFunds):
    return JSONResponse(
        status_code=402,
        content={
            "error": "insufficient_funds",
            "balance": error.balance,
            "price": error.price,
        },
    )


# 200 if the balance covers it, 402 if it does not.
# Example request:
# curl -i "http://127.0.0.1:8010/checkout?price=50"
@app.get("/checkout")
def checkout(price: float):
    balance = 10.0
    if price > balance:
        raise InsufficientFunds(balance, price)
    return {"charged": price, "balance": balance - price}


# --------------------------------------- 200 or 502 against a real provider

class AskRequest(BaseModel):
    question: str
    model: str = CHAT_MODEL


# 200 when OpenRouter answers. When OpenRouter fails, the failure is not our
# client's fault, so we answer 502 Bad Gateway and pass the upstream message on.
# Example requests:
# curl -i -X POST http://127.0.0.1:8010/ask -H "Content-Type: application/json" -d '{"question": "What does HTTP 502 mean?"}'
# curl -i -X POST http://127.0.0.1:8010/ask -H "Content-Type: application/json" -d '{"question": "hi", "model": "not/a-real-model"}'
@app.post("/ask")
def ask(request: AskRequest):
    if not API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OPENROUTER_API_KEY is missing. Add it to the .env file at the repo root.",
        )

    client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=30)
    try:
        completion = client.chat.completions.create(
            model=request.model,
            messages=[{"role": "user", "content": request.question}],
            temperature=0,
        )
    except APITimeoutError as error:
        raise HTTPException(status_code=504, detail="OpenRouter took too long") from error
    except APIConnectionError as error:
        raise HTTPException(status_code=502, detail="cannot reach OpenRouter") from error
    except APIStatusError as error:
        # Bad model, no credits, rate limit, bad key: the provider said no.
        # error.body is the JSON OpenRouter sent back, so we forward only its message.
        message = error.body.get("message") if isinstance(error.body, dict) else error.message
        raise HTTPException(
            status_code=502,
            detail=f"OpenRouter answered {error.status_code}: {message}",
        ) from error

    return {"model": request.model, "answer": completion.choices[0].message.content}
