import math
import os
import pytest

import pybelsberg


@pytest.fixture(scope="session", autouse=True)
def z3_timeout():
    import z3
    z3.set_param('timeout', 5000)


@pytest.fixture(autouse=True)
def clean_environment():
    """No constraint of another test is in force here (or afterwards)."""
    pybelsberg.clear()
    yield
    pybelsberg.clear()


@pytest.fixture
def Point():
    class Point:
        def __init__(self, x, y):
            self.x = x
            self.y = y

        def distance(self, other):
            return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

        def __repr__(self):
            return "Point(%r, %r)" % (self.x, self.y)

    return Point


@pytest.fixture
def almost():
    __tracebackhide__ = True
    def _almost(value, expected):
        return abs(value - expected) < 1e-6
    return _almost
