"""Entry point that ties the sample modules together."""

from geometry import perimeter, rectangle_area, square_area


def report(width, height):
    """Build a one-line report of a rectangle's area and perimeter."""
    area = rectangle_area(width, height)
    per = perimeter(width, height)
    return f"area={area} perimeter={per}"


def main():
    """Print a couple of sample computations."""
    print(report(3, 4))
    print(square_area(5))


if __name__ == "__main__":
    main()
