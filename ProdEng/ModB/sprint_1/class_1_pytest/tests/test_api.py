# tests/test_api.py
from src.my_project.api import fetch_status

def test_api_call(mocker):
    # Patch requests.get where it is looked up (in my_project.api)
    mock_get = mocker.patch("src.my_project.api.requests.get")
    mock_get.return_value.status_code = 200

    result = fetch_status("google.com")

    assert result == 200