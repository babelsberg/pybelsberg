import itertools
import pytest

from pybelsberg import Solver, always, ConstraintError


@pytest.fixture
def Countries():
    class Country:
        def __init__(self, name):
            self.name = name
            self.color = 0
            self.neighbors = []

        def get_color(self):
            return self.color

        def set_color(self, value):
            self.color = value

        def is_neighbor_of(self, other):
            return other in self.neighbors

    return Country


CHOICES = [0, 1, 2, 3]  # module level, like the demo's COLORS


def make_triangle(Country):
    a, b, c = Country("A"), Country("B"), Country("C")
    for x, y in itertools.combinations((a, b, c), 2):  # triangle
        x.neighbors.append(y)
        y.neighbors.append(x)
    return [a, b, c]


def valid(countries):
    colors = {c.name: int(c.color) for c in countries}
    for c in countries:
        if colors[c.name] not in CHOICES:
            return False
        for n in c.neighbors:
            if colors[c.name] == colors[n.name]:
                return False
    return True


def test_js_demo_shape_per_block_always(Countries):
    countries = make_triangle(Countries)

    with Solver():
        for country in countries:
            always(lambda: country.get_color() in CHOICES)

        for c1, c2 in itertools.combinations(countries, 2):
            if c1.is_neighbor_of(c2):
                always(lambda: c1.get_color() != c2.get_color())

    assert valid(countries)

    # one shared solve; the *combination* of all blocks stays satisfied
    for color in range(4):
        countries[0].set_color(color)
        assert valid(countries)


def test_invalid_assignment_rejected_atomically(Countries):
    countries = make_triangle(Countries)

    with Solver():
        for country in countries:
            always(lambda: country.get_color() in CHOICES)

    with pytest.raises(ConstraintError):
        countries[0].set_color(9)  # not a choice

    # the rejected write did not happen
    assert int(countries[0].color) in CHOICES


def test_membership_in_operator_directly():
    class Item:
        pass

    item = Item()
    item.color = 0

    always(lambda: item.color in CHOICES)  # not even a generator needed

    assert item.color in CHOICES
    with pytest.raises(ConstraintError):
        item.color = 7
