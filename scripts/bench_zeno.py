#!/usr/bin/env python3
"""Run the full benchmark grid for ZenoTravel only.

3 instances x 2 sets x 8 constraint types = 48 cells (+ 6 unconstrained
baselines).  Writes benchmark_results_zeno.csv.
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(_PROJECT_ROOT)
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from unified_planning.io import PDDLReader  # noqa: E402

import benchmark as bv2  # noqa: E402
from utils.optic import OpticImpl  # noqa: E402


TIMEOUT_A = 300.0
TIMEOUT_B = 60.0
INSTANCES = (1, 3, 5)


def _run_unconstrained(
    optic: OpticImpl, dom: Path, prob: Path, anytime: bool, timeout: float
):
    up = PDDLReader().parse_problem(str(dom), str(prob))
    found, t, cost, plan, _ = bv2._solve_files_timed(
        optic, str(dom), str(prob), up, anytime, timeout
    )
    return up, found, t, cost, plan


def _run_constrained(
    optic: OpticImpl,
    dom_text: str,
    prob_text: str,
    up,
    constraint,
    anytime: bool,
    timeout: float,
):
    new_d, new_p = constraint.apply_to_pddl(dom_text, prob_text, up)
    return bv2._solve_text_timed(optic, new_d, new_p, up, anytime, timeout)


def main() -> None:
    optic = OpticImpl()
    rows: list[dict] = []
    dom = Path("pddl/benchmarks/zenotravel/domain.pddl")

    for inst in INSTANCES:
        prob = Path(f"pddl/benchmarks/zenotravel/instances/instance-{inst}.pddl")
        dom_text = dom.read_text()
        prob_text = prob.read_text()

        for set_label, anytime, timeout in [("A", False, TIMEOUT_A), ("B", True, TIMEOUT_B)]:
            print(f"\n=== ZenoTravel inst-{inst} unconstrained Set {set_label} ===")
            up, found, t_base, cost_base, plan = _run_unconstrained(
                optic, dom, prob, anytime, timeout
            )
            rows.append({
                "bench_set": set_label, "domain": "ZenoTravel",
                "problem": f"instance-{inst}", "constraint_type": "unconstrained",
                "plan_found": "yes" if found else "no",
                "time_s": round(t_base, 3), "cost": cost_base,
                "time_delta_s": 0.0, "cost_delta": 0.0, "notes": "",
            })
            if not found or plan is None:
                print("baseline failed; skipping constraints")
                continue

            factory = bv2._CONSTRAINT_FACTORIES["ZenoTravel"]
            all_c = factory(plan, up, dom_text, prob_text)

            for ct in bv2.CONSTRAINT_TYPES:
                c = all_c.get(ct)
                print(f"\n  --- {ct} ---")
                if c is None:
                    rows.append({
                        "bench_set": set_label, "domain": "ZenoTravel",
                        "problem": f"instance-{inst}", "constraint_type": ct,
                        "plan_found": "no", "time_s": 0.0, "cost": None,
                        "time_delta_s": None, "cost_delta": None,
                        "notes": "N/A: not applicable for ZenoTravel",
                    })
                    print("    N/A")
                    continue
                try:
                    found_c, t_c, cost_c, _, eng = _run_constrained(
                        optic, dom_text, prob_text, up, c, anytime, timeout
                    )
                except Exception as exc:
                    rows.append({
                        "bench_set": set_label, "domain": "ZenoTravel",
                        "problem": f"instance-{inst}", "constraint_type": ct,
                        "plan_found": "no", "time_s": 0.0, "cost": None,
                        "time_delta_s": None, "cost_delta": None,
                        "notes": f"Error: {exc}",
                    })
                    print(f"    Error: {exc}")
                    continue
                t_delta = round(t_c - t_base, 3) if found_c else None
                cost_delta = (
                    round(cost_c - cost_base, 2)
                    if (found_c and cost_c is not None and cost_base is not None)
                    else None
                )
                notes = "" if found_c else bv2._classify_failure(eng, t_c, timeout)
                rows.append({
                    "bench_set": set_label, "domain": "ZenoTravel",
                    "problem": f"instance-{inst}", "constraint_type": ct,
                    "plan_found": "yes" if found_c else "no",
                    "time_s": round(t_c, 3), "cost": cost_c,
                    "time_delta_s": t_delta, "cost_delta": cost_delta,
                    "notes": notes,
                })
                print(f"    found={found_c} t={t_c:.3f}s cost={cost_c} "
                      f"Δt={t_delta} Δcost={cost_delta}")

    out = Path("results/benchmark_results_zeno.csv")
    with out.open("w", newline="") as f:
        fields = ["bench_set", "domain", "problem", "constraint_type",
                  "plan_found", "time_s", "cost", "time_delta_s",
                  "cost_delta", "notes"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\nWrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
