import asyncio

from fastapi import FastAPI

app = FastAPI()

def say_hello():
    return "Hi"

async def classify():
    await asyncio.sleep(1)


async def lookup_profile():
    await asyncio.sleep(1)


async def search_docs():
    await asyncio.sleep(1)


async def generate_reply():
    await asyncio.sleep(1)


async def save_result():
    await asyncio.sleep(1)


@app.get("/answer")
async def answer():
    await asyncio.gather(classify(), lookup_profile(), search_docs(), generate_reply(), save_result())
    return {"answer": say_hello()}