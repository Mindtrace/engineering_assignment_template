import pytest
from mindtrace.utils import multithread


# Sample functions to test with the decorator
@multithread(num_threads=4)
def add_numbers(a, b):
    return a + b

@multithread(num_threads=4)
def multiply_numbers(a, b, c):
    return a * b * c

@multithread(num_threads=4)
def concat_strings(s1, s2):
    """Concatenates two strings."""
    return s1 + s2

@multithread(num_threads=4)
def process_data(x, y, z):
    """Returns a dictionary with sum and product of three numbers."""
    return {"sum": x + y + z, "product": x * y * z}

# ---- TEST CASES ----

def test_single_execution():
    """Test normal function execution without multithreading."""
    assert add_numbers(2, 3) == 5
    assert multiply_numbers(2, 3, 4) == 24
    assert concat_strings("Hello, ", "World!") == "Hello, World!"
    assert process_data(1, 2, 3) == {"sum": 6, "product": 6}

def test_batch_execution_with_tuples():
    """Test batch execution with positional arguments (list of tuples)."""
    batch_args = [(1, 2), (3, 4), (5, 6)]
    results = add_numbers(batch_args)
    assert results == [3, 7, 11]

    batch_args_multi = [(1, 2, 3), (4, 5, 6), (7, 8, 9)]
    results = multiply_numbers(batch_args_multi)
    assert results == [6, 120, 504]

def test_batch_execution_with_dicts():
    """Test batch execution with keyword arguments (list of dicts)."""
    batch_kwargs = [
        {"x": 1, "y": 2, "z": 3},
        {"x": 4, "y": 5, "z": 6},
        {"x": 7, "y": 8, "z": 9}
    ]
    results = process_data(batch_kwargs)
    assert results == [
        {"sum": 6, "product": 6},
        {"sum": 15, "product": 120},
        {"sum": 24, "product": 504}
    ]

def test_batch_execution_with_tasks_keyword():
    """Test batch execution using 'tasks' keyword argument."""
    batch_kwargs = [
        {"x": 1, "y": 2, "z": 3},
        {"x": 4, "y": 5, "z": 6},
        {"x": 7, "y": 8, "z": 9}
    ]
    results = process_data(tasks=batch_kwargs)
    assert results == [
        {"sum": 6, "product": 6},
        {"sum": 15, "product": 120},
        {"sum": 24, "product": 504}
    ]

def test_batch_execution_with_strings():
    """Test batch execution with string concatenation."""
    batch_args = [("Hello, ", "World!"), ("Good ", "Morning"), ("Pytest ", "Rocks")]
    results = concat_strings(batch_args)
    assert results == ["Hello, World!", "Good Morning", "Pytest Rocks"]

def test_empty_batch():
    """Test handling of an empty batch."""
    assert add_numbers([]) == []
    assert multiply_numbers([]) == []
    assert process_data([]) == []
    
def test_invalid_input():
    """Test invalid inputs that should raise exceptions."""
    with pytest.raises(TypeError):
        process_data("string instead of list")  # Invalid type

    with pytest.raises(TypeError):
        process_data(123)  # Invalid non-iterable input

    with pytest.raises(TypeError):
        add_numbers([1, 2, 3])  # Should be list of tuples

def test_mixed_inputs():
    """Test passing mixed argument formats, should handle normally."""
    batch_mixed = [(1, 2), {"x": 3, "y": 4, "z": 5}]
    with pytest.raises(TypeError):  # Expect failure due to inconsistent format
        process_data(batch_mixed)

if __name__ == "__main__":
    pytest.main()