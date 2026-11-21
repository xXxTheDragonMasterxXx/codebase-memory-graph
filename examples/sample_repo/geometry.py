"""Simple geometry functions that build on the calculator module."""

from calculator import add, multiply, square


def rectangle_area(width, height):
    """Area of a rectangle."""
    return multiply(width, height)


def square_area(side):
    """Area of a square."""
    return square(side)


def perimeter(width, height):
    """Perimeter of a rectangle."""
    return multiply(add(width, height), 2)
