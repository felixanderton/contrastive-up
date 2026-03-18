import subprocess
import re
import os
import sys
from typing import Callable, IO, Optional, List, Tuple, Union

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
        # OPTIC is very capable. We list all features it supports 
        # so UP doesn't block the problem before we even try.
        supported_kind = up.model.ProblemKind()
        supported_kind.set_problem_class("ACTION_BASED")
        
        # Types
        supported_kind.set_typing('FLAT_TYPING')
        supported_kind.set_typing('HIERARCHICAL_TYPING')
        
        # Time
        supported_kind.set_time('CONTINUOUS_TIME')
        supported_kind.set_time('DISCRETE_TIME')
        supported_kind.set_time('INTERMEDIATE_CONDITIONS_AND_EFFECTS')
        supported_kind.set_time('TIMED_EFFECTS')
        supported_kind.set_time('TIMED_GOALS')
        supported_kind.set_time('DURATION_INEQUALITIES')
        supported_kind.set_time('SELF_OVERLAPPING')

        # Expression duration
        supported_kind.set_expression_duration('STATIC_FLUENTS_IN_DURATIONS')
        supported_kind.set_expression_duration('FLUENTS_IN_DURATIONS')
        supported_kind.set_expression_duration('INT_TYPE_DURATIONS')
        supported_kind.set_expression_duration('REAL_TYPE_DURATIONS')

        # Initial state
        supported_kind.set_initial_state('UNDEFINED_INITIAL_NUMERIC')
        # Numbers
        supported_kind.set_numbers('CONTINUOUS_NUMBERS')
        supported_kind.set_numbers('DISCRETE_NUMBERS')
        supported_kind.set_numbers('BOUNDED_TYPES')
        
        # Fluents
        supported_kind.set_fluents_type('NUMERIC_FLUENTS')
        supported_kind.set_fluents_type('OBJECT_FLUENTS')
        
        # Conditions / Effects
        supported_kind.set_conditions_kind('NEGATIVE_CONDITIONS')
        supported_kind.set_conditions_kind('DISJUNCTIVE_CONDITIONS')
        supported_kind.set_conditions_kind('EQUALITIES')
        supported_kind.set_conditions_kind('EXISTENTIAL_CONDITIONS')
        supported_kind.set_conditions_kind('UNIVERSAL_CONDITIONS')
        supported_kind.set_effects_kind('CONDITIONAL_EFFECTS')
        supported_kind.set_effects_kind('INCREASE_EFFECTS')
        supported_kind.set_effects_kind('DECREASE_EFFECTS')
        
        # Metrics
        supported_kind.set_quality_metrics('ACTIONS_COST')
        supported_kind.set_quality_metrics('MAKESPAN')
        supported_kind.set_quality_metrics('PLAN_LENGTH') # Required for problems with (:metric minimize (total-cost))

        return supported_kind

    @staticmethod
    def supports(problem_kind):
        # We claim to support almost anything compatible with PDDL 2.1+
        return problem_kind <= OpticImpl.supported_kind()

    def _solve_with_params(
        self,
        problem: 'up.model.Problem',
        heuristic: Optional[Callable[["up.model.state.State"], Optional[float]]] = None,
        timeout: Optional[float] = None,
        output_stream: Optional[IO[str]] = None,
        warm_start_plan: Optional["up.plans.Plan"] = None,
        **kwargs,
    ) -> 'up.engines.PlanGenerationResult':
        
        # 1. Prepare file paths
        domain_filename = "domain_optic_temp.pddl"
        problem_filename = "problem_optic_temp.pddl"

        # 2. Write the PDDL files using UP's built-in writer
        # This handles the translation from UP objects to PDDL syntax
        writer = PDDLWriter(problem)
        writer.write_domain(domain_filename)
        writer.write_problem(problem_filename)

        # 3. Construct the command
        # No -N: anytime mode — OPTIC keeps improving the plan until it proves
        # optimality or the subprocess timeout is reached. The last solution found
        # is used, which is the best one OPTIC produced within the time budget.
        cmd = [self.executable_path, domain_filename, problem_filename]
        timeout = timeout if timeout is not None else 300

        # 4. Run Subprocess
        logs = []
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            output = res.stdout
            logs.append(LogMessage(LogLevel.INFO, "OPTIC Executed successfully"))
        except subprocess.TimeoutExpired as e:
            # In anytime mode OPTIC may have already found and printed solutions
            # before being killed — use whatever output was captured.
            raw = e.stdout or b""
            output = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            if "Solution Found" not in output:
                return PlanGenerationResult(PlanGenerationResultStatus.TIMEOUT, None, self.name, log_messages=logs)
            logs.append(LogMessage(LogLevel.INFO, "OPTIC timed out but a solution was found"))
        except FileNotFoundError:
            return PlanGenerationResult(
                PlanGenerationResultStatus.INTERNAL_ERROR, 
                None, 
                self.name, 
                log_messages=[LogMessage(LogLevel.ERROR, f"Executable not found at {self.executable_path}")]
            )
        finally:
            # Cleanup temp files
            if os.path.exists(domain_filename): os.remove(domain_filename)
            if os.path.exists(problem_filename): os.remove(problem_filename)

        # 5. Parse Output
        if "Solution Found" not in output:
             return PlanGenerationResult(PlanGenerationResultStatus.UNSOLVABLE_INCOMPLETELY, None, self.name, log_messages=logs)

        # In anytime mode OPTIC emits multiple improving plans; only the last is optimal.
        # Split on the marker and take the final block.
        last_plan_block = output.split("Solution Found")[-1]

        # Regex to capture: StartTime, ActionName, Args, Duration
        # Example line: 0.000: (load_truck m t1 a) [0.010]
        regex = r"^\s*(\d+(?:\.\d+)?):\s*\(([^)]+)\)\s*\[(\d+(?:\.\d+)?)\]"

        plan_items = []

        for line in last_plan_block.splitlines():
            match = re.search(regex, line)
            if match:
                start_time = float(match.group(1))
                content = match.group(2).split() # e.g. ['load_truck', 'm', 't1', 'a']
                duration = float(match.group(3))
                
                action_name = content[0]
                obj_names = content[1:]

                # Map strings back to UP Objects
                try:
                    # Find the UP Action object
                    up_action = problem.action(action_name)
                    
                    # Find the UP Object parameters
                    # Note: We must look up the objects in the problem definition
                    params = []
                    for obj_name in obj_names:
                        params.append(problem.object(obj_name))

                    # Create the ActionInstance
                    # (Unified Planning requires parameters to be Value/Object types)
                    action_instance = ActionInstance(up_action, tuple(params))
                    
                    # Add to plan list: (start, action, duration)
                    plan_items.append((start_time, action_instance, duration))
                    
                except Exception as e:
                    logs.append(LogMessage(LogLevel.ERROR, f"Error parsing line '{line}': {e}"))
                    return PlanGenerationResult(PlanGenerationResultStatus.INTERNAL_ERROR, None, self.name, log_messages=logs)

        # 6. Create the TimeTriggeredPlan
        # We pass the plan_items list which contains tuples of (start, action, duration)
        final_plan = TimeTriggeredPlan(plan_items)
        
        return PlanGenerationResult(
            PlanGenerationResultStatus.SOLVED_OPTIMALLY, # Assumes OPTIC ran successfully
            final_plan, 
            self.name, 
            metrics={"engine_output": output},
            log_messages=logs
        )

    def _solve(self, problem, heuristic=None, timeout=None, output_stream=None):
        # This method is deprecated in favor of `_solve_with_params`.
        # This method is kept for backward compatibility with older versions of UPF.
        # You should use this exact override in your own solver to pass the call to `_solve_with_params`.
        return self._solve_with_params(problem, heuristic, timeout, output_stream)

    def destroy(self):
        pass