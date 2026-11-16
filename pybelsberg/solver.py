import z3


class ConstraintError(Exception):
    pass


class Solver:
    """A constraint solver.

    :param constraints:  Core constraints which HAVE to be satisifed,
                        e.g., ``[z3.FreshInt() * 2 == 100]``.
    :type constraints: List of Z3 expressions (`z3.ExprRef`).
    :param bindings:  Optional variable assignments that SHOULD be satisifed,
                      but can be invalidated by the solver and subsequently
                      ignored.
    :type bindings: List of Z3 variable to value mappings,
                    e.g., ``[(z3.FreshInt(), 10)]``.

    """
    def __init__(self, constraints, bindings):
        self.solver = z3.Solver()

        # for introspection
        self.constraints = constraints
        self.bindings = bindings

        self.soft_constraints = {}
        for var, value in bindings.values():
            proposition = z3.FreshBool()
            constraint = z3.Implies(proposition, var == value)
            self.soft_constraints[proposition] = constraint
        self.solver.add(constraints)

    def solve(self, extra_constraints=None):
        """Return a solution to the constraint system, including all conditions
        in `extra_constraints` (which are variable assignments when called from
        `Constraints` after ``@always``.)

        """
        # rebuild a plain solver per check: nlsat goes pathological on
        # nonlinear `sqrt` constraints when solving incrementally
        self.solver = z3.Solver()
        self.solver.add(self.constraints)
        if extra_constraints is not None:
            self.solver.add(extra_constraints)
        self.solver.add(*self.soft_constraints.values())

        check = self.solver.check()
        if check == z3.sat:
            solution = self.solver.model()
            self.soft_constraints = {s: k for s, k
                                     in self.soft_constraints.items()
                                     if z3.is_true(solution[s])}
            return solution
        raise ConstraintError(self.solver, extra_constraints)
