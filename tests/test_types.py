import pytest
from pybelsberg import always

@pytest.fixture
def Object():
    return type('Object', (), {})


def test_integer(Point, almost):
    # integers are real
    a = Point(0, 10)

    @always
    def constraint_half():
        return a.x * 2 == 5

    assert almost(a.x, 2.5)


def test_float(Point, almost):
    a = Point(0.0, 10.0)

    @always
    def constraint_half():
        return a.x * 2 == 5

    assert almost(a.x, 2.5)


def test_list(Object):
    a = Object()
    a.seq = [1, 2]

    @always
    def constraint_equal():
        return a.seq[0] == a.seq[1]

    assert a.seq[0] == a.seq[1]


def test_dict(Object):
    a = {'b': 2}

    @always
    def constraint_constant_ab():
        yield a['b'] == 7

    assert a['b'] == 7


def test_association(Object):
    a = Object()
    b = Object()
    a.b = b
    b.c = 5

    @always
    def constraint_constant_abc():
        return a.b.c == 10

    assert a.b.c == 10


def test_recurse(Object):
    a = Object()
    a.table = {'seq': [1, 2]}

    @always
    def constraint_equal():
        return a.table['seq'][0] == a.table['seq'][1]

    assert a.table['seq'][0] == a.table['seq'][1]


def test_unsupported_datatype(Object):
    a = Object()
    a.x = 10
    a.y = "I am a string"

    @always
    def constraint_unrelated():
        return a.x == 20

    assert a.y == "I am a string"  # should not have been touched


@pytest.mark.xfail
def test_direct_primitive():
    a = []

    @always
    def constraint_equal():
        return a[0] == a[1]

    assert a[0] == a[1]
