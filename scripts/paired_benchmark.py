"""
paired_benchmark.py

Paired comparison of two encodings of the same ordering constraint:
  1. ActionOrdering (FQ5 hard constraint via guard predicates + release actions)
  2. Preference with sometime-before (PDDL 3.0 soft constraint, high penalty)

Instances: refrigerated delivery + elevators instance-1.
Timing uses time.perf_counter() around OPTIC's solve only; compilation is excluded.
First-solution mode (-N) for every run.
"""
from __future__ import annotations

import csv
import os
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(_PROJECT_ROOT)
sys.path.insert(0, str(_PROJECT_ROOT))

from unified_planning.io import PDDLReader
from unified_planning.model import Problem
from unified_planning.plans import TimeTriggeredPlan

from utils.constraint import ActionOrdering, Preference
from utils.optic import OpticImpl
from utils.plan_diff import _plan_cost

TIMEOUT = 120.0
N_RUNS = 5
PENALTY = 10000
RESULTS_DIR = Path("results")
OUT_CSV = RESULTS_DIR / "paired_benchmark_results.csv"
TMP_DOMAIN = Path("_paired_domain.pddl")
TMP_PROBLEM = Path("_paired_problem.pddl")


@dataclass
class OrderingSpec:
    before_action: str
    before_params: list[str]
    after_action: str
    after_params: list[str]
    before_atom: list[str]   # atom established by before_action (for sometime-before)
    after_atom: list[str]    # atom established by after_action
    pref_name: str


@dataclass
class Row:
    domain: str
    instance: str
    encoding: str
    run_number: int
    wall_clock_seconds: float
    solution_cost: float | None
    preference_satisfied: bool | None


def _sorted_actions(plan: TimeTriggeredPlan) -> list[tuple[float, str, list[str]]]:
    return sorted(
        [(t, ai.action.name, [str(p) for p in ai.actual_parameters]) for t, ai, _ in plan.timed_actions],
        key=lambda x: x[0],
    )


def _solve(
    optic: OpticImpl,
    domain_path: str,
    problem_path: str,
    up_problem: Problem,
) -> tuple[TimeTriggeredPlan | None, float]:
    t0 = time.perf_counter()
    result = optic.solve_files(domain_path, problem_path, up_problem, TIMEOUT, anytime=False)
    elapsed = time.perf_counter() - t0
    return result.plan, elapsed


def _solve_text(
    optic: OpticImpl,
    domain_text: str,
    problem_text: str,
    up_problem: Problem,
) -> tuple[TimeTriggeredPlan | None, float]:
    TMP_DOMAIN.write_text(domain_text)
    TMP_PROBLEM.write_text(problem_text)
    try:
        return _solve(optic, str(TMP_DOMAIN), str(TMP_PROBLEM), up_problem)
    finally:
        TMP_DOMAIN.unlink(missing_ok=True)
        TMP_PROBLEM.unlink(missing_ok=True)


def _pick_refrigerated_ordering(plan: TimeTriggeredPlan) -> OrderingSpec:
    """Order deliver_produce(ce,...,c) AFTER deliver_produce(m,...,b)."""
    actions = _sorted_actions(plan)
    delivers = [(t, n, p) for t, n, p in actions if n == "deliver_produce"]
    meat = next((p for _, _, p in delivers if p[0] == "m" and p[2] == "b"), None)
    cereal = next((p for _, _, p in delivers if p[0] == "ce" and p[2] == "c"), None)
    if meat is None or cereal is None:
        raise RuntimeError(f"Expected deliver_produce(m,_,b) and deliver_produce(ce,_,c) in plan; got {delivers}")
    return OrderingSpec(
        before_action="deliver_produce",
        before_params=meat,
        after_action="deliver_produce",
        after_params=cereal,
        before_atom=["at", "m", "b"],
        after_atom=["at", "ce", "c"],
        pref_name="meat_before_cereal",
    )


def _pick_elevators_ordering(plan: TimeTriggeredPlan) -> OrderingSpec:
    """Order leave(p0,...,n3) AFTER leave(p2,...,n2)."""
    actions = _sorted_actions(plan)
    leaves = [(t, n, p) for t, n, p in actions if n == "leave"]
    p2_leave = next((p for _, _, p in leaves if p[0] == "p2" and p[2] == "n2"), None)
    p0_leave = next((p for _, _, p in leaves if p[0] == "p0" and p[2] == "n3"), None)
    if p2_leave is None or p0_leave is None:
        raise RuntimeError(f"Expected leave(p2,_,n2) and leave(p0,_,n3); got {leaves}")
    return OrderingSpec(
        before_action="leave",
        before_params=p2_leave,
        after_action="leave",
        after_params=p0_leave,
        before_atom=["passenger-at", "p2", "n2"],
        after_atom=["passenger-at", "p0", "n3"],
        pref_name="p2_served_before_p0",
    )


def _verify_ordering(plan: TimeTriggeredPlan, spec: OrderingSpec) -> bool:
    """Check that before_action(before_params) ends before after_action(after_params) starts.

    Uses the action grounding from the plan. Falls back to atom-order check if the
    exact grounding isn't present (because the planner picked different parameters).
    """
    actions = _sorted_actions(plan)
    before_times = [t for t, n, p in actions if n == spec.before_action and p == spec.before_params]
    after_times = [t for t, n, p in actions if n == spec.after_action and p == spec.after_params]
    if before_times and after_times:
        return min(before_times) < min(after_times)
    # Fallback: check by atom-establishing action matching first two params of atom
    def first_occurrence(atom: list[str]) -> float | None:
        name = atom[0]
        args = atom[1:]
        for t, n, p in actions:
            if name == "at" and n == "deliver_produce" and len(p) >= 3 and p[0] == args[0] and p[2] == args[1]:
                return t
            if name == "passenger-at" and n == "leave" and len(p) >= 3 and p[0] == args[0] and p[2] == args[1]:
                return t
        return None
    tb = first_occurrence(spec.before_atom)
    ta = first_occurrence(spec.after_atom)
    if tb is None or ta is None:
        return False
    return tb < ta


def run_instance(
    optic: OpticImpl,
    domain_name: str,
    instance_name: str,
    domain_path: Path,
    problem_path: Path,
    ordering_picker,
    rows: list[Row],
) -> None:
    print(f"\n=== {domain_name} / {instance_name} ===")
    up_problem = PDDLReader().parse_problem(str(domain_path), str(problem_path))
    domain_text = domain_path.read_text()
    problem_text = problem_path.read_text()

    print("  Warm-up baseline solve to extract ordering...")
    warm_plan, _ = _solve(optic, str(domain_path), str(problem_path), up_problem)
    if warm_plan is None:
        print("  FAILED to solve baseline; skipping instance.")
        return
    spec = ordering_picker(warm_plan)
    print(
        f"  Ordering: {spec.before_action}{spec.before_params} BEFORE "
        f"{spec.after_action}{spec.after_params}"
    )

    # Pre-compile constrained PDDL once so timing excludes compilation.
    ao = ActionOrdering(spec.before_action, spec.before_params, spec.after_action, spec.after_params)
    ao_domain, ao_problem = ao.apply_to_pddl(domain_text, problem_text, up_problem)

    pref = Preference(
        name=spec.pref_name,
        formula_type="sometime-before",
        args=[spec.after_atom, spec.before_atom],  # sometime-before AFTER BEFORE
        penalty=PENALTY,
    )
    pref_domain, pref_problem = pref.apply_to_pddl(domain_text, problem_text, up_problem)

    configs = [
        ("unconstrained", lambda: _solve(optic, str(domain_path), str(problem_path), up_problem)),
        ("ActionOrdering", lambda: _solve_text(optic, ao_domain, ao_problem, up_problem)),
        ("Preference", lambda: _solve_text(optic, pref_domain, pref_problem, up_problem)),
    ]

    for encoding, runner in configs:
        for i in range(1, N_RUNS + 1):
            plan, elapsed = runner()
            cost = _plan_cost(plan) if plan is not None else None
            satisfied: bool | None = None
            if encoding == "Preference" and plan is not None:
                satisfied = _verify_ordering(plan, spec)
                if not satisfied:
                    print(f"    [WARN] Preference plan violates ordering (run {i})")
            elif encoding == "ActionOrdering" and plan is not None:
                satisfied = _verify_ordering(plan, spec)
            print(
                f"  {encoding:15s} run {i}: {elapsed:7.3f}s  cost="
                f"{cost if cost is not None else 'NO PLAN'}"
                + (f"  pref_ok={satisfied}" if satisfied is not None else "")
            )
            rows.append(Row(
                domain=domain_name,
                instance=instance_name,
                encoding=encoding,
                run_number=i,
                wall_clock_seconds=round(elapsed, 4),
                solution_cost=cost,
                preference_satisfied=satisfied,
            ))


def write_csv(rows: list[Row], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "domain", "instance", "encoding", "run_number",
            "wall_clock_seconds", "solution_cost", "preference_satisfied",
        ])
        for r in rows:
            w.writerow([
                r.domain, r.instance, r.encoding, r.run_number,
                r.wall_clock_seconds,
                "" if r.solution_cost is None else r.solution_cost,
                "" if r.preference_satisfied is None else r.preference_satisfied,
            ])
    print(f"\nCSV written → {path}")


def print_summary(rows: list[Row]) -> None:
    print("\n" + "=" * 78)
    print("SUMMARY: Mean planning time (s) per encoding per instance")
    print("=" * 78)
    key_set: list[tuple[str, str]] = []
    for r in rows:
        k = (r.domain, r.instance)
        if k not in key_set:
            key_set.append(k)

    header = f"{'domain/instance':35s} {'unconstr':>10s} {'FQ5 AO':>10s} {'Pref':>10s} {'FQ5-Pref':>10s}"
    print(header)
    print("-" * len(header))
    for dom, inst in key_set:
        def mean_for(enc: str) -> float | None:
            vs = [r.wall_clock_seconds for r in rows
                  if r.domain == dom and r.instance == inst and r.encoding == enc
                  and r.solution_cost is not None]
            return statistics.mean(vs) if vs else None

        unc = mean_for("unconstrained")
        ao = mean_for("ActionOrdering")
        pr = mean_for("Preference")
        delta = (ao - pr) if (ao is not None and pr is not None) else None
        def fmt(x: float | None) -> str:
            return "  NO PLAN" if x is None else f"{x:10.3f}"
        print(f"{dom + '/' + inst:35s} {fmt(unc)} {fmt(ao)} {fmt(pr)} {fmt(delta)}")

    # Preference-satisfaction check
    violations = [r for r in rows if r.encoding == "Preference" and r.preference_satisfied is False]
    if violations:
        print(f"\n[WARN] {len(violations)} Preference runs did NOT satisfy the ordering.")
    else:
        pref_runs = [r for r in rows if r.encoding == "Preference" and r.solution_cost is not None]
        print(f"\nAll {len(pref_runs)} Preference plans satisfy the ordering.")


def main() -> None:
    optic = OpticImpl()
    rows: list[Row] = []

    run_instance(
        optic,
        domain_name="refrigerated",
        instance_name="instance-1",
        domain_path=Path("pddl/correctness_tests/refrigerated_delivery_domain.pddl"),
        problem_path=Path("pddl/correctness_tests/refrigerated_delivery_problem.pddl"),
        ordering_picker=_pick_refrigerated_ordering,
        rows=rows,
    )
    run_instance(
        optic,
        domain_name="elevators",
        instance_name="instance-1",
        domain_path=Path("pddl/benchmarks/elevators/domain.pddl"),
        problem_path=Path("pddl/benchmarks/elevators/instances/instance-1.pddl"),
        ordering_picker=_pick_elevators_ordering,
        rows=rows,
    )

    write_csv(rows, OUT_CSV)
    print_summary(rows)


if __name__ == "__main__":
    main()
