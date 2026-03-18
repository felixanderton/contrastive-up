import re
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
        domain_text = _add_requirement(domain_text, ':equality')
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


class ActionOrdering:
    def __init__(
        self,
        before_name: str,
        before_params: list[str],
        after_name: str,
        after_params: list[str],
    ):
        self.before_name = before_name
        self.before_params = before_params
        self.after_name = after_name
        self.after_params = after_params

    def apply_to_pddl(
        self,
        domain_text: str,
        problem_text: str,
        problem: Problem,
    ) -> tuple[str, str]:
        """
        Enforce ordering: after_instance can only start once before_instance completes.
        Uses the same permit+TIL pattern as ProhibitedAction, but re-enables the
        permit via a conditional effect on before_action rather than leaving it removed.
        Applies only to the specific after_instance; all other groundings of after_action
        are unrestricted.
        """
        before_action = problem.action(self.before_name)
        after_action = problem.action(self.after_name)

        pred = f"order_{self.after_name}_by_{'_'.join(self.before_params)}"
        after_params_with_types = " ".join(
            f"?{p.name} - {p.type.name}" for p in after_action.parameters
        )
        after_params_vars = " ".join(f"?{p.name}" for p in after_action.parameters)
        after_args = " ".join(self.after_params)
        before_equalities = " ".join(
            f"(= ?{p.name} {o})"
            for p, o in zip(before_action.parameters, self.before_params)
        )

        domain_text = _add_requirement(domain_text, ':conditional-effects')
        domain_text = _add_requirement(domain_text, ':equality')
        domain_text = _insert_before_section_close(
            domain_text, ':predicates', f"({pred} {after_params_with_types})"
        )
        # after_action requires the permit at start
        domain_text = _add_to_action_section_and(
            domain_text, self.after_name, ':condition',
            f"(at start ({pred} {after_params_vars}))"
        )
        # before_action re-enables the specific permit when it fires with before_params
        domain_text = _add_to_action_section_and(
            domain_text, self.before_name, ':effect',
            f"(at end (when (and {before_equalities}) ({pred} {after_args})))"
        )

        # All groundings start permitted; specific after_instance is removed by TIL
        # and re-added only when before_instance completes.
        objects_per_param = [
            [o.name for o in problem.objects(p.type)] for p in after_action.parameters
        ]
        for combo in iterproduct(*objects_per_param):
            problem_text = _insert_before_section_close(
                problem_text, ':init', f"({pred} {' '.join(combo)})"
            )
        problem_text = _insert_before_section_close(
            problem_text, ':init', f"(at 0.001 (not ({pred} {after_args})))"
        )

        print(
            f"INFO: Ordered '{self.after_name}({', '.join(self.after_params)})'"
            f" to start after '{self.before_name}({', '.join(self.before_params)})' completes"
        )
        return domain_text, problem_text


class AtomGoal:
    def __init__(self, predicate: str, args: list[str]):
        self.predicate = predicate
        self.args = args

    def apply_to_pddl(
        self,
        domain_text: str,
        problem_text: str,
        problem: Problem,
    ) -> tuple[str, str]:
        """Add a ground atom to the problem goal."""
        atom = f"({self.predicate} {' '.join(self.args)})" if self.args else f"({self.predicate})"
        problem_text = _add_to_goal_and(problem_text, atom)
        print(f"INFO: Added goal atom '{atom}'")
        return domain_text, problem_text


class FluentChange:
    def __init__(self, fluent: str, args: list[str], new_value: float | int):
        self.fluent = fluent
        self.args = args
        self.new_value = new_value

    def apply_to_pddl(
        self,
        domain_text: str,
        problem_text: str,
        problem: Problem,
    ) -> tuple[str, str]:
        """Replace an existing numeric fluent assignment in :init, or add it if absent."""
        fluent_atom = f"({self.fluent} {' '.join(self.args)})" if self.args else f"({self.fluent})"
        pattern = re.escape(f"(= {fluent_atom}") + r"\s+[^\)]+\)"
        replacement = f"(= {fluent_atom} {self.new_value})"
        new_text, n = re.subn(pattern, replacement, problem_text)
        if n > 0:
            problem_text = new_text
        else:
            problem_text = _insert_before_section_close(problem_text, ':init', replacement)
        print(f"INFO: Set fluent '{fluent_atom}' to {self.new_value}")
        return domain_text, problem_text


class TimedLiteral:
    def __init__(self, time: float | int, predicate: str, args: list[str], holds: bool = True):
        self.time = time
        self.predicate = predicate
        self.args = args
        self.holds = holds

    def apply_to_pddl(
        self,
        domain_text: str,
        problem_text: str,
        problem: Problem,
    ) -> tuple[str, str]:
        """Add a timed initial literal to :init."""
        atom = f"({self.predicate} {' '.join(self.args)})" if self.args else f"({self.predicate})"
        til = f"(at {self.time} {atom})" if self.holds else f"(at {self.time} (not {atom}))"
        problem_text = _insert_before_section_close(problem_text, ':init', til)
        print(f"INFO: Added timed literal '{til}'")
        return domain_text, problem_text


class ActionCountLimit:
    def __init__(self, action_name: str, max_uses: int):
        self.action_name = action_name
        self.max_uses = max_uses

    def apply_to_pddl(
        self,
        domain_text: str,
        problem_text: str,
        problem: Problem,
    ) -> tuple[str, str]:
        """Limit the number of times an action can fire using a countdown fluent."""
        counter = f"uses_left_{self.action_name}"
        domain_text = _add_requirement(domain_text, ':numeric-fluents')
        if ':functions' in domain_text:
            domain_text = _insert_before_section_close(
                domain_text, ':functions', f"({counter})"
            )
        else:
            domain_text = _insert_before_section_close(
                domain_text, ':predicates', f")\n  (:functions\n    ({counter})"
            )
        domain_text = _add_to_action_section_and(
            domain_text, self.action_name, ':condition',
            f"(at start (> ({counter}) 0))"
        )
        domain_text = _add_to_action_section_and(
            domain_text, self.action_name, ':effect',
            f"(at start (decrease ({counter}) 1))"
        )
        problem_text = _insert_before_section_close(
            problem_text, ':init', f"(= ({counter}) {self.max_uses})"
        )
        print(f"INFO: Limited action '{self.action_name}' to {self.max_uses} use(s)")
        return domain_text, problem_text
