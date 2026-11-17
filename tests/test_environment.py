import itertools
import pytest

from pybelsberg import always, clear, environment, ConstraintError


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

    for country in countries:
        always(lambda: country.get_color() in CHOICES)

    for c1, c2 in itertools.combinations(countries, 2):
        if c1.is_neighbor_of(c2):
            always(lambda: c1.get_color() != c2.get_color())

    assert valid(countries)

    # one shared environment; the *combination* of all constraints holds
    for color in range(4):
        countries[0].set_color(color)
        assert valid(countries)


def test_constraints_add_up(Countries):
    countries = make_triangle(Countries)
    a, b, c = countries

    always(lambda: a.get_color() == 0)
    always(lambda: b.get_color() != a.get_color())

    # the second constraint had to move `b`, `a` stayed where the first put it
    assert int(a.color) == 0
    assert int(b.color) != 0

    always(lambda: c.get_color() == a.get_color())

    # all of them hold at once
    assert int(a.color) == 0
    assert int(c.color) == int(a.color)
    assert int(b.color) != int(a.color)

    # and a new assignment has to fit all of them: `c` goes with `a`,
    # which the first constraint keeps at 0
    with pytest.raises(ConstraintError):
        c.set_color(2)
    assert int(c.color) == int(a.color) == 0


def test_clear_forgets_the_constraints(Countries):
    countries = make_triangle(Countries)
    for country in countries:
        always(lambda: country.get_color() in CHOICES)

    with pytest.raises(ConstraintError):
        countries[0].set_color(9)

    clear()

    countries[0].set_color(9)  # nobody objects anymore
    assert int(countries[0].color) == 9
    assert environment.constraints == []
    assert list(environment.namespace.all_patches()) == []


def test_a_refused_constraint_leaves_the_environment_usable(Countries):
    a, b, _ = make_triangle(Countries)

    always(lambda: a.get_color() == 0)
    with pytest.raises(ConstraintError):
        always(lambda: a.get_color() == 1)

    # the impossible one was refused, the possible one is still in force
    assert int(a.color) == 0
    with pytest.raises(ConstraintError):
        a.set_color(3)

    always(lambda: b.get_color() != a.get_color())
    assert int(b.color) != 0


def test_constraints_after_a_clear_are_in_force(Countries):
    country, = make_triangle(Countries)[:1]

    always(lambda: country.get_color() in [0, 1])
    assert int(country.color) in [0, 1]

    clear()

    always(lambda: country.get_color() in [2, 3])  # object seen before
    assert int(country.color) in [2, 3]
    with pytest.raises(ConstraintError):
        country.set_color(0)


def test_invalid_assignment_rejected_atomically(Countries):
    countries = make_triangle(Countries)
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
