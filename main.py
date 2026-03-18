from unified_planning.environment import get_environment
from unified_planning.io import PDDLReader
from unified_planning.shortcuts import OneshotPlanner

from utils.plan_diff import diff_plans, _plan_cost
from utils.constraint import ProhibitedAction, EnforcedAction
from utils.optic import OpticImpl

env = get_environment()
env.factory.add_engine('optic', __name__, 'OpticImpl')

def contrastive_plan_comparison(
        domain_path: str,
        problem_path: str,
        constraint_question: str,
        prohibited_actions: list[ProhibitedAction] = [],
        enforced_actions: list[EnforcedAction] = []
    ):
    reader = PDDLReader()
    original_problem = reader.parse_problem(
        domain_path,
        problem_path
    )

    constrained_problem = reader.parse_problem(
        domain_path,
        problem_path
    )

    for action in prohibited_actions:
        action.prohibit_action(constrained_problem)

    for action in enforced_actions:
        action.enforce_action(constrained_problem)


    with OneshotPlanner(name='optic') as planner:
        original_result = planner.solve(original_problem)
        constrained_result = planner.solve(constrained_problem)


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