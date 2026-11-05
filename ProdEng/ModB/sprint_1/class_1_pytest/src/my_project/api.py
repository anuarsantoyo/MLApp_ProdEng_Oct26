# src/my_project/api.py
import requests

def fetch_status(url: str):
    """Fetch the 'status' field from a JSON API."""
    response = requests.get(url)

    return response.status_code