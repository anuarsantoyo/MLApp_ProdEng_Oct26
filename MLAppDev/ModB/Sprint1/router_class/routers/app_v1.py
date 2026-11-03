# uvicorn MLAppDev.ModB.Sprint1.router_class.routers.app_v1:app --reload --port 8011     (run from this folder)
#
# The "before". Every route lives in one file, "/items" is written three times,
# and FastAPI has no idea these routes belong together.
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="routers demo")

ITEMS = {1: {"name": "keyboard", "price": 40.0}, 2: {"name": "mouse", "price": 20.0}}


class Item(BaseModel):
    name: str
    price: float


@app.get("/items/")
def list_items():
    return ITEMS


@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="item not found")
    return ITEMS[item_id]


@app.post("/items/", status_code=201)
def create_item(item: Item):
    item_id = len(ITEMS) + 1
    ITEMS[item_id] = item.model_dump()
    return {"item_id": item_id, **ITEMS[item_id]}


@app.get("/health/")
def health():
    return {"status": "ok"}
