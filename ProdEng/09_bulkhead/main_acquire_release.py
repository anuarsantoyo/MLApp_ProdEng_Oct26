# uvicorn ProdEng.09_bulkhead.main_acquire_release:app --reload --port 8007
# (run from the repo root, or run `uvicorn main_acquire_release:app --reload --port 8007` inside this folder)
#
# The same bulkhead as main_no_timeout.py, but written with the explicit
# acquire/release calls instead of `async with slots:`. Same behaviour, same
# timing, only the two lines that `async with` was hiding are now visible.
# Send six at once from another terminal:
#   python ProdEng/09_bulkhead/client.py
#
# Three versions to compare:
#   main.py                    bounded wait, four requests get a 503
#   main_no_timeout.py         unbounded wait, `async with slots:`
#   main_acquire_release.py    unbounded wait, explicit acquire and release

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
    slots.release()
    return {"charging_now": charging, "max_concurrent": MAX_CONCURRENT}


# Example request:
# curl -X POST 'http://127.0.0.1:8007/charge/1?amount=25'
@app.post("/charge/{user_id}")
async def charge(user_id: int, amount: float = 10.0):
    global charging

    # No timeout here, so this await returns only when a slot is free.
    # This is the line that `async with slots:` was running for us.
    await slots.acquire()
    try:
        charging += 1
        print(f"user {user_id} charging {amount}...")
        await asyncio.sleep(CHARGE_TIME)  # pretend the provider is slow
        print(f"user {user_id} charged {amount}")
        return {"user_id": user_id, "amount": amount, "charged": True}
    finally:
        charging -= 1
        # This is the other line `async with` was hiding. It must run on every
        # path, including errors and cancellation, or the slot is lost forever.
        slots.release()
