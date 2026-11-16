"""Read-only proxy views over `list`/`tuple`/`dict` for constraint discovery.

Builtin types cannot be hooked (C-slot patching segfaults modern CPython,
even with monkeypatch/forbiddenfruit), so containers a constraint function
touches are replaced by these proxies for the duration of discovery.
Reads participate in the constraint system (elements become fresh Z3
variables, `in` becomes a disjunction); writes through the container
itself stay unconstrained and never trigger a re-solve.  Outside
discovery the proxies are pass-through views.
"""
import z3


class _WrappingContainer:
    __slots__ = ('_ns', '_coll')

    def __init__(self, ns, coll):
        self._ns = ns
        self._coll = coll

    def _view(self, key):
        return self._ns.wrap_value(self._coll, key, self._coll[key])

    def unwrap(self):
        """The underlying, unwrapped container (raw elements)."""
        return self._coll

    def rebind(self, ns):
        """An equivalent proxy bound to a (possibly new) namespace."""
        return type(self)(ns, self._coll)

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self._coll)


class WrappingSequence(_WrappingContainer):
    """Read-only view for `list`/`tuple`; patches are keyed `(list, index)`."""

    def __getitem__(self, key):
        if isinstance(key, slice):
            return [self._view(i)
                    for i in range(*key.indices(len(self._coll)))]
        return self._view(key)

    def __iter__(self):
        for i in range(len(self._coll)):
            yield self._view(i)

    def __len__(self):
        return len(self._coll)

    def __contains__(self, x):
        if isinstance(x, z3.ExprRef):
            # `color in [RED, GREEN, YELLOW, BLUE]` -- a disjunction
            choices = [e for e in self._coll
                       if isinstance(e, (bool, int, float))]
            if not choices or len(choices) != len(self._coll):
                raise TypeError(
                    "symbolic membership is only supported for collections "
                    "of numeric choices")
            return z3.Or(*[x == e for e in choices])
        for e in self._coll:
            # no bare `any()` -- builtins.any is z3.Or during discovery
            if x is e or x == e:
                return True
        return False

    def __eq__(self, other):
        if isinstance(other, _WrappingContainer):
            other = other._coll
        return self._coll == other

    def __hash__(self):
        raise TypeError("unhashable type")


class WrappingMapping(_WrappingContainer):
    """Read-only view for `dict`; patches are keyed `(dict, key)`.

    Keys are looked up concretely (identity/hash), only *values* are
    wrapped.  `k in d` keeps its concrete key-membership meaning.
    """

    def __getitem__(self, key):
        return self._view(key)

    def get(self, key, default=None):
        if key in self._coll:
            return self._view(key)
        return default

    def keys(self):
        return self._coll.keys()

    def values(self):
        return [self._view(k) for k in self._coll]

    def items(self):
        return [(k, self._view(k)) for k in self._coll]

    def __iter__(self):
        return iter(self._coll)

    def __contains__(self, key):
        return key in self._coll

    def __len__(self):
        return len(self._coll)

    def __eq__(self, other):
        if isinstance(other, _WrappingContainer):
            other = other._coll
        return self._coll == other

    def __hash__(self):
        raise TypeError("unhashable type")
