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
    yield a.distance(b) == 20

print(a.x, a.y) # -> 20.0 0.0
print(b.x, b.y) # -> 0.0 0.0

a.x, a.y = 50.0
print(a.x, a.y) # -> 50.0 50.0
print(b.x, b.y) # -> 30.0 50.0
```

Setup
-----
Pybelsberg requires Python version >= 3.3.

Z3 needs to be built from the [unstable branch](http://z3.codeplex.com/SourceControl/list/changesets?branch=unstable) (using the provided [instructions](http://z3.codeplex.com/SourceControl/latest?branch=unstable#README)) because only this branch (as of August 2014) supports Python 3.x. Make sure the Z3 directory is in the PYTHONPATH.

Pybelsberg uses [tox](https://testrun.org/tox/latest/) and [py.test](http://pytest.org/latest/) for testing.

Documentation
-------------
All of the supported functionality is covered by tests in the /tests directory.
Files beginning with "demo" represent more complex use cases.
All tests that are marked as "xfail" represent functionality that is not supported yet.

License
-------
Pybelsberg is open-source and licensed under the [BSD 3-Clause License](http://opensource.org/licenses/BSD-3-Clause).
