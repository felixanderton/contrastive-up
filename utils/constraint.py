from itertools import product as iterproduct
from unified_planning.model import Problem, DurativeAction, InstantaneousAction


# ---------------------------------------------------------------------------
# PDDL text-manipulation helpers
# ---------------------------------------------------------------------------

def _find_matching_close(text: str, open_idx: int) -> int:
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    return -1


def _insert_before_section_close(text: str, section_keyword: str, insertion: str) -> str:
    """Find (:section_keyword ...) and insert text before its closing paren."""
    kw_idx = text.find(section_keyword)
    if kw_idx == -1:
        return text
    open_idx = text.rfind('(', 0, kw_idx)
    close_idx = _find_matching_close(text, open_idx)
    if close_idx == -1:
        return text
    return text[:close_idx] + f'\n    {insertion}' + text[close_idx:]


def _add_to_action_section_and(
    domain_text: str, action_name: str, section_keyword: str, addition: str
) -> str:
    """Add a clause inside a durative-action's :condition or :effect (and ...) block."""
    marker = f':durative-action {action_name}'
    kw_idx = domain_text.find(marker)
    if kw_idx == -1:
        return domain_text
    action_open = domain_text.rfind('(', 0, kw_idx)
    action_close = _find_matching_close(domain_text, action_open)
    section_idx = domain_text.find(section_keyword, action_open, action_close)
    if section_idx == -1:
        return domain_text
    and_idx = domain_text.find('(and', section_idx, action_close)
    if and_idx == -1:
        return domain_text
    and_close = _find_matching_close(domain_text, and_idx)
    return domain_text[:and_close] + f'\n                  {addition}' + domain_text[and_close:]


def _add_to_goal_and(problem_text: str, goal_fact: str) -> str:
    """Add a fact inside (:goal (and ...))."""
    kw_idx = problem_text.find(':goal')
    if kw_idx == -1:
        return problem_text
    goal_open = problem_text.rfind('(', 0, kw_idx)
    goal_close = _find_matching_close(problem_text, goal_open)
    and_idx = problem_text.find('(and', goal_open, goal_close)
    if and_idx == -1:
        return problem_text
    and_close = _find_matching_close(problem_text, and_idx)
    return problem_text[:and_close] + f'\n        {goal_fact}' + problem_text[and_close:]


def _add_requirement(domain_text: str, requirement: str) -> str:
    return _insert_before_section_close(domain_text, ':requirements', requirement)


# ---------------------------------------------------------------------------
# Constraint classes
# ---------------------------------------------------------------------------

class ProhibitedAction:
    def __init__(self, action_name: str, param_object_names: list[str]):
        self.action_name = action_name
        self.param_object_names = param_object_names

    def apply_to_pddl(
        self,
        domain_text: str,
        problem_text: str,
        problem: Problem,
    ) -> tuple[str, str]:
        """
        Prohibit a specific action instance using a positive permit predicate.
        All instances are permitted in the init except the prohibited one.
        Positive preconditions are handled cleanly by OPTIC's LP heuristic;
        negative preconditions on static fluents can cause the LP to loop.
        """
        action = problem.action(self.action_name)
        permit_pred = f"permit_{self.action_name}"
        params_with_types = " ".join(
            f"?{p.name} - {p.type.name}" for p in action.parameters
        )
        params = " ".join(f"?{p.name}" for p in action.parameters)
        args = " ".join(self.param_object_names)

        domain_text = _insert_before_section_close(
            domain_text, ':predicates', f"({permit_pred} {params_with_types})"
        )
        domain_text = _add_to_action_section_and(
            domain_text, self.action_name, ':condition',
            f"(at start ({permit_pred} {params}))"
        )

        # Add ALL groundings to init so the LP sees every precondition as
        # achievable (avoids the LP-initialisation hang caused by unreachable
        # preconditions). Then immediately remove the prohibited instance via a
        # TIL at 0.001 s — before any action sequence can make the drive
        # applicable (all durative actions have duration >= 0.01 s, so
        # preconditions like 'boarded' cannot be established before that).
        objects_per_param = [
            [o.name for o in problem.objects(p.type)] for p in action.parameters
        ]
        for combo in iterproduct(*objects_per_param):
            problem_text = _insert_before_section_close(
                problem_text, ':init', f"({permit_pred} {' '.join(combo)})"
            )
        problem_text = _insert_before_section_close(
            problem_text, ':init', f"(at 0.001 (not ({permit_pred} {args})))"
        )

        print(f"INFO: Prohibited action '{self.action_name}({', '.join(self.param_object_names)})'")
        return domain_text, problem_text


class EnforcedAction:
    def __init__(self, action_name: str, param_object_names: list[str]):
        self.action_name = action_name
        self.param_object_names = param_object_names

    def apply_to_pddl(
        self,
        domain_text: str,
        problem_text: str,
        problem: Problem,
    ) -> tuple[str, str]:
        """
        Enforce a specific action instance by adding a marker predicate,
        a conditional effect, and a goal. Uses text edits on the original PDDL.
        """
        action = problem.action(self.action_name)
        marker_name = f"did_{self.action_name}_{'_'.join(self.param_object_names)}"
        equalities = " ".join(
            f"(= ?{p.name} {o})"
            for p, o in zip(action.parameters, self.param_object_names)
        )

        domain_text = _add_requirement(domain_text, ':conditional-effects')
        domain_text = _insert_before_section_close(
            domain_text, ':predicates', f"({marker_name})"
        )
        domain_text = _add_to_action_section_and(
            domain_text, self.action_name, ':effect',
            f"(at end (when (and {equalities}) ({marker_name})))"
        )
        problem_text = _add_to_goal_and(problem_text, f"({marker_name})")
        print(f"INFO: Enforced action '{self.action_name}({', '.join(self.param_object_names)})'")
        return domain_text, problem_text
