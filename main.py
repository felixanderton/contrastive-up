from pathlib import Path

from unified_planning.io import PDDLReader

from utils.plan_diff import diff_plans, _plan_cost
from utils.constraint import (
    ProhibitedAction, EnforcedAction,
    ActionOrdering, AtomGoal, FluentChange, TimedLiteral, ActionCountLimit,
)
from utils.optic import OpticImpl


def contrastive_plan_comparison(
        domain_path: str,
        problem_path: str,
        constraint_question: str,
        constraints: list | None = None,
        prohibited_actions: list[ProhibitedAction] | None = None,
        enforced_actions: list[EnforcedAction] | None = None,
    ):
    # Parse original problem once — used only for action/object lookup when
    # interpreting OPTIC's plan output. We never re-serialize it with PDDLWriter.
    up_problem = PDDLReader().parse_problem(domain_path, problem_path)

    # Build constrained PDDL by making targeted text edits to the original files.
    # This avoids PDDLWriter mangling TILs, metrics, and duration expressions.
    domain_text = Path(domain_path).read_text()
    problem_text = Path(problem_path).read_text()

    constrained_domain_text = domain_text
    constrained_problem_text = problem_text

    all_constraints = list(constraints or []) + list(prohibited_actions or []) + list(enforced_actions or [])
    for constraint in all_constraints:
        constrained_domain_text, constrained_problem_text = constraint.apply_to_pddl(
            constrained_domain_text, constrained_problem_text, up_problem
        )

    constrained_domain_file = "domain_constrained_temp.pddl"
    constrained_problem_file = "problem_constrained_temp.pddl"
    Path(constrained_domain_file).write_text(constrained_domain_text)
    Path(constrained_problem_file).write_text(constrained_problem_text)

    optic = OpticImpl()
    try:
        original_result = optic.solve_files(domain_path, problem_path, up_problem)
        constrained_result = optic.solve_files(
            constrained_domain_file, constrained_problem_file, up_problem,
        )
    finally:
        Path(constrained_domain_file).unlink(missing_ok=True)
        Path(constrained_problem_file).unlink(missing_ok=True)

    if not original_result.plan or not constrained_result.plan:
        print("Could not obtain both plans.")
        print("Original status:", original_result.status)
        print("Constrained status:", constrained_result.status)
    else:
        original_cost = _plan_cost(original_result.plan)
        constrained_cost = _plan_cost(constrained_result.plan)
        if constrained_cost is not None and original_cost is not None and constrained_cost < original_cost:
            print(
                f"Error: contrastive comparison is invalid — the constrained plan "
                f"(cost {constrained_cost:.2f}) is cheaper than the original plan "
                f"(cost {original_cost:.2f}). The planner did not find an optimal "
                f"solution for the original problem, so no meaningful explanation "
                f"can be produced."
            )
            return
        print(f"\n\n Constraint: {constraint_question}")
        diff_plans(original_result.plan, constrained_result.plan)


def main():
    contrastive_plan_comparison(
        domain_path='refrigerated_delivery_domain.pddl',
        problem_path='refrigerated_delivery_problem.pddl',
        constraint_question='Why did the driver use truck t2 to drive from a to c?',
        constraints=[
            ProhibitedAction('drive_truck', ['d1', 't2', 'a', 'c']),
        ],
    )

if __name__ == "__main__":
    main()
