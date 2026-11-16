import functools
import z3

class WrappingNamespace(dict):
    """A namespace that automatically wraps all objects that are looked up on
    it with magic substitutes for the getattr/setattr protocols.

    :type constraints: pybelsberg.constraint.Constraints
    :var patches: A mapping of all instance attributes to their wrapped
                  counterpart and its original value, e.g.,
                  ``{(Point(), 'x'): (z3.FreshReal(), 100)}``.

    """
    def __init__(self, constraints, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.constraints = constraints
        self.patches = {}

    def __getitem__(self, key):
        if key == '__tracebackhide__':  # py.test compatibility
            return False
        try:
            obj = dict.__getitem__(self, key)
        except KeyError:
            import builtins
            obj = builtins.__dict__[key]
        if not key.startswith('__'):
            self.wrap(obj)
        return obj

    def wrap(self, obj):
        """Replace the attribute mechanism of `obj` with custom hooks.

        This hooks up `obj.__getattribute__` (or rather its type's
        `__getattribute__`) to return an appropriate `z3.ArithRef` and
        `obj.__setattr__` to notify all constraint solver to run.

        """
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
            if not self.constraints.inprogress:
                return val

            patch = self.patches.get((this, key))
            if patch:
                return patch[0]

            # find a wrapper for the type of `val` or any of its superclasses
            wrapper = [w for t, w in WRAPPERS.items() if isinstance(val, t)]
            if wrapper:
                wrapped = wrapper[0]()
                this.__pybelsberg__.add(self.constraints)
                self.patches[(this, key)] = (wrapped, val)
                return wrapped
            elif isinstance(val, list):
                raise NotImplementedError
            elif isinstance(val, tuple):
                raise NotImplementedError
            elif isinstance(val, dict):
                raise NotImplementedError
            else:
                return val

        if not hasattr(obj, '__pybelsberg__'):
            # collection of relevant `Constraints`
            #XXX make this more granular,
            #    ie. relevant `Constraints` for a single attribute
            obj.__pybelsberg__ = set()

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
