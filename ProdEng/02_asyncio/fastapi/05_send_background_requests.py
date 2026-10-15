import asyncio
import time

import httpx

BASE = "http://127.0.0.1:8000/answer"
start = time.perf_counter()


async def send_request(client, n):
    response = await client.post(f"{BASE}/async")
    job_id = response.json()["job_id"]
    print(f"request {n} acknowledged at {time.perf_counter() - start:.2f} s (HTTP {response.status_code})")

    job = await client.get(f"{BASE}/{job_id}")
    print(f"request {n} right away: {job.json()['status']}")

    await asyncio.sleep(2)

    job = await client.get(f"{BASE}/{job_id}")
    print(f"request {n} 2 s later:  {job.json()['status']}")


async def main():
    async with httpx.AsyncClient(timeout=60) as client:
        await asyncio.gather(
            send_request(client, 1),
            send_request(client, 2),
            send_request(client, 3),
            send_request(client, 4),
            send_request(client, 5),
        )


asyncio.run(main())
