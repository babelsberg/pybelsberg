"""The one, global, implicit constraint environment.

There is exactly one environment (the `environment` singleton at the bottom
of this module).  Every constraint registered via `always` joins it, and they
are all satisfied together, so a new constraint may move variables an older
one put where it wanted them as long as all of them stay satisfied.
Constraints can only be added (`always`) or thrown away altogether (`clear`).
"""
import types

import z3

from .solver import Solver, ConstraintError
from .wrappers import (WrappingNamespace, WrappingSequence, WrappingMapping,
                       _WrappingContainer)
from .babelsberg_builtins import patch_builtins, capture_constraints


class Environment:
    """The constraints currently in force, and the world they refer to.

    :ivar constraints: the Z3 expressions of every constraint registered so
                       far, e.g., ``[z3.FreshReal() * 2 == 100]``.
    :ivar namespace: The `wrappers.WrappingNamespace` constraint functions
                     are executed in -- one for the whole environment, so all
                     of them see the same variable for the same attribute.
    :ivar inprogress: Marker if a solver run is currently in progress and no
                      further action should be taken.
    """
    def __init__(self):
        self.constraints = []
        self.namespace = None
        self.inprogress = False

    def clear(self):
        """Throw away all constraints.

        Objects keep the values a solution has already written back to them,
        but nothing is symbolic anymore and no further solving happens.
        Mostly useful to start from a clean slate in the next test.
        """
        self.constraints = []
        if self.namespace is not None:
            self.namespace.reset()

    def add(self, func):
        """Add the constraint `func` expresses, and satisfy them all again.

        :param func: A function returning the constraint as a Z3 expression.
                     Registration happens once per constraint, so collecting
                     constraints means calling this once per constraint.
        :raises solver.ConstraintError: if the constraint does not fit the
                     ones already in force (it is not added then)
        """
        if self.namespace is None:
            self.namespace = WrappingNamespace(self, [func.__globals__])
        elif func.__globals__ not in self.namespace.real_globals:
            self.namespace.real_globals.append(func.__globals__)

        self.inprogress = True
        try:
            new_constraints = self.discover(self.namespace, func)
        finally:
            self.inprogress = False

        start = len(self.constraints)
        self.constraints.extend(new_constraints)
        try:
            self.solve()
        except ConstraintError:
            # constraints that do not fit the ones in force are refused,
            # just as an impossible assignment is
            del self.constraints[start:]
            raise

    @staticmethod
    def discover(ns, func):
        """Return the Z3 expressions `func` states as constraints.

        `func` is executed with `ns` as its global namespace, which turns
        every object it looks up into a symbolic counterpart (see
        `wrappers.WrappingNamespace`), so that the expression it ends up
        returning is about Z3 variables instead of concrete values.
        """
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
        with patch_builtins(), capture_constraints() as captured:
            returned = proxy()
            if isinstance(returned, types.GeneratorType):
                list(returned)  # run it, so it raises about its real body
                raise TypeError(
                    "%s() yields, but a constraint is a single expression: "
                    "return it, or register one constraint per `always`"
                    % func.__name__)

            constraints = list(captured)  # boolified expressions, see babelsberg_builtins
            if isinstance(returned, z3.ExprRef):
                constraints.append(returned)
            elif isinstance(returned, (list, tuple)):
                constraints.extend(e for e in returned
                                   if isinstance(e, z3.ExprRef))
            return constraints

    def solve(self, extra_constraint=None):
        """Bring every constraint (plus `extra_constraint`) back into effect.

        `extra_constraint` is what a user just assigned to an attribute that
        is under observation; it either fits the constraints or the
        assignment is refused with a `solver.ConstraintError`.
        """
        if self.inprogress:
            # recursive call from `setattr` during solution write-back
            return
        self.inprogress = True
        try:
            solver = Solver(self.constraints, self.namespace.bindings())
            solution = solver.solve(extra_constraint)
            self.apply_solution(solution)
        finally:
            self.inprogress = False

    def apply_solution(self, solution):
        """Write `solution` back to the objects it has been found for."""
        for (obj, attr), (var, orig) in self.namespace.all_patches():
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


def always(func):
    """Declare a constraint that should always be satisfied.

    `func` is called right away, in a symbolic view of the world it is
    executed in, and the constraint it returns joins the constraints of the
    environment: they all have to hold at once, and they are re-satisfied
    whenever one of the values involved is assigned to.

    A constraint is a single expression, and one `always` registers one of
    them -- to constrain a whole collection of objects, loop::

        for country in countries:
            always(lambda: country.get_color() in COLORS)

    :param func: The function returning the constraint as a Z3 expression,
                 e.g. ``lambda: a.x == 20``.
    :returns: `func`, unchanged (so this can be used as a decorator)
    :raises solver.ConstraintError: if it cannot be satisfied together with
                 the constraints already in force (it is not added then)

    """
    if not callable(func):
        raise TypeError("always expects the function stating the constraint")
    environment.add(func)
    return func


#: The environment every constraint joins.
environment = Environment()

#: Remove all constraints from the environment (see `Environment.clear`).
clear = environment.clear
