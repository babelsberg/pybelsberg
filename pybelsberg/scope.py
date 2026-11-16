class _ScopeStack:
    def __init__(self):
        self.active = []


_stack = _ScopeStack()


def current_scope():
    return _stack.active[-1] if _stack.active else None


class Solver:
    """A solver scope; usable as a context manager (`with Solver():`)."""

    def __init__(self):
        self.constraints = []  # cores of every @always in this scope
        self.namespace = None  # shared WrappingNamespace, created lazily
        self.inprogress = False

    # -- context manager ----------------------------------------------------
    def __enter__(self):
        _stack.active.append(self)
        return self

    def __exit__(self, *exc_info):
        assert _stack.active[-1] is self
        _stack.active.pop()
        return False

    # duck-types `constraint.Constraints` for the shared namespace's hooks
    @property
    def solver(self):
        return self  # cores live on `self`

    def add_constraint(self, func):
        from .constraint import discover, WrappingNamespace
        if self.namespace is None:
            self.namespace = WrappingNamespace(self, [func.__globals__])
        else:
            if func.__globals__ not in self.namespace.real_globals:
                self.namespace.real_globals.append(func.__globals__)
        self.inprogress = True
        try:
            self.constraints.extend(discover(self.namespace, func))
        finally:
            self.inprogress = False
        self.solve()

    def solve(self, extra_constraint=None):
        if self.inprogress:
            # recursive call from `setattr` during solution write-back
            return
        from .constraint import apply_solution, solve_with
        self.inprogress = True
        try:
            solution = solve_with(self.constraints, self.namespace.patches,
                                  extra_constraint)
            apply_solution(self.namespace, solution)
        finally:
            self.inprogress = False
