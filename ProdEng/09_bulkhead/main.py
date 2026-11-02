# uvicorn ProdEng.09_bulkhead.main:app --reload --port 8007
# (run from the repo root, or run `uvicorn main:app --reload --port 8007` inside this folder)
#
# The bulkhead in one idea: only two charges can run at the same time.
# Send six at once from another terminal:
#   python ProdEng/09_bulkhead/client.py
#
# The older version, with a circuit breaker next to the bulkhead, is in
# main_with_breaker.py if you want that demo back.

import asyncio

from fastapi import FastAPI, HTTPException

MAX_CONCURRENT = 2  # how many charges may run at the same time
WAIT_TIMEOUT = 3  # seconds a request waits for a free slot
CHARGE_TIME = 1.0  # pretend the billing provider needs one second

# This semaphore is the bulkhead. Two permits means two charges at a time.
slots = asyncio.Semaphore(MAX_CONCURRENT)

charging = 0  # charges running right now
rejected = 0  # requests that could not get a slot

app = FastAPI()


# Example request:
# curl http://127.0.0.1:8007/status
@app.get("/status")
def status():
    return {
        "charging_now": charging,
        "rejected": rejected,
        "max_concurrent": MAX_CONCURRENT,
    }


# Example request:
# curl -X POST 'http://127.0.0.1:8007/charge/1?amount=25'
@app.post("/charge/{user_id}")
async def charge(user_id: int, amount: float = 10.0):
    global charging, rejected

    # 1. Wait for a free slot, but not forever.
    try:
        await asyncio.wait_for(slots.acquire(), timeout=WAIT_TIMEOUT)
    except TimeoutError:
        rejected += 1
        print(f"user {user_id} rejected, all {MAX_CONCURRENT} slots are busy")
        raise HTTPException(status_code=503, detail="too many charges at once")

    # 2. We hold a slot now. Do the work, then always give the slot back.
    charging += 1
    try:
        print(f"user {user_id} charging {amount}...")
        await asyncio.sleep(CHARGE_TIME)  # pretend the provider is slow
        print(f"user {user_id} charged {amount}")
        return {"user_id": user_id, "amount": amount, "charged": True}
    finally:
        charging -= 1
        slots.release()
