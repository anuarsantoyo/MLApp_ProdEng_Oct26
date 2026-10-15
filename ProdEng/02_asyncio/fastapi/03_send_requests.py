import asyncio
import time

import httpx

start = time.perf_counter()


async def send_request(client, n):
    await client.post("http://127.0.0.1:8000/answer")
    print(f"request {n} finished at {time.perf_counter() - start:.2f} s")


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
