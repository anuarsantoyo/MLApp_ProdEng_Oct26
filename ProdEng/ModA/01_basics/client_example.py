import requests

r1 = requests.get(f"http://127.0.0.1:8000/items/33")
print(r1.json())

































"""
print("\n--- 2. Testing Path Parameter & Optional Query Parameter GET ---")
# Hits /items/{item_id} with a query parameter ?q=fastapi
r2 = requests.get(f"{base_url}/items/42?q=fastapi")
print(r2.json())

print("\n--- 3. Testing Multiple Path Parameters GET ---")
# Hits /details/{item_id}/{name}/{color}
r3 = requests.get(f"{base_url}/details/7/backpack/blue")
print(r3.json())

print("\n--- 4. Testing POST Product Endpoint ---")
# Sends JSON data matching our Pydantic model
new_product = {
    "name": "Gaming Keyboard",
    "description": "Mechanical RGB keyboard",
    "price": 79.99,
    "tax":1.2
}
r4 = requests.post(f"{base_url}/products/", json=new_product)
print("Status Code:", r4.status_code)
print(r4.json())

"""