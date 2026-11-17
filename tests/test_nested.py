import math
import pytest

from pybelsberg import always, ConstraintError, environment


@pytest.fixture
def Point():
    class Point:
        def __init__(self, x, y):
            self.x = x
            self.y = y

        def __sub__(self, other):
            return Point(self.x - other.x, self.y - other.y)

        def distance(self, other):
            return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    return Point


@pytest.fixture
def Rectangle():
    class Rectangle:
        def __init__(self, top_left, bottom_right):
            self.top_left = top_left
            self.bottom_right = bottom_right

    return Rectangle


def patch_roles(id_to_role):
    """The patched (role, attribute) pairs of the global environment"""
    return {(id_to_role[id(obj)], key)
            for (obj, key), _ in environment.namespace.all_patches()}


def test_nested_point_attributes_are_wrapped(Point, Rectangle, almost):
    rect = Rectangle(Point(0, 0), Point(30, 40))
    b = Point(0, 0)

    always(lambda: (rect.bottom_right - rect.top_left).distance(b) == 50)

    # every patch belongs to a real corner or to `b`, never to a temp
    roles = {id(rect.top_left): 'tl', id(rect.bottom_right): 'br', id(b): 'b'}
    assert patch_roles(roles) == {
        ('tl', 'x'), ('tl', 'y'), ('br', 'x'), ('br', 'y'),
        ('b', 'x'), ('b', 'y'),
    }
    assert almost((rect.bottom_right - rect.top_left).distance(b), 50)


def test_two_rectangles_without_top_level_point(Rectangle, Point, almost):
    # no Point is reachable as a name; only deep wrapping can hook it
    r1 = Rectangle(Point(0, 0), Point(10, 0))
    r2 = Rectangle(Point(5, 5), Point(20, 5))

    always(lambda:
           (r1.bottom_right - r1.top_left).distance(r2.top_left) == 50)

    roles = {id(r1.top_left): 'r1.tl', id(r1.bottom_right): 'r1.br',
             id(r2.top_left): 'r2.tl', id(r2.bottom_right): 'r2.br'}
    assert patch_roles(roles) == {
        ('r1.br', 'x'), ('r1.br', 'y'),
        ('r1.tl', 'x'), ('r1.tl', 'y'),
        ('r2.tl', 'x'), ('r2.tl', 'y'),
    }

    # a deep assignment re-satisfies by moving the *other* corners
    r1.top_left.x = 10
    assert almost((r1.bottom_right - r1.top_left).distance(r2.top_left), 50)


def test_nested_assignment_keeps_constraint(Rectangle, Point, almost):
    rect = Rectangle(Point(0, 0), Point(30, 40))
    b = Point(0, 0)

    always(lambda: (rect.bottom_right - rect.top_left).distance(b) == 50)

    rect.top_left.x = 10
    assert almost((rect.bottom_right - rect.top_left).distance(b), 50)


def test_list_element_reads():
    class Stats:
        pass

    s = Stats()
    s.scores = [1, 2]

    always(lambda: s.scores[0] == s.scores[1])

    assert s.scores[0] == s.scores[1]  # model values are written back


COLORS = [0, 1, 2, 3]  # module level: reachable as a global name


def test_membership_in_choices_forces_valid_assignment():
    class Item:
        pass

    item = Item()
    item.color = 0

    always(lambda: item.color in COLORS)  # `in` becomes a disjunction, see wrappers

    assert item.color in COLORS

    item.color = 2  # valid choice, fine

    with pytest.raises(ConstraintError):
        item.color = 9  # violates the membership constraint


def test_dict_value_reads():
    class Config:
        pass

    cfg = Config()
    cfg.options = {'retries': 2, 'debug': 1}

    always(lambda: cfg.options['retries'] > cfg.options['debug'])

    keys = {key for (_, key), _ in environment.namespace.all_patches()}
    assert {'retries', 'debug'} <= keys
    assert cfg.options['retries'] > cfg.options['debug']


def test_tuple_reads_are_symbolic_only():
    class Pair:
        pass

    p = Pair()
    p.pair = (1, 2)

    always(lambda: p.pair[0] == p.pair[1])  # sat: model says both equal

    assert len(environment.namespace.patches[id(p.pair)][1]) == 2
    # tuples are immutable: reads participate, write-back skips them
    assert p.pair == (1, 2)
