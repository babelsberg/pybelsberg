"""The symbolic counterparts constraint functions work with.

A constraint function is executed in a `WrappingNamespace` instead of the
globals of its module, and everything it looks up is handed to it in a form
that takes part in the constraint system: attributes become fresh Z3
variables on the fly, assignments to them re-satisfy the constraints, and
`list`/`tuple`/`dict` are handed out as read-only proxies whose elements are
variables too (builtins cannot be hooked -- patching their C slots segfaults
modern CPythons, even with monkeypatch/forbiddenfruit).

Outside of a constraint discovery run all of this is inert: the proxies are
pass-through views and attributes keep their real values.
"""
import functools
import types
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


_sentinel = object()


class WrappingNamespace(dict):
    """A namespace that automatically wraps all objects that are looked up on
    it with magic substitutes for the getattr/setattr protocols.

    :type environment: pybelsberg.environment.Environment
    :ivar patches: Everything that takes part in the environment's
                   constraints: a mapping of each object to its attributes
                   (or, for a list or dict, its elements) with their wrapped
                   counterpart and their original value, e.g.,
                   ``{id(a_point): (a_point, {'x': (z3.FreshReal(), 100)})}``.
                   Objects are keyed by `id` (containers are unhashable); the
                   object itself is part of the entry, so its `id` stays
                   valid.

    """
    def __init__(self, environment, real_globals=(), *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        # the modules that registered constraints, referenced rather than
        # copied: a `for` loop creating one `always` per iteration is to see
        # the current values of its loop variables
        self.real_globals = list(real_globals)
        self.environment = environment
        self.patches = {}

    def reset(self):
        """Forget every object seen so far, to start over with an empty
        environment.

        The hooks installed on the classes of the objects seen so far stay in
        place (they cannot be undone reliably), but without patches there is
        nothing left for them to observe.
        """
        dict.clear(self)
        self.real_globals = []
        self.patches.clear()

    # -- patches: attribute (or element) -> Z3 variable ----------------------
    def get_patch(self, this, key):
        entry = self.patches.get(id(this))
        return entry[1].get(key) if entry else None

    def set_patch(self, this, key, pair):
        self.patches.setdefault(id(this), (this, {}))[1][key] = pair

    def all_patches(self):
        """Yield ``((object, key), (variable, original value))``."""
        for obj, keymap in self.patches.values():
            for key, pair in keymap.items():
                yield (obj, key), pair

    def bindings(self):
        """The ``(variable, value)`` pairs a solution should keep if it can."""
        for _, (var, orig) in self.all_patches():
            yield var, orig

    def __getitem__(self, key):
        if key == '__tracebackhide__':  # py.test compatibility
            return False
        try:
            obj = dict.__getitem__(self, key)
        except KeyError:
            obj = _sentinel
            for globs in self.real_globals:
                try:
                    obj = globs[key]
                    break
                except KeyError:
                    pass
            if obj is _sentinel:
                import builtins
                obj = builtins.__dict__[key]
        if not key.startswith('__'):
            if self.environment.inprogress:
                if isinstance(obj, dict):
                    return WrappingMapping(self, obj)
                if isinstance(obj, (list, tuple)):
                    return WrappingSequence(self, obj)
            self.wrap(obj)
        return obj

    def wrap_value(self, this, key, val):
        """`val` as seen by the constraint system: a fresh Z3 variable for
        scalars (registered in `patches`), a read-only proxy for
        containers, hooked classes for everything else.
        """
        if not self.environment.inprogress:
            return val
        patch = self.get_patch(this, key)
        if patch:
            return patch[0]
        wrapper = [w for t, w in WRAPPERS.items() if isinstance(val, t)]
        if wrapper:
            wrapped = wrapper[0]()
            self.set_patch(this, key, (wrapped, val))
            return wrapped
        if isinstance(val, dict):
            return WrappingMapping(self, val)
        if isinstance(val, (list, tuple)):
            return WrappingSequence(self, val)
        if (not isinstance(val, z3.ExprRef)
                and hasattr(val, '__dict__') and not callable(val)):
            self.wrap(val)  # nested object; hook its class too
            return val
        return val

    def wrap(self, obj):
        """Replace the attribute mechanism of `obj` with custom hooks.

        Nested objects are wrapped recursively (see `getattr_`), hence
        wrapping is idempotent per type.

        This hooks up `obj.__getattribute__` (or rather its type's
        `__getattribute__`) to return an appropriate `z3.ArithRef` and
        `obj.__setattr__` to have the environment satisfy the constraints
        again.

        """
        if isinstance(obj, UNWRAPPABLE):
            return

        typ = type(obj)
        if getattr(typ, '__pybelsberg__', False):
            return  # hooks for this type are already installed

        def setattr_(this, key, value):
            if not key.startswith('__'):
                patch = self.get_patch(this, key)
                if patch is not None:
                    # the value of an attribute that is under observation is
                    # about to change: the new one has to fit the constraints
                    self.environment.solve(patch[0] == value)
            orig_setattr(this, key, value)

        # only ever called during constraint discovery
        def getattr_(this, key):
            val = orig_getattr(this, key)
            if key.startswith('__'):
                return val
            return self.wrap_value(this, key, val)

        orig_setattr = typ.__setattr__
        orig_getattr = typ.__getattribute__
        try:
            typ.__setattr__ = setattr_
            typ.__getattribute__ = getattr_
        except TypeError:
            pass  # duh, can happen for modules
        else:
            typ.__pybelsberg__ = True  # marker: these hooks are ours


WRAPPERS = {
    float: functools.partial(z3.FreshReal, prefix='R'),
    int: functools.partial(z3.FreshReal, prefix='D'),  # keep it real
    bool: functools.partial(z3.FreshBool, prefix='B'),
}

# no writable attributes on the builtins, and hooking modules would
# silently pollute global state
UNWRAPPABLE = (str, bytes, int, float, bool, complex, type(None),
               list, tuple, dict, set, frozenset,
               types.ModuleType, types.FunctionType,
               types.BuiltinFunctionType, types.MethodType,
               type)
