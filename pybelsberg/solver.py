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
                      ignored, e.g., ``[(z3.FreshInt(), 10)]``.
    :type bindings: Iterable of Z3 variable to value pairs.

    """
    def __init__(self, constraints, bindings=()):
        # for introspection
        self.constraints = list(constraints)
        self.bindings = list(bindings)

        self.soft_constraints = {}
        for var, value in self.bindings:
            proposition = z3.FreshBool()
            self.soft_constraints[proposition] = z3.Implies(proposition,
                                                            var == value)

    def solve(self, extra_constraints=None):
        """Return a solution to the constraint system, including all conditions
        in `extra_constraints` (which are variable assignments when called
        from `environment.Environment.solve` after an assignment.)

        """
        # rebuild a plain solver per check: nlsat goes pathological on
        # nonlinear `sqrt` constraints when solving incrementally
        solver = z3.Solver()
        solver.add(self.constraints)
        if extra_constraints is not None:
            solver.add(extra_constraints)
        solver.add(*self.soft_constraints.values())

        check = solver.check()
        if check == z3.sat:
            solution = solver.model()
            self.soft_constraints = {s: k for s, k
                                     in self.soft_constraints.items()
                                     if z3.is_true(solution[s])}
            return solution
        raise ConstraintError(solver, extra_constraints)
