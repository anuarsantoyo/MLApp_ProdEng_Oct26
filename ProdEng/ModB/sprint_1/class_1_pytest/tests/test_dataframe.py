import pytest

def test_row_count(sample_dataframe):
    assert len(sample_dataframe) == 3

@pytest.mark.slow
def test_mean_age(sample_dataframe):
    assert sample_dataframe["age"].mean() == 30