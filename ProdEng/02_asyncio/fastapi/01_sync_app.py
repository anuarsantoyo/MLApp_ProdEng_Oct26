# uvicorn ProdEng.02_asyncio.fastapi.01_sync_app:app --reload

import time

from fastapi import FastAPI

app = FastAPI()


def classify():
    time.sleep(1)


def lookup_profile():
    time.sleep(1)


def search_docs():
    time.sleep(1)


def generate_reply():
    time.sleep(1)


def save_result():
    time.sleep(1)


@app.get("/answer")
async def answer():
    classify()
    lookup_profile()
    search_docs()
    generate_reply()
    save_result()
    return {"answer": "done"}
