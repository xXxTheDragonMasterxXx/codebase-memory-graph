"""Basic arithmetic helpers used across the sample repository."""


def add(a, b):
    """Return the sum of a and b."""
    return a + b


def multiply(a, b):
    """Return the product of a and b, built on repeated addition."""
    result = 0
    for _ in range(b):
        result = add(result, a)
    return result


def square(x):
    """Return x squared."""
    return multiply(x, x)
