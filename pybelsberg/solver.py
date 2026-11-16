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
        self.solver.push()
        try:
            if extra_constraints is not None:
                self.solver.add(extra_constraints)
            self.solver.add(*self.soft_constraints.values())

            check = self.solver.check()
            if check == z3.sat:
                solution = self.solver.model()
                # deleted_bindings = [
                self.soft_constraints = {s: k for s, k
                                         in self.soft_constraints.items()
                                         if z3.is_true(solution[s])}
                return solution
            else:
                raise ConstraintError(self.solver, extra_constraints)
        finally:
            self.solver.pop()


# make ExprRef -- and thus BoolRef -- hashable;  required in
# `Solver.soft_constraints`, which is a a mapping of `z3.BoolRef` to
# `z3.Implies`
def ExprRef_hash(self):
    return self.hash()
z3.ExprRef.__hash__ = ExprRef_hash
