from fastapi import FastAPI
from pydantic import BaseModel
import json

app = FastAPI()

@app.get("/")
def read_root():
  return {"message": "Hello World"}

# 2. Path Parameter (e.g., /items/42)
# FastAPI automatically validates that 'item_id' is an integer.
@app.get("/items/{item_id}")
def read_item(item_id: int):
  return {"item_id": item_id*10}


@app.get("/details/{item_id}/{name}/{color}")
def read_item(item_id: int, name: str, color: str):
  result = item_id*name + color

  return {"item_id": item_id, "name": name, "color": color, "result":result}




# 1. Define the shape of the data you want to receive using Pydantic
class Item(BaseModel):
  name: str
  description: str | None = None
  price: float
  tax: float | None = None


# 2. Create a POST endpoint
@app.post("/products/")
def create_item(item: Item):
  # FastAPI automatically parses the incoming JSON into the 'Item' model
  # You can access attributes like item.name, item.price, etc.
  
  item_json_string = item.model_dump_json()

  with open(f"ProdEng/items/{item.name}.json", "w") as f:
    json.dump(item_json_string, f, indent=4)

  # Let's calculate total price with tax if tax is provided
  total_price = item.price
  if item.tax:
    total_price += item.tax

  return {
      "message": "Item created successfully!",
      "item": item,
      "total_price": total_price,
  }





"""

  item_json_string = item.model_dump_json()
  with open(f"ProdEng/items/{item.name}.json", "w") as f:
    json.dump(item_json_string, f, indent=4)'''

# curl -X POST http://127.0.0.1:8000/products/ -H "Content-Type: application/json" -d '{"title": "Mouse", "price": 10.0}'
"""