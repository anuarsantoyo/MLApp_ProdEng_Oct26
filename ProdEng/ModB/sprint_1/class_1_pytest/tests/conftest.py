import pytest
from src.my_project.user import User
import pandas as pd

@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User("Alice", "alice@example.com")




@pytest.fixture
def sample_dataframe():
    """Create a DataFrame, share it with the test, then discard it."""
    df = pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie"],
        "age": [25, 30, 35],
    })
    yield df                        # Test runs here
    df.drop(df.index, inplace=True) # Empty out the rows
    del df                          # Release the reference

