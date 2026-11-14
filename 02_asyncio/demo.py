import asyncio
import time

async def classify():
    await asyncio.sleep(0.1)

async def lookup_profile():
    await asyncio.sleep(0.2)

async def search_docs():
    await asyncio.sleep(0.3)

async def generate_reply():
    await asyncio.sleep(0.4)

async def save_result():
    await asyncio.sleep(0.5)

async def main():
    start = time.perf_counter()
    await asyncio.gather(classify(), lookup_profile(), search_docs(), generate_reply(), save_result())
    print(f"total {time.perf_counter() - start:.2f} s")

asyncio.run(main())
