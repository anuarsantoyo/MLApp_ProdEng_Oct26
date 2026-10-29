# python ProdEng/09_bulkhead/simple_semaphore.py
#
# The bulkhead in one idea: only two jobs may run at the same time.
# Try changing SLOTS to 6 and run it again.

import asyncio
import time

SLOTS = 2  # how many jobs may run at the same time
JOBS = 6  # how many jobs we start at the same time

slots = asyncio.Semaphore(SLOTS)


async def job(n: int) -> None:
    async with slots:  # wait here until a slot is free
        print(f"job {n} started")
        await asyncio.sleep(1)  # pretend the work takes one second
        print(f"job {n} done")


async def main() -> None:
    start = time.perf_counter()
    await asyncio.gather(*(job(n) for n in range(1, JOBS + 1)))
    print(f"all {JOBS} jobs done in {time.perf_counter() - start:.1f}s")


asyncio.run(main())
