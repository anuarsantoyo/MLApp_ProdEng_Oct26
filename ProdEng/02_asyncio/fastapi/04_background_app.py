import asyncio

from fastapi import BackgroundTasks, FastAPI

app = FastAPI()

jobs = {}


async def classify():
    await asyncio.sleep(5)


async def lookup_profile():
    await asyncio.sleep(2)


async def search_docs():
    await asyncio.sleep(2)


async def generate_reply():
    await asyncio.sleep(2)


async def save_result():
    await asyncio.sleep(2)


async def finish(job_id):
    await lookup_profile()
    await search_docs()
    await generate_reply()
    await save_result()
    jobs[job_id] = "finished"


@app.get("/answer/async", status_code=202)
async def answer_async(background_tasks: BackgroundTasks):
    await classify()
    background_tasks.add_task(finish, 3)
    return {"job_id": "true"}


@app.get("/answer/{job_id}")
async def get_job(job_id: int):
    return {"status": jobs[job_id]}
