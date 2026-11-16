import contextlib
from unittest import mock
import z3


def all_different(lst):
    return z3.And(_all_different(lst))
def _all_different(lst):
    for idx, elem in enumerate(lst):
        for other in lst[idx+1:]:
            yield elem != other

def all_same(lst):
    return z3.And(_all_same(lst))
def _all_same(lst):
    last = _sentinel
    for idx, elem in enumerate(lst[1:]):
        if last == _sentinel:
            continue
        yield last == elem


def Abs(number):
    return z3.If(number > 0, number, -number)

def Sum(sequence, start=0):
    return z3.Sum(sequence) + start


MATH_MODULE = mock.patch.multiple('math',
    sqrt = z3.Sqrt,
)
BUILTIN_MODULE = mock.patch.multiple('builtins',
    abs = Abs,
    all = z3.And,
    any = z3.Or,
    sum = z3.Sum,
)


# `BoolRef.__bool__` raises for symbolic expressions, which makes `in`
# unusable in constraints.  During discovery, such truthiness tests are
# captured instead of boolified, and `discover` registers what comes out;
# outside discovery the original raising behavior is restored.

_capture = None
_orig_boolref_bool = z3.BoolRef.__bool__


def _boolref_bool(self):
    if z3.is_true(self):
        return True
    if z3.is_false(self):
        return False
    if _capture is not None:
        _capture.append(self)
        return True
    return _orig_boolref_bool(self)


z3.BoolRef.__bool__ = _boolref_bool


@contextlib.contextmanager
def capture_constraints():
    """Collect boolified symbolic expressions in a list."""
    global _capture
    prev, _capture = _capture, []
    try:
        yield _capture
    finally:
        _capture = prev


@contextlib.contextmanager
def patch_builtins():
    with contextlib.ExitStack() as ctx:
        ctx.enter_context(MATH_MODULE)
        ctx.enter_context(BUILTIN_MODULE)
        yield
