import functools
import types
import z3
from .containers import WrappingSequence, WrappingMapping

_sentinel = object()


class WrappingNamespace(dict):
    """A namespace that automatically wraps all objects that are looked up on
    it with magic substitutes for the getattr/setattr protocols.

    :type constraints: pybelsberg.constraint.Constraints
    :var patches: A mapping of all instance attributes to their wrapped
                  counterpart and its original value, e.g.,
                  ``{(Point(), 'x'): (z3.FreshReal(), 100)}``.

    """
    def __init__(self, constraints, real_globals=(), *args, **kwargs):
        # kept live, so a `for` loop creating one @always per
        # iteration sees current values of its loop variables
        dict.__init__(self, *args, **kwargs)
        self.real_globals = list(real_globals)
        self.constraints = constraints
        self.patches = {}
        # containers are unhashable; their element patches live here
        self.container_patches = {}  # id(coll) -> (coll, {key: (var, orig)})
        self.wrapped_types = set()

    def get_patch(self, this, key):
        if isinstance(this, (list, tuple, dict)):
            entry = self.container_patches.get(id(this))
            return entry[1].get(key) if entry else None
        return self.patches.get((this, key))

    def set_patch(self, this, key, pair):
        if isinstance(this, (list, tuple, dict)):
            entry = self.container_patches.setdefault(id(this), (this, {}))
            entry[1][key] = pair
        else:
            self.patches[(this, key)] = pair

    def all_patches(self):
        """Attribute patches and element patches alike."""
        yield from self.patches.items()
        for coll, keymap in self.container_patches.values():
            for key, pair in keymap.items():
                yield (coll, key), pair

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
            if self.constraints.inprogress:
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
        if not self.constraints.inprogress:
            return val
        patch = self.get_patch(this, key)
        if patch:
            return patch[0]
        wrapper = [w for t, w in WRAPPERS.items() if isinstance(val, t)]
        if wrapper:
            wrapped = wrapper[0]()
            self.register(this)
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

    def register(self, this):
        """Note that `this` takes part in `self.constraints`.
        Containers can carry no marker -- and never re-solve either.
        """
        try:
            this.__pybelsberg__.add(self.constraints)
        except AttributeError:
            try:
                this.__pybelsberg__ = {self.constraints}
            except AttributeError:
                pass  # container without writable attributes

    def wrap(self, obj):
        """Replace the attribute mechanism of `obj` with custom hooks.

        Nested objects are wrapped recursively (see `getattr_`), hence
        wrapping is idempotent per type.

        This hooks up `obj.__getattribute__` (or rather its type's
        `__getattribute__`) to return an appropriate `z3.ArithRef` and
        `obj.__setattr__` to notify all constraint solver to run.

        """
        if isinstance(obj, UNWRAPPABLE):
            return

        if not hasattr(obj, '__pybelsberg__'):
            # collection of relevant `Constraints`
            #XXX make this more granular,
            #    ie. relevant `Constraints` for a single attribute
            obj.__pybelsberg__ = set()

        if type(obj) in self.wrapped_types:
            return  # hooks for this type are already installed for us
        self.wrapped_types.add(type(obj))

        def setattr_(this, key, value):  # idempotent
            if not key.startswith('__') and hasattr(this, '__pybelsberg__'):
                for constraints in this.__pybelsberg__:
                    #XXX solve at the same time
                    # `self` is not reliable here as a second @always would
                    # override obj.__setattr__ again
                    patch = constraints.namespace.patches.get((this, key))
                    if patch is not None:
                        # instance variable is actually affected by this
                        # `Constraints`
                        constraints.solve(patch[0] == value)
            orig_setattr(this, key, value)

        # only ever called during constraint discovery
        def getattr_(this, key):
            val = orig_getattr(this, key)
            if key.startswith('__'):
                return val
            return self.wrap_value(this, key, val)

        typ = type(obj)
        orig_setattr = typ.__setattr__
        orig_getattr = typ.__getattribute__
        try:
            typ.__setattr__ = setattr_
            typ.__getattribute__ = getattr_
        except TypeError:
            pass  # duh, can happen for modules


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
