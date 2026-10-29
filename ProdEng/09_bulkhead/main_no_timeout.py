# uvicorn ProdEng.09_bulkhead.main_no_timeout:app --reload --port 8007
# (run from the repo root, or run `uvicorn main_no_timeout:app --reload --port 8007` inside this folder)
#
# The same bulkhead as main.py, but with no wait_for. A request waits until a
# slot is free, however long that takes, so nothing is ever rejected.
# Send six at once from another terminal:
#   python ProdEng/09_bulkhead/client.py
#
# Compare with main.py: there the wait stops after 0.25s and four of the six
# requests get a 503 instead of waiting their turn.

import asyncio

from fastapi import FastAPI

MAX_CONCURRENT = 2  # how many charges may run at the same time
CHARGE_TIME = 1.0  # pretend the billing provider needs one second

# This semaphore is the bulkhead. Two permits means two charges at a time.
slots = asyncio.Semaphore(MAX_CONCURRENT)

charging = 0  # charges running right now

app = FastAPI()


# Example request:
# curl http://127.0.0.1:8007/status
@app.get("/status")
def status():
    return {"charging_now": charging, "max_concurrent": MAX_CONCURRENT}


# Example request:
# curl -X POST 'http://127.0.0.1:8007/charge/1?amount=25'
@app.post("/charge/{user_id}")
async def charge(user_id: int, amount: float = 10.0):
    global charging

    # No timeout here. This line returns only when a slot is free, and the
    # request just waits in line until then. So there is no 503 branch.
    async with slots:
        charging += 1
        try:
            print(f"user {user_id} charging {amount}...")
            await asyncio.sleep(CHARGE_TIME)  # pretend the provider is slow
            print(f"user {user_id} charged {amount}")
            return {"user_id": user_id, "amount": amount, "charged": True}
        finally:
            # async with gives the slot back by itself. This finally only keeps
            # the counter honest if the request is cancelled mid-charge.
            charging -= 1
