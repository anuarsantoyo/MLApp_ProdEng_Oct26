import sys
from src.my_project.calculator import add, subtract, multiply, divide
import pytest

def test_add_positive_numbers():
    result = add(2, 3)
    assert result == 5

#@pytest.mark.xfail
def test_add_negative_numbers():
    result = add(-1, -5)
    assert result == -6

#@pytest.mark.skipif(sys.platform != "windows", reason= "Wrong system")
def test_subtract():
    result = subtract(10, 4)
    assert result == 6

#@pytest.mark.skip
def test_multiply():
    result = multiply(3, 6)
    assert result == 18

#@pytest.mark.slow
def test_divide():
    result = divide(10, 2)
    assert result == 5.0

def test_divide_by_zero():
    with pytest.raises(ValueError) as exc_info:
        divide(10, 0)
    assert str(exc_info.value) == "Cannot divide by zero"


@pytest.mark.parametrize("a,b,expected", [(10, 2, 5),(20, 4, 5),(100, 10, 10),(-10, 2, -5)])
def test_divide(a, b, expected):
    assert divide(a, b) == expected