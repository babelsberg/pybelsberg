pybelsberg
==========

[![Build Status](https://travis-ci.org/babelsberg/pybelsberg.png?branch=master)](https://travis-ci.org/babelsberg/pybelsberg)

An implementation of Babelsberg allowing constraint-based programming in Python (using the [Z3 theorem prover](http://z3.codeplex.com/)).

See also [Babelsberg/R](https://github.com/timfel/babelsberg-r), [Babelsberg/JS](https://github.com/timfel/babelsberg-js/).

It allows you to write code like the following:

```python
from pybelsberg import always

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def distance(self, other):
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

a = Point(10.0, 0.0)
b = Point(0.0, 0.0)

# Declare a constraint that should always be satisfied
@always
def constant_distance():
    return a.distance(b) == 20

print(a.distance(b)) # -> 20.0

a.x = 50.0           # ... and stays satisfied when things change
print(a.x, a.distance(b)) # -> 50.0 20.0
```

Assignments that cannot be reconciled with the constraints are refused with a
`ConstraintError` instead of being applied silently:

```python
from pybelsberg import always, clear, ConstraintError

COLORS = [0, 1, 2, 3]

class Country:
    def __init__(self, name):
        self.name = name
        self.color = 0

france = Country("France")
always(lambda: france.color in COLORS)

france.color = 2       # fine, any of the four colors will do
try:
    france.color = 9   # not one of them
except ConstraintError:
    print(france.color) # -> 2, the assignment never happened
```

The environment
---------------

Constraints live in one implicit, global *environment* (Babelsberg's name
for it) and are satisfied *together*: a new constraint may move variables an
older one had put where it wanted them, as long as all of them stay
satisfied.  One `always` registers one constraint (the expression a function
returns), so collecting constraints over a collection means looping:

```python
for country in countries:
    always(lambda: country.get_color() in COLORS)

for c1, c2 in neighbouring_pairs(countries):
    always(lambda: c1.get_color() != c2.get_color())
```

Apart from adding constraints, all of them can be thrown away at once with
`pybelsberg.clear()`, which is mostly useful to start a test with a clean
slate (see `tests/conftest.py`).  Objects keep the values a solution has
written back to them, but afterwards nothing is symbolic anymore.  The one
environment is `pybelsberg.environment` (an `Environment`), which is worth
looking at if a test wants to know what is currently in force; adding and
throwing away constraints is all there is to it otherwise.

Documentation
-------------
All of the supported functionality is covered by tests in the /tests directory.
Files beginning with "demo" represent more complex use cases.
All tests that are marked as "xfail" represent functionality that is not supported yet.

License
-------
Pybelsberg is open-source and licensed under the [BSD 3-Clause License](http://opensource.org/licenses/BSD-3-Clause).
