import types
import z3
from .solver import Solver
from .namespace import WrappingNamespace
from .env import patch_builtins
from .scope import current_scope


def discover(ns, func):
    from .containers import (WrappingSequence, WrappingMapping,
                             _WrappingContainer)
    for cell in func.__closure__ or ():
        try:
            contents = cell.cell_contents
        except ValueError:  # empty cell
            continue
        if isinstance(contents, _WrappingContainer):
            cell.cell_contents = contents.rebind(ns)  # proxied already
        elif isinstance(contents, dict):
            cell.cell_contents = WrappingMapping(ns, contents)
        elif isinstance(contents, (list, tuple)):
            cell.cell_contents = WrappingSequence(ns, contents)
        else:
            ns.wrap(contents)

    # create a function in a new global namespace
    proxy = types.FunctionType(func.__code__,
                               globals=ns,
                               closure=func.__closure__)
    from .env import capture_constraints
    with patch_builtins(), capture_constraints() as captured:
        constraints = proxy()  # !!
        if isinstance(constraints, types.GeneratorType):
            constraints = list(constraints)  # support yield
            yielded = [c for c in constraints if isinstance(c, z3.ExprRef)]
            if yielded:
                return yielded
            # e.g. `yield x in COLORS`, boolified -- see env
            return list(captured)
        if isinstance(constraints, z3.ExprRef):
            return [constraints]  # plain lambda
        if captured:
            return list(captured)
        return list(constraints)


def solve_with(constraints, patches, extra_constraint):
    solver = Solver(constraints, {})
    solver.soft_constraints = {}
    for var, value in patches.values():
        proposition = z3.FreshBool()
        solver.soft_constraints[proposition] = z3.Implies(proposition, var == value)
    return solver.solve(extra_constraint)


def apply_solution(ns, solution):
    for (obj, attr), (var, orig) in ns.all_patches():
        value = solution[var]
        if isinstance(value, z3.AlgebraicNumRef):
            value = value.approx()
        if isinstance(value, z3.IntNumRef):
            value = value.as_long()
        if isinstance(value, z3.RatNumRef):
            value = float(value.as_fraction())
        if isinstance(value, z3.BoolRef):
            value = z3.is_true(value)
        if value is None:
            continue
        if isinstance(obj, (list, dict)):
            obj[attr] = value  # container element patch
        elif isinstance(obj, tuple):
            continue  # immutable: element reads stay symbolic
        else:
            setattr(obj, attr, value)


class Constraints:
    """A collection of constraints.

    Standalone, that means an own namespace of symbolic variables and an
    own solver (one constraint re-satisfied at a time, see
    `#XXX solve at the same time`).  Inside a solver scope, both are
    shared by all `@always` blocks of the scope.

    :var namespace: Substitute for the global namespace in which the function
                    is normally executed.
    :var inprogress: Marker if a solver run is currently in progress and no
                     further action should be taken.
    :param func: The function returning or yielding the constraints.

    """
    def __init__(self, func):
        self.scope = current_scope()
        if self.scope is not None:
            self.scope.add_constraint(func)
            return

        self.inprogress = True
        self.namespace = ns = WrappingNamespace(self, [func.__globals__])
        constraints = discover(ns, func)
        self.inprogress = False

        self.solver = Solver(constraints, ns.patches)
        self.solve()

    def solve(self, extra_constraint=None):
        if self.scope is not None:
            return self.scope.solve(extra_constraint)  # scope is in charge

        if self.inprogress:
            # already in a solving run,
            # called recursively by `WrappingNamespace.wrap` from `setattr`
            return

        self.inprogress = True
        try:
            # could raise a ConstraintError
            solution = self.solver.solve(extra_constraint)
            apply_solution(self.namespace, solution)
        finally:
            self.inprogress = False
