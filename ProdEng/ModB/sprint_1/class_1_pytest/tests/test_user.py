# tests/test_user.py
import pytest

class TestUser:
    """Group related tests in a class."""

    def test_create_user(self,sample_user):
        user = sample_user
        assert user.name == "Alice"

    def test_user_email(self,sample_user):
        user = sample_user
        assert user.email == "alice@example.com"

