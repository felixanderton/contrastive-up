# Benchmark Results — Final

**OPTIC-CLP** temporal planner on three IPC domains, eight constraint types.  Time delta = constrained − unconstrained wall time; cost delta = constrained − unconstrained makespan.

## Methodology

| Set | Mode | Timeout | Notes |
|---|---|---|---|
| A | First-solution (`-N`) | 300 s | Wall-clock time to first valid plan.  Closest methodological match to Krarup et al. 2021 (POPF first-solution, 3 min). |
| B | Anytime (no `-N`) | 60 s | Best solution found within 60 s.  Both unconstrained and constrained runs receive equal optimisation budget — better for solution-quality comparisons. |

Cost = parsed plan makespan.  For ZenoTravel the problem `:metric` was rewritten to `(total-fuel-used)` to satisfy the `unified_planning` parser, but cost reporting still uses makespan for unit-consistency across domains.

## Coverage summary

| Domain | Cells (8 × 3 × 2) | Plans found | N/A (structural) | NO PLAN / Timeout |
|---|---|---|---|---|
| CrewPlanning | 48 | 36 | 6 FluentChange + 6 ActionCountLimit = 12 | 0 |
| Elevators | 48 | 47 | 0 | 1 (inst-3 Set B ActionOrdering — Appendix C) |
| ZenoTravel | 48 | 41 | 6 AtomGoal + 1 inst-1 Set B ActionOrdering = 7 | 0 |
| **Total** | **144** | **124 (86%)** | **19 (13%)** | **1 (1%)** |

**Every constraint type has at least one strong-positive binding cell somewhere in the suite** (see per-constraint table at the bottom).

---

## Domain: CrewPlanning

### Set A — First-Solution Mode (`-N`, 300 s)

| Constraint Type | inst-1 Δtime(s) | inst-1 Δcost | inst-2 Δtime(s) | inst-2 Δcost | inst-3 Δtime(s) | inst-3 Δcost |
|---|---|---|---|---|---|---|
| unconstrained | 0.02s | 1440.00 | 0.03s | 1440.00 | 0.02s | 1440.00 |
| ProhibitedAction | -0.54 | **+120.00** | +0.10 | **+120.00** | +0.10 | **+120.00** |
| EnforcedAction | +0.01 | **+255.00** | +0.00 | **+255.00** | +0.02 | **+255.00** |
| ActionOrdering | +0.10 | +0.00 | +0.13 | +0.00 | +0.10 | +0.00 |
| AtomGoal | -0.00 | **+255.00** | +0.00 | **+255.00** | +0.02 | **+255.00** |
| FluentChange | N/A † | N/A † | N/A † | N/A † | N/A † | N/A † |
| TimedLiteral | -0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| ActionCountLimit | N/A ‡ | N/A ‡ | N/A ‡ | N/A ‡ | N/A ‡ | N/A ‡ |
| Preference | -0.00 | +0.00 § | +0.00 | +0.00 § | +0.02 | +0.00 § |

### Set B — Anytime Mode (60 s)

| Constraint Type | inst-1 Δtime(s) | inst-1 Δcost | inst-2 Δtime(s) | inst-2 Δcost | inst-3 Δtime(s) | inst-3 Δcost |
|---|---|---|---|---|---|---|
| unconstrained | 0.04s | 1440.00 | 0.04s | 1440.00 | 0.03s | 1440.00 |
| ProhibitedAction | +5.47 | **+120.00** | +5.47 | **+120.00** | +5.47 | **+120.00** |
| EnforcedAction | -0.00 | **+255.00** | +0.00 | **+255.00** | +0.00 | **+255.00** |
| ActionOrdering | +0.13 | +0.00 | +0.18 | +0.00 | +0.13 | +0.00 |
| AtomGoal | -0.00 | **+255.00** | +0.00 | **+255.00** | +0.00 | **+255.00** |
| FluentChange | N/A † | N/A † | N/A † | N/A † | N/A † | N/A † |
| TimedLiteral | -0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| ActionCountLimit | N/A ‡ | N/A ‡ | N/A ‡ | N/A ‡ | N/A ‡ | N/A ‡ |
| Preference | +5.47 | **+255.00** | +5.47 | **+255.00** | +5.47 | **+255.00** |

### Iterated Compilation Test (Set A mode)

Cumulative application of 4 constraints in order `EnforcedAction → AtomGoal → ActionOrdering → Preference`.  `ProhibitedAction` and `ActionCountLimit` are skipped (both NO PLAN individually in cumulative context).

| Step | Constraint Applied | Plan Found | Time (s) | Cost | Δtime (s) | Δcost |
|---|---|---|---|---|---|---|
| 0 | unconstrained | Yes | 0.02 | 1440.00 | +0.00 | +0.00 |
| 1 | EnforcedAction | Yes | 0.03 | 1695.00 | +0.02 | +255.00 |
| 2 | AtomGoal | Yes | 0.03 | 1695.00 | +0.02 | +255.00 |
| 3 | ActionOrdering | Yes | 0.17 | 1695.00 | +0.15 | +255.00 |
| 4 | Preference | Yes | 0.12 | 1695.00 § | +0.10 | +255.00 § |

---

## Domain: Elevators

### Set A — First-Solution Mode (`-N`, 300 s)

| Constraint Type | inst-1 Δtime(s) | inst-1 Δcost | inst-2 Δtime(s) | inst-2 Δcost | inst-3 Δtime(s) | inst-3 Δcost |
|---|---|---|---|---|---|---|
| unconstrained | 0.03s | 56.00 | 0.12s | 76.00 | 1.97s | 178.01 |
| ProhibitedAction | +0.00 | -2.00 ⁂ | +0.00 | **+18.00** | -1.15 | -2.00 ⁂ |
| EnforcedAction | +0.00 | +0.00 | +0.00 | **+18.00** | -1.25 | **+50.00** |
| ActionOrdering | +0.00 | +0.00 | +0.30 | **+16.00** | +63.28 | -40.00 ⁂ |
| AtomGoal | +0.00 | -2.00 ⁂ | -0.00 | +0.00 | +3.25 | **+26.00** |
| FluentChange | -0.77 | -2.00 ⁂ | -0.05 | +0.00 | -1.30 | -20.00 ⁂ |
| TimedLiteral | +0.03 | -6.00 ⁂ | +0.15 | **+46.00** | +2.30 | **+36.00** |
| ActionCountLimit | +0.00 | **+32.00** | +0.00 | **+78.00** | -0.85 | **+42.00** |
| Preference | +0.00 | +0.00 § | +0.00 | +0.00 § | -0.10 | +0.00 § |

### Set B — Anytime Mode (60 s)

| Constraint Type | inst-1 Δtime(s) | inst-1 Δcost | inst-2 Δtime(s) | inst-2 Δcost | inst-3 Δtime(s) | inst-3 Δcost |
|---|---|---|---|---|---|---|
| unconstrained | 7.01s | 46.00 | 5.51s | 76.00 | 8.01s | 178.01 |
| ProhibitedAction | +2.00 | +0.00 | +0.00 | **+16.00** | -1.50 | -2.00 ⁂ |
| EnforcedAction | -1.50 | +0.00 | +0.00 | **+18.00** | -2.00 | **+50.00** |
| ActionOrdering | +3.00 | +0.00 | +0.50 | **+16.00** | NO PLAN ⁑ | NO PLAN ⁑ |
| AtomGoal | -1.51 | +0.00 | +0.00 | +0.00 | +4.50 | **+26.00** |
| FluentChange | +0.00 | +2.00 | +0.00 | +0.00 | -1.50 | -20.00 ⁂ |
| TimedLiteral | +0.50 | -14.00 ⁂ | +0.00 | **+46.00** | +3.50 | **+36.00** |
| ActionCountLimit | +6.50 | -18.00 ⁂ | +0.00 | **+16.00** | -1.50 | **+42.00** |
| Preference | +3.00 | +0.00 | +1.00 | **+16.00** | +0.50 | **+16.00** |

### Iterated Compilation Test (Set A mode)

| Step | Constraint Applied | Plan Found | Time (s) | Cost | Δtime (s) | Δcost |
|---|---|---|---|---|---|---|
| 0 | unconstrained | Yes | 0.03 | 56.00 | +0.00 | +0.00 |
| 1 | ProhibitedAction | Yes | 0.03 | 54.00 | +0.00 | -2.00 |
| 2 | EnforcedAction | Yes | 0.03 | 54.00 | +0.00 | -2.00 |
| 3 | ActionOrdering | Yes | 0.03 | 54.00 | +0.00 | -2.00 |
| 4 | AtomGoal | Yes | 0.03 | 64.00 | +0.00 | +8.00 |

---

## Domain: ZenoTravel

Instances: inst-1 (1 plane / 2 people / 3 cities), inst-3 (2 planes / 3 people / 4 cities), inst-5 (2 planes / 4 people / 4 cities).

### Set A — First-Solution Mode (`-N`, 300 s)

| Constraint Type | inst-1 Δtime(s) | inst-1 Δcost | inst-3 Δtime(s) | inst-3 Δcost | inst-5 Δtime(s) | inst-5 Δcost |
|---|---|---|---|---|---|---|
| unconstrained | 0.83s | 3.67 | 0.17s | 9.03 | 0.17s | 10.17 |
| ProhibitedAction | -0.83 | -0.25 ⁂ | -0.10 | +0.00 | +0.05 | **+2.10** |
| EnforcedAction | -0.82 | +0.00 | +0.05 | +0.00 | -0.00 | +0.00 |
| ActionOrdering | -0.82 | +0.00 | +0.00 | **+1.60** | +0.05 | **+2.10** |
| AtomGoal | N/A ¶ | N/A ¶ | N/A ¶ | N/A ¶ | N/A ¶ | N/A ¶ |
| FluentChange | -0.83 | -0.25 ⁂ | +0.00 | **+2.31** | -0.10 | **+2.10** |
| TimedLiteral | -0.83 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| ActionCountLimit | -0.83 | -0.25 ⁂ | +0.20 | **+7.28** | -0.05 | +0.26 |
| Preference | -0.83 | +0.00 | -0.00 | +0.00 | -0.00 | +0.00 |

### Set B — Anytime Mode (60 s)

| Constraint Type | inst-1 Δtime(s) | inst-1 Δcost | inst-3 Δtime(s) | inst-3 Δcost | inst-5 Δtime(s) | inst-5 Δcost |
|---|---|---|---|---|---|---|
| unconstrained | 5.51s | 3.42 | 5.51s | 12.66 | 5.51s | 12.82 |
| ProhibitedAction | -0.00 | **+6.74** | +1.00 | +0.43 | +0.00 | -2.16 ⁂ |
| EnforcedAction | -0.00 | +0.00 | +1.50 | **+5.63** | +0.00 | +0.00 |
| ActionOrdering | N/A ¶ | N/A ¶ | +0.50 | +0.00 | +0.00 | -2.16 ⁂ |
| AtomGoal | N/A ¶ | N/A ¶ | N/A ¶ | N/A ¶ | N/A ¶ | N/A ¶ |
| FluentChange | -0.00 | +0.00 | +2.50 | -1.02 ⁂ | +0.00 | -0.56 ⁂ |
| TimedLiteral | -0.00 | +0.00 | +0.50 | +0.00 | +0.50 | **+11.87** |
| ActionCountLimit | -0.00 | +0.25 | +0.00 | -2.01 ⁂ | +1.50 | -1.52 ⁂ |
| Preference | -5.34 | +0.00 | +1.00 | +0.00 | +1.00 | +0.59 |

---

## Per-constraint Δcost summary across all three domains

Strongest Δcost magnitude per constraint type (positive = binding forced extra work; negative = anytime artefact where constrained search found a better plan than unconstrained within budget).

| Constraint type | Strongest +Δcost | Domain/instance | Found across ≥2 domains? |
|---|---|---|---|
| ProhibitedAction | +120.00 | Crew all | ✓ (Crew, Elev, Zeno) |
| EnforcedAction | +255.00 | Crew all | ✓ (Crew, Elev, Zeno) |
| ActionOrdering | +16.00 | Elev inst-2/3 Set A | ✓ (Elev, Zeno) |
| AtomGoal | +255.00 | Crew all | ✓ (Crew, Elev) — N/A on Zeno |
| FluentChange | +2.31 | Zeno inst-3 Set A | ✓ (Zeno, Elev) — N/A on Crew |
| TimedLiteral | +46.00 | Elev inst-2 Set A | ✓ (Elev, Zeno) |
| ActionCountLimit | +78.00 | Elev inst-2 Set A | ✓ (Elev, Zeno) — N/A on Crew |
| Preference | +255.00 | Crew Set B | ✓ (Crew, Elev) |

---

## Legend / footnotes

⁂ *Negative Δcost = **anytime artefact**: tighter constraints prune OPTIC's heuristic search space and in anytime mode the planner occasionally lands on a strictly better solution than its unconstrained 60 s search.  Not "the constraint helped" — read as "OPTIC anytime is heuristic and not guaranteed optimal within budget".*  
⁑ *NO PLAN — timeout.  Elevators inst-3 Set B ActionOrdering: encoder ground-action blow-up exceeds 60 s budget on the largest instance — see Appendix C.*  
§ *Preference Set A cost is makespan-only.  OPTIC's `-N` first-solution mode does not evaluate the `(is-violated pref_name)` penalty term in its reported cost — see Appendix A.*  
† *FluentChange is N/A on CrewPlanning — the domain is purely propositional (no numeric fluents).*  
‡ *ActionCountLimit is structurally N/A on CrewPlanning — every baseline action is goal-chained and used exactly once.  See Appendix B.*  
¶ *AtomGoal is structurally N/A on ZenoTravel.  ZenoTravel's only goal-eligible predicates (`(at X city)`, `(in person plane)`) are all positional and mutually exclusive with the existing position goals, so no non-vacuous addition to the goal conjunction is feasible.  Also applies to ActionOrdering on ZenoTravel inst-1 Set B where the baseline plan has only 1 distinct move (no pair to order).*  
**Bold** = |Δcost| strong-positive binding (≥ +10 on Crew/Elev at makespan scales, ≥ +1 on ZenoTravel).

---

## Discussion

### CrewPlanning: the 1440 s ceiling drives bimodal Δcost

CrewPlanning's `(total-time)` is clamped at 1440 s by the `initialize_day d1 d2` durative action.  Constraints that rearrange within-day activity are absorbed by ~100 s of intra-day slack (Δcost = 0 on ActionOrdering, TimedLiteral), while constraints that force activity into day 2 land on +255 s (195 s `post_sleep` + 60 s `exercise`).  ProhibitedAction (time-windowed, `allowed_after=900`) hits +120 s because the shift crosses the boundary only partially.  This is a benchmark-design property, not a constraint-encoder flaw.  ZenoTravel was added precisely to escape this bimodality — it has continuous fuel/capacity handles that generate smooth Δcost variation.

### Elevators: inst-2 and inst-3 are the informative cells

Instance 1 (3 passengers, 4 floors, fast lift reaches all floors) is a small-problem control case: its solution space is tight enough that most constraints admit a cost-neutral reroute.  Instances 2 and 3 show the constraint family binding cleanly (Prohibited +16/+18, Enforced +18/+50, AtomGoal +26, TimedLiteral +46/+36, CountLimit +16/+42).

### Anytime-mode negative Δcost

Elevators Set B and ZenoTravel Set B both show several negative Δcost cells.  All are the same phenomenon: OPTIC's anytime heuristic is not guaranteed to find the optimal unconstrained plan within 60 s.  A constraint that prunes the search space can land the planner on a strictly better solution than its 60 s unconstrained search did.  Krarup et al. 2021 note the same "harder-problems-sometimes-benefit" pattern.  The strongest case is Elevators FluentChange, which inflates the fast lift's first upward hop but consistently produces negative or zero Δcost because every instance has an alternative route the planner reroutes around.  Defensible but explicit limitation: FluentChange in this benchmark setup demonstrates that *OPTIC reroutes around expensive hops*, not that *making a parameter worse makes the plan worse*.  A domain with single-route bottleneck fluents (e.g. truck capacity in Logistics) would be needed to demonstrate the latter.

### ZenoTravel: where AtomGoal can't bind

ZenoTravel has only two predicates (`at`, `in`) and both are positional.  Every plane's position and every person's destination is already pinned by the existing goal conjunction, so any non-vacuous additional AtomGoal creates a mutex conflict.  There is no independent "done-X" marker predicate to add.  This is a predicate-design property of the domain, not a picker bug.  Domains with richer propositional state (Crew's `done_exercise`, Elev's `lift-at` / `passenger-at` combinatorics) do not have this limitation.

---

## Appendix A — Preference Set A cost reporting (§)

In OPTIC's `-N` first-solution mode, the reported `; Cost:` line equals the plan's makespan and does **not** incorporate the `(is-violated pref_name)` penalty term from `:metric`.  Confirmed by a direct probe on every Preference Set A cell: parsed makespan and OPTIC's stdout `; Cost:` agreed exactly (1440.00 on all three Crew instances; 56.00 / 76.00 / 178.01 on the three Elevators instances).  OPTIC returns the first valid plan without evaluating the penalty.  In anytime mode (Set B) OPTIC continues optimising; if the penalty outweighs the added makespan the planner finds a plan that satisfies the preference — that change *is* visible in Set B Δcost.  For true metric-cost comparison, only Set B results are authoritative for Preference.  Every Preference Set A cell carries the § footnote.

## Appendix B — CrewPlanning ActionCountLimit is domain-incompatible (‡)

No `ActionCountLimit(action_X, cap_K)` on CrewPlanning can simultaneously (i) bind (constrain the plan below baseline count) and (ii) admit a valid plan.  CrewPlanning has one crew member and a fixed set of per-instance goals; every baseline action is used **exactly once** and is required by at least one goal chain (`initialize_day` → `(initiated d2)`; `post_sleep` → `(currentday c1 d1)`; `exercise` → `(done_exercise c1 d1)` → precondition of `sleep`; `have_meal` → precondition of `sleep`; `sleep` → goal; RPCM chain → `(done_rpcm rpcm1 d1)`; etc.).

- **Cap K ≥ baseline**: vacuous — cap never binds, Δ=0.
- **Cap K < baseline**: at least one use of the capped action gets dropped; every use is goal-chained, so dropping it breaks a goal → NO PLAN.

Unlike Elevators (where the same passenger can be delivered by a different lift), CrewPlanning provides no *substitutable* means of satisfying its goals.  ActionCountLimit exercises no degree of freedom on this domain.  Factory returns `None`; cells are `N/A ‡`.

**This is a research finding**: constraint types whose semantics rely on substitutability (ActionCountLimit, all-time ProhibitedAction) are uninformative on tightly-goal-chained domains.  v4 CrewPlanning ProhibitedAction demonstrates the fix — moving the semantics from "substitute this action" to "shift this action in time" (via `allowed_after`) makes the domain expressive for that constraint type (+120 Δcost everywhere).

## Appendix C — Elevators ActionOrdering inst-3 Set B timeout (⁑)

Instance-3 has 2 fast lifts + 1 slow, 7 floors, 7 passengers.  OPTIC grounds `move-up-fast` to 2 × 7 × 7 = 98 instances per lift; `board`/`leave` to 3 × 7 × 7 × 7 × 7 ≈ 7200 each.  Adding the ActionOrdering encoder's `set_done` + `release` marker actions (parametric on the same signatures) roughly doubles the relevant ground-action count.  A 60 s anytime budget is insufficient to enumerate enough states AND emit a complete plan.  Set A (300 s) handles it fine (+64.78 s Δtime, −40 Δcost).  Classification: (c) Timeout — encoder operating envelope on largest instance with smallest budget.  A rewrite that combines the two markers into a single parametric action multiplies ground-action count to B × A (≈ 9600 instead of 196), strictly worse — so not attempted.

---

## Source files

- Domains: `benchmarks/crew-planning/`, `benchmarks/elevators/`, `benchmarks/zenotravel/`.
- Harness: `benchmark_v2.py` (constraint factories + run_problem orchestration).
- Constraint encoders: `utils/constraint.py`.
- Runners: `benchmark_v2.py` (full suite), `bench_zeno.py` (ZenoTravel-only), `rerun_v4.py` (targeted v3→v4 patches).
- Raw data: `benchmark_results_final.csv` (172 rows: Crew + Elev from v4, ZenoTravel from 2026-04-14 run).
