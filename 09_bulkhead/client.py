# python ProdEng/09_bulkhead/client.py
# (run from the repo root, or run `python client.py` inside this folder)
#
# Sends six charges at once. With MAX_CONCURRENT = 2, two calls get a slot
# and four are rejected after WAIT_TIMEOUT.

import asyncio
import time

import httpx

BASE_URL = "http://127.0.0.1:8007"
REQUESTS = 10


async def charge(client: httpx.AsyncClient, n: int) -> None:
    start = time.perf_counter()
    response = await client.post(f"{BASE_URL}/charge/{n}")
    elapsed = time.perf_counter() - start
    body = response.json()
    detail = body.get("detail", body)
    print(f"request {n}: {response.status_code} in {elapsed:.2f}s {detail}")


async def main() -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        await asyncio.gather(*(charge(client, n) for n in range(1, REQUESTS + 1)))


asyncio.run(main())
