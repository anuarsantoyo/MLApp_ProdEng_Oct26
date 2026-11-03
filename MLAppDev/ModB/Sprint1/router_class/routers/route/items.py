# An APIRouter is a smaller FastAPI. Every decorator and argument you already
# know works here unchanged, so there is nothing new to learn.
# Look at what is missing: "/items". main.py adds it once, at plug-in time.
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

ITEMS = {1: {"name": "keyboard", "price": 40.0}, 2: {"name": "mouse", "price": 20.0}}


class Item(BaseModel):
    name: str
    price: float


@router.get("/")
def list_items():
    return ITEMS


@router.get("/{item_id}")
def get_item(item_id: int):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="item not found")
    return ITEMS[item_id]


@router.post("/", status_code=201)
def create_item(item: Item):
    item_id = len(ITEMS) + 1
    ITEMS[item_id] = item.model_dump()
    return {"item_id": item_id, **ITEMS[item_id]}
