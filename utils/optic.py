import subprocess
import re
import os
from typing import Callable, IO, Optional

import unified_planning as up
from unified_planning import engines
from unified_planning.io import PDDLWriter
from unified_planning.plans import TimeTriggeredPlan, ActionInstance
from unified_planning.engines.results import PlanGenerationResult, PlanGenerationResultStatus, LogMessage, LogLevel


class OpticImpl(up.engines.Engine, up.engines.mixins.OneshotPlannerMixin):
    def __init__(self, executable_path: str = './optic-clp', **options):
        up.engines.Engine.__init__(self)
        up.engines.mixins.OneshotPlannerMixin.__init__(self)
        self.executable_path = executable_path

    @property
    def name(self) -> str:
        return "OPTIC"

    @staticmethod
    def supported_kind() -> up.model.ProblemKind:
        supported_kind = up.model.ProblemKind()
        supported_kind.set_problem_class("ACTION_BASED")
        supported_kind.set_typing('FLAT_TYPING')
        supported_kind.set_typing('HIERARCHICAL_TYPING')
        supported_kind.set_time('CONTINUOUS_TIME')
        supported_kind.set_time('DISCRETE_TIME')
        supported_kind.set_time('INTERMEDIATE_CONDITIONS_AND_EFFECTS')
        supported_kind.set_time('TIMED_EFFECTS')
        supported_kind.set_time('TIMED_GOALS')
        supported_kind.set_time('DURATION_INEQUALITIES')
        supported_kind.set_time('SELF_OVERLAPPING')
        supported_kind.set_expression_duration('STATIC_FLUENTS_IN_DURATIONS')
        supported_kind.set_expression_duration('FLUENTS_IN_DURATIONS')
        supported_kind.set_expression_duration('INT_TYPE_DURATIONS')
        supported_kind.set_expression_duration('REAL_TYPE_DURATIONS')
        supported_kind.set_initial_state('UNDEFINED_INITIAL_NUMERIC')
        supported_kind.set_numbers('CONTINUOUS_NUMBERS')
        supported_kind.set_numbers('DISCRETE_NUMBERS')
        supported_kind.set_numbers('BOUNDED_TYPES')
        supported_kind.set_fluents_type('NUMERIC_FLUENTS')
        supported_kind.set_fluents_type('OBJECT_FLUENTS')
        supported_kind.set_conditions_kind('NEGATIVE_CONDITIONS')
        supported_kind.set_conditions_kind('DISJUNCTIVE_CONDITIONS')
        supported_kind.set_conditions_kind('EQUALITIES')
        supported_kind.set_conditions_kind('EXISTENTIAL_CONDITIONS')
        supported_kind.set_conditions_kind('UNIVERSAL_CONDITIONS')
        supported_kind.set_effects_kind('CONDITIONAL_EFFECTS')
        supported_kind.set_effects_kind('INCREASE_EFFECTS')
        supported_kind.set_effects_kind('DECREASE_EFFECTS')
        supported_kind.set_quality_metrics('ACTIONS_COST')
        supported_kind.set_quality_metrics('MAKESPAN')
        supported_kind.set_quality_metrics('PLAN_LENGTH')
        return supported_kind

    @staticmethod
    def supports(problem_kind):
        return problem_kind <= OpticImpl.supported_kind()

    # ------------------------------------------------------------------
    # Public entry point for file-based solving (bypasses PDDLWriter)
    # ------------------------------------------------------------------

    def solve_files(
        self,
        domain_path: str,
        problem_path: str,
        up_problem: 'up.model.Problem',
        timeout: float | None = None,
    ) -> 'PlanGenerationResult':
        """
        Run OPTIC directly on the provided PDDL files.
        up_problem is used only for action/object lookup when parsing the plan output.
        This bypasses PDDLWriter so the planner sees the original PDDL syntax unchanged.
        """
        cmd = [self.executable_path, domain_path, problem_path]
        return self._run_optic(cmd, up_problem, timeout)

    # ------------------------------------------------------------------
    # UP engine interface (uses PDDLWriter — kept for compatibility)
    # ------------------------------------------------------------------

    def _solve_with_params(
        self,
        problem: 'up.model.Problem',
        heuristic: Optional[Callable[["up.model.state.State"], Optional[float]]] = None,
        timeout: Optional[float] = None,
        output_stream: Optional[IO[str]] = None,
        warm_start_plan: Optional["up.plans.Plan"] = None,
        **kwargs,
    ) -> 'PlanGenerationResult':
        domain_filename = "domain_optic_temp.pddl"
        problem_filename = "problem_optic_temp.pddl"
        writer = PDDLWriter(problem)
        writer.write_domain(domain_filename)
        writer.write_problem(problem_filename)
        try:
            cmd = [self.executable_path, domain_filename, problem_filename]
            return self._run_optic(cmd, problem, timeout)
        finally:
            if os.path.exists(domain_filename):
                os.remove(domain_filename)
            if os.path.exists(problem_filename):
                os.remove(problem_filename)

    def _solve(self, problem, heuristic=None, timeout=None, output_stream=None):
        return self._solve_with_params(problem, heuristic, timeout, output_stream)

    def destroy(self):
        pass

    # ------------------------------------------------------------------
    # Shared subprocess + plan-parsing logic
    # ------------------------------------------------------------------

    def _run_optic(
        self,
        cmd: list[str],
        up_problem: 'up.model.Problem',
        timeout: float | None,
    ) -> 'PlanGenerationResult':
        timeout = timeout if timeout is not None else 300
        logs = []
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            output = res.stdout
            logs.append(LogMessage(LogLevel.INFO, "OPTIC executed successfully"))
        except subprocess.TimeoutExpired as e:
            raw = e.stdout or b""
            output = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            if "Solution Found" not in output:
                return PlanGenerationResult(
                    PlanGenerationResultStatus.TIMEOUT, None, self.name, log_messages=logs
                )
            logs.append(LogMessage(LogLevel.INFO, "OPTIC timed out but a solution was found"))
        except FileNotFoundError:
            return PlanGenerationResult(
                PlanGenerationResultStatus.INTERNAL_ERROR,
                None,
                self.name,
                log_messages=[LogMessage(LogLevel.ERROR, f"Executable not found at {self.executable_path}")],
            )

        if "Solution Found" not in output:
            return PlanGenerationResult(
                PlanGenerationResultStatus.UNSOLVABLE_INCOMPLETELY, None, self.name, log_messages=logs
            )

        # In anytime mode OPTIC emits multiple improving plans; only the last is optimal.
        last_plan_block = output.split("Solution Found")[-1]

        regex = r"^\s*(\d+(?:\.\d+)?):\s*\(([^)]+)\)\s*\[(\d+(?:\.\d+)?)\]"
        plan_items = []

        for line in last_plan_block.splitlines():
            match = re.search(regex, line)
            if match:
                start_time = float(match.group(1))
                content = match.group(2).split()
                duration = float(match.group(3))
                action_name = content[0]
                obj_names = content[1:]
                try:
                    up_action = up_problem.action(action_name)
                    params = [up_problem.object(n) for n in obj_names]
                    plan_items.append((start_time, ActionInstance(up_action, tuple(params)), duration))
                except Exception as e:
                    logs.append(LogMessage(LogLevel.ERROR, f"Error parsing line '{line}': {e}"))
                    return PlanGenerationResult(
                        PlanGenerationResultStatus.INTERNAL_ERROR, None, self.name, log_messages=logs
                    )

        final_plan = TimeTriggeredPlan(plan_items)
        return PlanGenerationResult(
            PlanGenerationResultStatus.SOLVED_OPTIMALLY,
            final_plan,
            self.name,
            metrics={"engine_output": output},
            log_messages=logs,
        )
