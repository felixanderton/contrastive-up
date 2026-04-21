from __future__ import annotations

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
    and_match = re.search(r'\(\s*and\b', domain_text[section_idx:action_close])
    if and_match is None:
        return domain_text
    and_idx = section_idx + and_match.start()
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


def _get_ground_at_end_positive_effects(
    domain_text: str, action_name: str, param_names: list[str], object_names: list[str]
) -> list[str]:
    """Extract and ground the at-end positive effects of a durative action from PDDL text."""
    param_to_obj = {f'?{p}': o for p, o in zip(param_names, object_names)}
    marker = f':durative-action {action_name}'
    kw_idx = domain_text.find(marker)
    if kw_idx == -1:
        return []
    action_open = domain_text.rfind('(', 0, kw_idx)
    action_close = _find_matching_close(domain_text, action_open)
    action_text = domain_text[action_open:action_close + 1]
    effect_start = action_text.find(':effect')
    if effect_start == -1:
        return []
    effect_section = action_text[effect_start:]
    atoms: list[str] = []
    i = 0
    while i < len(effect_section):
        if effect_section[i:i + 8] == '(at end ':
            close = _find_matching_close(effect_section, i)
            if close == -1:
                i += 1
                continue
            content = effect_section[i + 8:close].strip()
            # Skip negations, conditional effects, and numeric effects
            # (increase/decrease/assign/scale-up/scale-down): these aren't
            # propositional atoms and would break preconditions if treated as
            # such.
            head = content.lstrip('(').split(None, 1)[0] if content.startswith('(') else ''
            if (
                not content.startswith('(not')
                and not content.startswith('(when')
                and head not in {
                    'increase', 'decrease', 'assign',
                    'scale-up', 'scale-down',
                }
            ):
                grounded = content
                for param, obj in param_to_obj.items():
                    grounded = re.sub(re.escape(param) + r'\b', obj, grounded)
                atoms.append(grounded)
            i = close + 1
        else:
            i += 1
    return atoms


def _insert_action(domain_text: str, action_text: str) -> str:
    """Append a new action definition before the domain's closing paren."""
    close_idx = _find_matching_close(domain_text, 0)
    if close_idx == -1:
        return domain_text + action_text
    return domain_text[:close_idx] + action_text + '\n' + domain_text[close_idx:]


# ---------------------------------------------------------------------------
# Constraint classes
# ---------------------------------------------------------------------------

class ProhibitedAction:
    def __init__(
        self,
        action_name: str,
        param_object_names: list[str],
        allowed_after: float | None = None,
    ):
        self.action_name = action_name
        self.param_object_names = param_object_names
        # If set, the prohibited instance is allowed to start at t >= allowed_after
        # (a TIL restores the permit at that time).  This turns the all-time ban
        # into a time-windowed ban, which can force a schedule shift rather than
        # outright infeasibility when the action is goal-critical.
        self.allowed_after = allowed_after

    def apply_to_pddl(
        self,
        domain_text: str,
        problem_text: str,
        problem: Problem,
    ) -> tuple[str, str]:
        """
        Prohibit a specific action instance using a positive permit predicate.
        All instances are permitted in init except the prohibited one (blocked
        via a TIL at 0.001 s).  If allowed_after is set, a second TIL restores
        the permit at that time, producing a time-windowed ban.
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
        if self.allowed_after is not None:
            problem_text = _insert_before_section_close(
                problem_text, ':init',
                f"(at {self.allowed_after} ({permit_pred} {args}))"
            )
            print(
                f"INFO: Prohibited '{self.action_name}"
                f"({', '.join(self.param_object_names)})' until t={self.allowed_after}"
            )
            return domain_text, problem_text

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
        Enforce a specific action instance using a fully parametric marker action.
        A typed target predicate (set in :init for the specific grounding only) acts
        as an equality check inside the domain, avoiding ground-object references in
        action bodies (which OPTIC rejects with INTERNAL_ERROR).
        """
        action = problem.action(self.action_name)
        args_str = '_'.join(self.param_object_names)
        goal_pred = f"did_{self.action_name}_{args_str}"
        tgt_pred = f"tgt_{self.action_name}_{args_str}"
        marker_action_name = f"mark_{self.action_name}_{args_str}"

        params_with_types = " ".join(
            f"?{p.name} - {p.type.name}" for p in action.parameters
        )
        params_vars = " ".join(f"?{p.name}" for p in action.parameters)
        args = " ".join(self.param_object_names)

        # Get at-end positive effects parametrically (no substitution)
        at_end_atoms = _get_ground_at_end_positive_effects(
            domain_text, self.action_name, [], []
        )
        precond_parts = [f"(at start {a})" for a in at_end_atoms]
        precond_parts.append(f"(at start ({tgt_pred} {params_vars}))")
        precond = " ".join(precond_parts)

        marker_action = (
            f"\n  (:durative-action {marker_action_name}\n"
            f"    :parameters ({params_with_types})\n"
            f"    :duration (= ?duration 0.01)\n"
            f"    :condition (and {precond})\n"
            f"    :effect (and (at end ({goal_pred})))\n"
            f"  )"
        )

        domain_text = _insert_before_section_close(
            domain_text, ':predicates', f"({goal_pred})"
        )
        domain_text = _insert_before_section_close(
            domain_text, ':predicates', f"({tgt_pred} {params_with_types})"
        )
        domain_text = _insert_action(domain_text, marker_action)

        problem_text = _insert_before_section_close(
            problem_text, ':init', f"({tgt_pred} {args})"
        )
        problem_text = _add_to_goal_and(problem_text, f"({goal_pred})")
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

        Uses the permit+TIL pattern to block the specific after_instance, then a two-step
        parametric release mechanism:
          1. A typed target predicate in :init identifies the before grounding.
          2. A 'set_done' marker action (parametric, typed) sets a propositional done flag
             once the before-instance's at-end effects hold.
          3. A 'release' action re-enables the permit for the after_instance once the done
             flag is set (restricted by a typed target predicate for the after grounding).

        No ground-object references appear in domain action bodies (OPTIC INTERNAL_ERROR).
        No conditional effects (OPTIC rejects (when ...) inside (at end ...)).
        """
        before_action = problem.action(self.before_name)
        after_action = problem.action(self.after_name)

        pred = f"order_{self.after_name}_by_{'_'.join(self.before_params)}"
        after_params_with_types = " ".join(
            f"?{p.name} - {p.type.name}" for p in after_action.parameters
        )
        after_params_vars = " ".join(f"?{p.name}" for p in after_action.parameters)
        after_args = " ".join(self.after_params)
        before_params_with_types = " ".join(
            f"?{p.name} - {p.type.name}" for p in before_action.parameters
        )
        before_params_vars = " ".join(f"?{p.name}" for p in before_action.parameters)
        before_args = " ".join(self.before_params)

        # --- permit predicate on after_action ---
        domain_text = _insert_before_section_close(
            domain_text, ':predicates', f"({pred} {after_params_with_types})"
        )
        domain_text = _add_to_action_section_and(
            domain_text, self.after_name, ':condition',
            f"(at start ({pred} {after_params_vars}))"
        )

        # --- done flag + target predicate for before-instance ---
        done_flag = f"done_{self.before_name}_{'_'.join(self.before_params)}"
        tgt_before = f"tgt_{done_flag}"
        before_at_end = _get_ground_at_end_positive_effects(
            domain_text, self.before_name, [], []
        )
        before_precond_parts = [f"(at start {a})" for a in before_at_end]
        before_precond_parts.append(f"(at start ({tgt_before} {before_params_vars}))")
        before_precond = " ".join(before_precond_parts)

        domain_text = _insert_before_section_close(
            domain_text, ':predicates', f"({done_flag})"
        )
        domain_text = _insert_before_section_close(
            domain_text, ':predicates', f"({tgt_before} {before_params_with_types})"
        )
        set_done_action = (
            f"\n  (:durative-action set_{done_flag}\n"
            f"    :parameters ({before_params_with_types})\n"
            f"    :duration (= ?duration 0.01)\n"
            f"    :condition (and {before_precond})\n"
            f"    :effect (and (at end ({done_flag})))\n"
            f"  )"
        )
        domain_text = _insert_action(domain_text, set_done_action)

        # --- release action re-enables permit for the specific after_instance ---
        tgt_after = f"tgt_{pred}"
        release_name = f"release_{pred}"
        release_precond = (
            f"(at start ({done_flag})) (at start ({tgt_after} {after_params_vars}))"
        )
        domain_text = _insert_before_section_close(
            domain_text, ':predicates', f"({tgt_after} {after_params_with_types})"
        )
        release_action = (
            f"\n  (:durative-action {release_name}\n"
            f"    :parameters ({after_params_with_types})\n"
            f"    :duration (= ?duration 0.01)\n"
            f"    :condition (and {release_precond})\n"
            f"    :effect (and (at end ({pred} {after_params_vars})))\n"
            f"  )"
        )
        domain_text = _insert_action(domain_text, release_action)

        # --- init ---
        problem_text = _insert_before_section_close(
            problem_text, ':init', f"({tgt_before} {before_args})"
        )
        problem_text = _insert_before_section_close(
            problem_text, ':init', f"({tgt_after} {after_args})"
        )
        # All groundings of after_action start permitted; specific instance removed by TIL
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
    def __init__(
        self,
        time: float | int,
        predicate: str,
        args: list[str],
        holds: bool = True,
        end_time: float | int | None = None,
    ):
        self.time = time
        self.predicate = predicate
        self.args = args
        self.holds = holds
        # When set, emit a paired TIL at end_time that flips the literal back
        # to the opposite polarity, producing a two-point window block/restore.
        self.end_time = end_time

    def apply_to_pddl(
        self,
        domain_text: str,
        problem_text: str,
        problem: Problem,
    ) -> tuple[str, str]:
        """Add a timed initial literal to :init (optionally a paired window)."""
        atom = f"({self.predicate} {' '.join(self.args)})" if self.args else f"({self.predicate})"
        til = f"(at {self.time} {atom})" if self.holds else f"(at {self.time} (not {atom}))"
        problem_text = _insert_before_section_close(problem_text, ':init', til)
        print(f"INFO: Added timed literal '{til}'")
        if self.end_time is not None:
            til2 = (
                f"(at {self.end_time} (not {atom}))"
                if self.holds
                else f"(at {self.end_time} {atom})"
            )
            problem_text = _insert_before_section_close(problem_text, ':init', til2)
            print(f"INFO: Added paired timed literal '{til2}'")
        return domain_text, problem_text


class ActionCountLimit:
    def __init__(
        self,
        action_name: str,
        max_uses: int,
        aux_goal: tuple[str, list[str]] | None = None,
    ):
        self.action_name = action_name
        self.max_uses = max_uses
        # Optional auxiliary ground atom appended to (:goal (and ...)) so the
        # cap is exercised against a chain that would normally need >max_uses
        # firings. Used to demonstrate binding behaviour in domains where every
        # baseline action is exactly-once (e.g. CrewPlanning).
        self.aux_goal = aux_goal

    def apply_to_pddl(
        self,
        domain_text: str,
        problem_text: str,
        problem: Problem,
    ) -> tuple[str, str]:
        """Limit the number of times an action can fire using a countdown fluent."""
        counter = f"uses_left_{self.action_name}"
        domain_text = _add_requirement(domain_text, ':numeric-fluents :fluents')
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
        if self.aux_goal is not None:
            pred, args = self.aux_goal
            atom = f"({pred} {' '.join(args)})" if args else f"({pred})"
            problem_text = _add_to_goal_and(problem_text, atom)
            print(f"INFO: Added aux goal '{atom}' for ActionCountLimit")
        print(f"INFO: Limited action '{self.action_name}' to {self.max_uses} use(s)")
        return domain_text, problem_text


def _rewrite_metric(problem_text: str, penalty_term: str) -> str:
    """Append a penalty term to the problem's :metric expression.

    Handles three cases:
    - No :metric section: inserts (:metric minimize (+ (total-time) penalty)).
    - Simple metric expression e.g. (total-time): wraps as (+ expr penalty).
    - Compound (+ ...) metric from a prior Preference: appends penalty inside
      the existing + expression, producing a flat multi-argument (+...).
    """
    metric_kw_idx = problem_text.find(':metric')
    if metric_kw_idx == -1:
        close_idx = _find_matching_close(problem_text, 0)
        new_section = f"\n(:metric minimize (+ (total-time)\n    {penalty_term}))\n"
        return problem_text[:close_idx] + new_section + problem_text[close_idx:]

    metric_section_open = problem_text.rfind('(', 0, metric_kw_idx)
    metric_section_close = _find_matching_close(problem_text, metric_section_open)
    minimize_idx = problem_text.find('minimize', metric_section_open, metric_section_close)
    expr_open = problem_text.find('(', minimize_idx, metric_section_close)
    expr_close = _find_matching_close(problem_text, expr_open)
    expr = problem_text[expr_open:expr_close + 1]

    if expr.startswith('(+'):
        new_expr = expr[:-1] + f'\n    {penalty_term})'
    else:
        new_expr = f'(+ {expr}\n    {penalty_term})'

    return problem_text[:expr_open] + new_expr + problem_text[expr_close + 1:]


_PREFERENCE_FORMULA_TYPES: frozenset[str] = frozenset({
    'always', 'sometime', 'at-most-once', 'sometime-before', 'sometime-after',
})


class Preference:
    def __init__(
        self,
        name: str,
        formula_type: str,
        args: list[list[str]],
        penalty: int | float = 100,
    ):
        if formula_type not in _PREFERENCE_FORMULA_TYPES:
            raise ValueError(
                f"Unsupported formula_type '{formula_type}'. "
                f"Must be one of: {sorted(_PREFERENCE_FORMULA_TYPES)}. "
                f"Note: 'always-within' crashes OPTIC and is excluded."
            )
        self.name = name
        self.formula_type = formula_type
        self.args = args
        self.penalty = penalty

    def apply_to_pddl(
        self,
        domain_text: str,
        problem_text: str,
        problem: Problem,
    ) -> tuple[str, str]:
        """
        Add a soft PDDL 3.0 preference using OPTIC's working syntax.

        Injects (:constraints (preference name (formula ...))) into the problem
        file and appends (* penalty (is-violated name)) to the :metric.

        OPTIC accepts (:constraints ...) in the problem file for preferences —
        the standard (:preferences ...) section syntax is rejected by its parser.
        Supported formula types: always, sometime, at-most-once, sometime-before,
        sometime-after. Do NOT use always-within: it crashes OPTIC.
        """
        atom_strs = [f"({' '.join(atom)})" for atom in self.args]
        if self.formula_type in {'sometime-before', 'sometime-after'}:
            formula = f"({self.formula_type} {atom_strs[0]} {atom_strs[1]})"
        else:
            formula = f"({self.formula_type} {atom_strs[0]})"

        pref_decl = f"(preference {self.name} {formula})"
        penalty_term = f"(* {self.penalty} (is-violated {self.name}))"

        # Inject preference declaration into (:constraints ...) in problem file
        if ':constraints' in problem_text:
            problem_text = _insert_before_section_close(
                problem_text, ':constraints', pref_decl
            )
        else:
            close_idx = _find_matching_close(problem_text, 0)
            constraints_block = f"\n(:constraints\n  {pref_decl}\n)\n"
            problem_text = problem_text[:close_idx] + constraints_block + problem_text[close_idx:]

        # Append penalty to :metric
        problem_text = _rewrite_metric(problem_text, penalty_term)

        # Add :preferences and :constraints requirements to domain
        if ':preferences' not in domain_text:
            domain_text = _add_requirement(domain_text, ':preferences')
        if ':constraints' not in domain_text:
            domain_text = _add_requirement(domain_text, ':constraints')

        print(f"INFO: Added preference '{self.name}' ({self.formula_type}) with penalty {self.penalty}")
        return domain_text, problem_text
