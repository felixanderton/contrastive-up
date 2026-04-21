# contrastive-up

Contrastive plan explanation using the [Unified Planning Framework](https://unified-planning.readthedocs.io/) and [OPTIC](https://nms.kcl.ac.uk/planning/software/optic.html).

Given a planning problem and a constraint question (e.g. *"Why did the driver drive from A to B?"*), the tool generates two plans — an original optimal plan and a constrained plan where the questioned action is prohibited — then produces a side-by-side diff explaining what changes when that action is removed.

---

> ## ⚠️ Platform requirement
>
> **This project must run on an x86_64 Ubuntu/Linux machine with Docker installed.**
>
> The bundled `optic-clp` planner is a **32-bit i386 Linux binary**. It will not execute natively on macOS, Windows, or ARM hardware. Running it requires either:
>
> - an x86_64 Ubuntu host (recommended), or
> - any Linux host with Docker and `linux/amd64` support enabled.
>
> On non-Linux hosts, Docker must emulate `linux/amd64` via QEMU, which produces significantly slower runs and has not been validated for this submission.
>
> ### Validated environment
>
> `./build.sh` was verified end-to-end on a Google Cloud VM with the following spec:
>
> | Field | Value |
> |---|---|
> | Project | `scenic-bolt-469812-m3` |
> | Instance | `planning-vm` |
> | Zone | `us-west1-a` |
> | Machine type | `e2-standard-4` (4 vCPU, 16 GB RAM) |
> | Architecture | `x86_64` |
> | OS | Ubuntu 22.04.5 LTS |
> | Docker | 29.1.3 |

---

## How it works

1. The original problem is solved with OPTIC to produce an optimal plan.
2. The same problem is solved again with a constraint applied (e.g. a specific action instance is prohibited or enforced).
3. The two plans are diffed and printed as a colour-coded table showing which actions were added, removed, or rescheduled.

## Quickstart

```bash
./build.sh                                # build image + run main.py
./build.sh python scripts/run_tests.py    # build image + run any command
```

`build.sh` wraps `docker build` + `docker run` and mounts the source directory so edits are picked up without rebuilding.

## Project structure

```
main.py                # Entry point — configure constraints here
build.sh               # Build + run the Docker container
Dockerfile             # linux/amd64 image with 32-bit runtime libs
docker-compose.yml     # Alternative runner (docker compose up)
requirements.txt       # Python dependencies
optic-clp              # OPTIC binary (linux/amd64 32-bit)

utils/
  optic.py             # Unified Planning engine wrapper for OPTIC
  constraint.py        # All constraint encodings (8 types)
  plan_diff.py         # Side-by-side plan comparison output
  config.py            # Colour map and display config

scripts/
  benchmark.py                     # Benchmark grid across constraint types
  bench_zeno.py                    # ZenoTravel benchmark
  paired_benchmark.py              # ActionOrdering vs Preference, first-solution
  paired_benchmark_anytime.py      # ActionOrdering vs Preference, anytime
  run_tests.py                     # Constraint tests on refrigerated delivery
  run_tests_elevators.py           # Constraint tests on elevators

pddl/
  correctness_tests/   # Demo domain (refrigerated delivery)
  benchmarks/          # IPC benchmark domains + instances
    crew-planning/
    elevators/
    zenotravel/

results/               # All benchmark + test output
  benchmark_results.{csv,md}
  paired_benchmark_results.csv
  paired_benchmark_anytime_results.csv
  test_results.txt
  test_results_elevators.txt

docs/
  architecture_diagram_v3_print.py   # Diagram generator
  architecture_diagram_v3_print.png  # Rendered diagram
```

All scripts can be run from the project root (e.g. `python scripts/benchmark.py`) and will resolve PDDL/output paths relative to the project root automatically.

## Defining constraints

Edit `main.py` to change the domain, problem, and constraints:

```python
contrastive_plan_comparison(
    domain_path='pddl/correctness_tests/refrigerated_delivery_domain.pddl',
    problem_path='pddl/correctness_tests/refrigerated_delivery_problem.pddl',
    constraint_question='Why did the driver use truck t2 to drive from a to c?',
    constraints=[
        ProhibitedAction('drive_truck', ['d1', 't2', 'a', 'c']),
    ],
)
```

Available constraint classes in `utils/constraint.py`: `ProhibitedAction`, `EnforcedAction`, `ActionOrdering`, `AtomGoal`, `FluentChange`, `TimedLiteral`, `ActionCountLimit`, `Preference`.
