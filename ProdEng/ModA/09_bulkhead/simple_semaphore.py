# python ProdEng/09_bulkhead/simple_semaphore.py
#
# The bulkhead in one idea: only two jobs may run at the same time.
# Try changing SLOTS to 6 and run it again.

import asyncio
import time
import random


SLOTS = 4  # how many jobs may run at the same time
JOBS = 10  # how many jobs we start at the same time

slots = asyncio.Semaphore(SLOTS)


async def job(n: int) -> None:
    async with slots:  # wait here until a slot is free
        start = time.perf_counter()
        print(f"job {n} started")
        await asyncio.sleep(1 + random.random())  # pretend the work takes one second
        print(f"job {n} stared at {start} ended at {time.perf_counter()}")


async def main() -> None:
    start = time.perf_counter()
    await asyncio.gather(*(job(n) for n in range(1, JOBS + 1)))
    print(f"all {JOBS} jobs done in {time.perf_counter() - start:.1f}s")


asyncio.run(main())
