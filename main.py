from pathlib import Path

from unified_planning.io import PDDLReader

from utils.plan_diff import diff_plans, _plan_cost
from utils.constraint import ProhibitedAction, EnforcedAction
from utils.optic import OpticImpl


def contrastive_plan_comparison(
        domain_path: str,
        problem_path: str,
        constraint_question: str,
        prohibited_actions: list[ProhibitedAction] = [],
        enforced_actions: list[EnforcedAction] = []
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

    for action in prohibited_actions:
        constrained_domain_text, constrained_problem_text = action.apply_to_pddl(
            constrained_domain_text, constrained_problem_text, up_problem
        )

    for action in enforced_actions:
        constrained_domain_text, constrained_problem_text = action.apply_to_pddl(
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
            anytime=False,
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

    prohibited_actions = [
        ProhibitedAction('drive_truck', ['d1', 't1', 'a', 'b']),
    ]

    enforced_actions = []

    contrastive_plan_comparison(
        domain_path = 'refrigerated_delivery_domain.pddl',
        problem_path = 'refrigerated_delivery_problem.pddl',
        constraint_question = 'Why did the driver drive from location a to location b?',
        enforced_actions=enforced_actions,
        prohibited_actions=prohibited_actions
    )

if __name__ == "__main__":
    main()
