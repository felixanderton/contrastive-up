from unified_planning.model import Problem, DurativeAction, InstantaneousAction
from unified_planning.shortcuts import Fluent, And, Equals, StartTiming, EndTiming


def enforce_goal(
    problem: Problem,
    fluent_name: str,
    object_names: list[str]
):
    """
    Enforces that a specific fluent with specific objects is part of the goal.

    :param problem: The planning problem to modify.
    :param fluent_name: The name of the fluent to add to the goal.
    :param object_names: The names of the objects that parameterize the fluent.
    """
    try:
        fluent_to_add = problem.fluent(fluent_name)
        objects = [problem.object(name) for name in object_names]
        problem.add_goal(fluent_to_add(*objects))
        print(f"INFO: Added goal '{fluent_name}({', '.join(object_names)})'")
    except Exception as e:
        print(f"ERROR: Could not add goal constraint: {e}")


class ProhibitedAction:
    def __init__(self, action_name: str, param_object_names: list[str]):
        self.action_name = action_name
        self.param_object_names = param_object_names

    def prohibit_action(
        self,
        problem: Problem,
    ):
        """
        Prohibits a specific action instance by adding a guard precondition.

        :param problem: The planning problem to modify.
        :param action_name: The name of the action to prohibit.
        :param param_object_names: The object names that define the specific action instance.
        """
        try:
            action_to_modify = problem.action(self.action_name)
            guard_fluent_name = f"permit_{self.action_name}"

            # 1. Create the guard fluent if it doesn't exist
            if not problem.has_fluent(guard_fluent_name):
                guard_fluent = Fluent(guard_fluent_name, **{p.name: p.type for p in action_to_modify.parameters})
                problem.add_fluent(guard_fluent, default_initial_value=True)
                # 2. Add the guard fluent as a precondition/condition to the action
                guard_expression = guard_fluent(*action_to_modify.parameters)
                if isinstance(action_to_modify, DurativeAction):
                    action_to_modify.add_condition(StartTiming(), guard_expression)
                else: # InstantaneousAction
                    action_to_modify.add_precondition(guard_expression)

            # 3. Set the initial state of the guard to False for the specific instance
            guard_fluent = problem.fluent(guard_fluent_name)
            objects = [problem.object(name) for name in self.param_object_names]
            problem.set_initial_value(guard_fluent(*objects), False)
            print(f"INFO: Prohibited action '{self.action_name}({', '.join(self.param_object_names)})'")
            return problem
        except Exception as e:
            print(f"ERROR: Could not prohibit action: {e}")
            return problem


class EnforcedAction:
    def __init__(self, action_name: str, param_object_names: list[str]):
        self.action_name = action_name
        self.param_object_names = param_object_names

    def enforce_action(
        self,
        problem: Problem
    ):
        """
        Enforces that a specific action instance must be taken by adding a marker effect and goal.

        :param problem: The planning problem to modify.
        :param action_name: The name of the action to enforce.
        :param param_object_names: The object names that define the specific action instance.
        """
        try:
            action_to_modify = problem.action(self.action_name)
            marker_fluent_name = f"did_{self.action_name}_{'_'.join(self.param_object_names)}"

            # 1. Create a unique marker fluent for this specific action instance
            if not problem.has_fluent(marker_fluent_name):
                marker_fluent = Fluent(marker_fluent_name)
                problem.add_fluent(marker_fluent, default_initial_value=False)
                # 2. Add the marker as an effect of the action, only when parameters match
                action_params = action_to_modify.parameters
                objects = [problem.object(name) for name in self.param_object_names]
                condition = And(Equals(p, o) for p, o in zip(action_params, objects))
                if isinstance(action_to_modify, DurativeAction):
                    action_to_modify.add_effect(EndTiming(), marker_fluent(), True, condition)
                else: # InstantaneousAction
                    action_to_modify.add_effect(marker_fluent(), True, condition)
                # 3. Add the marker fluent to the goal
                problem.add_goal(marker_fluent)
                print(f"INFO: Enforced action '{self.action_name}({', '.join(self.param_object_names)})'")
        except Exception as e:
            print(f"ERROR: Could not enforce action: {e}")
        
        return problem