# src/my_project/user.py

class User:
    """A simple user with name, email, and email-sending capability."""

    def __init__(self, name: str, email: str):
        if "@" not in email:
            raise ValueError("Invalid email address")
        self.name = name
        self.email = email

    def send_email(self, message: str) -> bool:
        """Real implementation would call an email service."""
        # ... actual sending logic ...
        return True

    def notify(self, message: str) -> bool:
        """Send a notification email to the user."""
        return self.send_email(message)