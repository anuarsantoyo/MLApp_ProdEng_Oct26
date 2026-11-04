def test_row_count(sample_dataframe):
    assert len(sample_dataframe) == 3

def test_mean_age(sample_dataframe):
    assert sample_dataframe["age"].mean() == 30