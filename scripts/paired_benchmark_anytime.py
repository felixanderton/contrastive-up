"""
paired_benchmark_anytime.py

Anytime-mode paired comparison with a 10s timeout.

For each (instance, encoding) runs OPTIC without -N, streams stdout, and records
wall-clock time of FIRST ``; Plan found`` emission and cost of FINAL plan.
Encodings compared: ActionOrdering (FQ5) vs Preference (sometime-before, penalty 10000).
Same orderings as paired_benchmark.py.
"""
from __future__ import annotations

import csv
import os
import re
import statistics
import subprocess
import sys
import threading
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

TIMEOUT = 10.0
N_RUNS = 5
PENALTY = 10000
PLANNER = "./optic-clp"
RESULTS_DIR = Path("results")
OUT_CSV = RESULTS_DIR / "paired_benchmark_anytime_results.csv"
TMP_DOMAIN = Path("_paired_any_domain.pddl")
TMP_PROBLEM = Path("_paired_any_problem.pddl")


@dataclass
class OrderingSpec:
    before_action: str
    before_params: list[str]
    after_action: str
    after_params: list[str]
    before_atom: list[str]
    after_atom: list[str]
    pref_name: str


@dataclass
class Row:
    domain: str
    instance: str
    encoding: str
    run_number: int
    time_to_first_s: float | None
    final_cost: float | None
    n_improvements: int
    preference_satisfied: bool | None
    timed_out: bool


def _run_anytime(domain_path: str, problem_path: str, timeout: float) -> tuple[str, float | None, float]:
    """Run OPTIC without -N; return (full_output, time_to_first_plan, wall_elapsed)."""
    cmd = [PLANNER, domain_path, problem_path]
    print(f"Running: {' '.join(cmd)}", flush=True)
    t0 = time.perf_counter()
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    lines: list[str] = []
    time_to_first: list[float | None] = [None]

    def _read() -> None:
        for line in process.stdout:  # type: ignore[union-attr]
            lines.append(line)
            if time_to_first[0] is None and "; Plan found" in line:
                time_to_first[0] = time.perf_counter() - t0

    reader = threading.Thread(target=_read, daemon=True)
    reader.start()

    deadline = t0 + timeout
    while True:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            process.kill()
            break
        try:
            process.wait(timeout=min(0.2, remaining))
            break
        except subprocess.TimeoutExpired:
            pass
    reader.join(timeout=1.0)
    elapsed = time.perf_counter() - t0
    return "".join(lines), time_to_first[0], elapsed


def _parse_plans(output: str) -> list[tuple[float, list[tuple[float, str, list[str]]]]]:
    """Return list of (metric_cost, action_list) for each '; Plan found with metric' block."""
    blocks = output.split("; Plan found with metric ")
    plans: list[tuple[float, list[tuple[float, str, list[str]]]]] = []
    action_re = re.compile(r"^\s*(\d+(?:\.\d+)?):\s*\(([^)]+)\)\s*\[(\d+(?:\.\d+)?)\]")
    for b in blocks[1:]:
        first_line, _, rest = b.partition("\n")
        try:
            cost = float(first_line.strip())
        except ValueError:
            continue
        actions: list[tuple[float, str, list[str]]] = []
        for line in rest.splitlines():
            m = action_re.match(line)
            if m:
                t = float(m.group(1))
                parts = m.group(2).split()
                actions.append((t, parts[0], parts[1:]))
        plans.append((cost, actions))
    return plans


def _verify_ordering(actions: list[tuple[float, str, list[str]]], spec: OrderingSpec) -> bool:
    before_times = [t for t, n, p in actions if n == spec.before_action and p == spec.before_params]
    after_times = [t for t, n, p in actions if n == spec.after_action and p == spec.after_params]
    if before_times and after_times:
        return min(before_times) < min(after_times)

    def first_occurrence(atom: list[str]) -> float | None:
        name, args = atom[0], atom[1:]
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


def _makespan(actions: list[tuple[float, str, list[str]]]) -> float | None:
    if not actions:
        return None
    return max(t for t, _, _ in actions)


def _pick_refrigerated_ordering(actions: list[tuple[float, str, list[str]]]) -> OrderingSpec:
    delivers = [(t, n, p) for t, n, p in actions if n == "deliver_produce"]
    meat = next((p for _, _, p in delivers if p[0] == "m" and p[2] == "b"), None)
    cereal = next((p for _, _, p in delivers if p[0] == "ce" and p[2] == "c"), None)
    if meat is None or cereal is None:
        raise RuntimeError(f"unexpected deliver_produce actions: {delivers}")
    return OrderingSpec("deliver_produce", meat, "deliver_produce", cereal,
                        ["at", "m", "b"], ["at", "ce", "c"], "meat_before_cereal")


def _pick_elevators_ordering(actions: list[tuple[float, str, list[str]]]) -> OrderingSpec:
    leaves = [(t, n, p) for t, n, p in actions if n == "leave"]
    p2 = next((p for _, _, p in leaves if p[0] == "p2" and p[2] == "n2"), None)
    p0 = next((p for _, _, p in leaves if p[0] == "p0" and p[2] == "n3"), None)
    if p2 is None or p0 is None:
        raise RuntimeError(f"unexpected leave actions: {leaves}")
    return OrderingSpec("leave", p2, "leave", p0,
                        ["passenger-at", "p2", "n2"], ["passenger-at", "p0", "n3"],
                        "p2_served_before_p0")


def run_instance(
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
    warm_output, _, _ = _run_anytime(str(domain_path), str(problem_path), TIMEOUT)
    warm_plans = _parse_plans(warm_output)
    if not warm_plans:
        print("  Warm-up failed")
        return
    spec = ordering_picker(warm_plans[-1][1])
    print(
        f"  Ordering: {spec.before_action}{spec.before_params} BEFORE "
        f"{spec.after_action}{spec.after_params}"
    )

    ao = ActionOrdering(spec.before_action, spec.before_params, spec.after_action, spec.after_params)
    ao_domain, ao_problem = ao.apply_to_pddl(domain_text, problem_text, up_problem)
    pref = Preference(
        name=spec.pref_name,
        formula_type="sometime-before",
        args=[spec.after_atom, spec.before_atom],
        penalty=PENALTY,
    )
    pref_domain, pref_problem = pref.apply_to_pddl(domain_text, problem_text, up_problem)

    configs = [
        ("ActionOrdering", ao_domain, ao_problem),
        ("Preference", pref_domain, pref_problem),
    ]

    for encoding, dtext, ptext in configs:
        TMP_DOMAIN.write_text(dtext)
        TMP_PROBLEM.write_text(ptext)
        try:
            for i in range(1, N_RUNS + 1):
                output, ttf, elapsed = _run_anytime(str(TMP_DOMAIN), str(TMP_PROBLEM), TIMEOUT)
                plans = _parse_plans(output)
                timed_out = elapsed >= TIMEOUT - 0.1
                if plans:
                    final_actions = plans[-1][1]
                    final_cost = _makespan(final_actions)
                    satisfied = _verify_ordering(final_actions, spec)
                else:
                    final_cost = None
                    satisfied = None
                n_imp = len(plans)
                print(
                    f"  {encoding:15s} run {i}: ttf={ttf if ttf is None else f'{ttf:.3f}s':8s}"
                    f" final_cost={final_cost} improvements={n_imp} pref_ok={satisfied} timed_out={timed_out}"
                )
                rows.append(Row(
                    domain=domain_name, instance=instance_name, encoding=encoding,
                    run_number=i,
                    time_to_first_s=None if ttf is None else round(ttf, 4),
                    final_cost=final_cost,
                    n_improvements=n_imp,
                    preference_satisfied=satisfied,
                    timed_out=timed_out,
                ))
        finally:
            TMP_DOMAIN.unlink(missing_ok=True)
            TMP_PROBLEM.unlink(missing_ok=True)


def write_csv(rows: list[Row], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "domain", "instance", "encoding", "run_number",
            "time_to_first_s", "final_cost", "n_improvements",
            "preference_satisfied", "timed_out",
        ])
        for r in rows:
            w.writerow([
                r.domain, r.instance, r.encoding, r.run_number,
                "" if r.time_to_first_s is None else r.time_to_first_s,
                "" if r.final_cost is None else r.final_cost,
                r.n_improvements,
                "" if r.preference_satisfied is None else r.preference_satisfied,
                r.timed_out,
            ])
    print(f"\nCSV written → {path}")


def print_summary(rows: list[Row]) -> None:
    print("\n" + "=" * 90)
    print("SUMMARY: anytime mode, 10s timeout")
    print("=" * 90)
    keys: list[tuple[str, str]] = []
    for r in rows:
        k = (r.domain, r.instance)
        if k not in keys:
            keys.append(k)
    hdr = f"{'domain/instance':28s} {'encoding':15s} {'mean_ttf(s)':>12s} {'mean_final_cost':>18s} {'pref_ok':>10s}"
    print(hdr)
    print("-" * len(hdr))
    for dom, inst in keys:
        for enc in ("ActionOrdering", "Preference"):
            rs = [r for r in rows if r.domain == dom and r.instance == inst and r.encoding == enc]
            ttfs = [r.time_to_first_s for r in rs if r.time_to_first_s is not None]
            costs = [r.final_cost for r in rs if r.final_cost is not None]
            ok = [r.preference_satisfied for r in rs if r.preference_satisfied is not None]
            ttf_mean = f"{statistics.mean(ttfs):.3f}" if ttfs else "—"
            cost_mean = f"{statistics.mean(costs):.3f}" if costs else "—"
            ok_frac = f"{sum(bool(x) for x in ok)}/{len(ok)}" if ok else "—"
            print(f"{dom + '/' + inst:28s} {enc:15s} {ttf_mean:>12s} {cost_mean:>18s} {ok_frac:>10s}")


def main() -> None:
    rows: list[Row] = []
    run_instance(
        domain_name="refrigerated",
        instance_name="instance-1",
        domain_path=Path("pddl/correctness_tests/refrigerated_delivery_domain.pddl"),
        problem_path=Path("pddl/correctness_tests/refrigerated_delivery_problem.pddl"),
        ordering_picker=_pick_refrigerated_ordering,
        rows=rows,
    )
    run_instance(
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
