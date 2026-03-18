# contrastive-up

Contrastive plan explanation using the [Unified Planning Framework](https://unified-planning.readthedocs.io/) and [OPTIC](https://nms.kcl.ac.uk/planning/software/optic.html).

Given a planning problem and a constraint question (e.g. *"Why did the driver drive from A to B?"*), the tool generates two plans — an original optimal plan and a constrained plan where the questioned action is prohibited — then produces a side-by-side diff explaining what changes when that action is removed.

## How it works

1. The original problem is solved with OPTIC to produce an optimal plan.
2. The same problem is solved again with a constraint applied (e.g. a specific action instance is prohibited or enforced).
3. The two plans are diffed and printed as a colour-coded table showing which actions were added, removed, or rescheduled.

## Running on Windows (recommended)

The included Docker setup targets `linux/amd64` and runs natively on any x86_64 Windows PC — no emulation overhead.

**Prerequisites:** [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) (uses WSL2 backend by default)

```bash
git clone https://github.com/felixanderton/contrastive-up.git
cd contrastive-up
docker compose up --build
```

## Running on macOS (Apple Silicon)

Docker emulates `linux/amd64` via QEMU on Apple Silicon, which causes significant slowdowns for the OPTIC binary. Before running, enable Rosetta emulation in Docker Desktop:

**Docker Desktop → Settings → General → "Use Rosetta for x86/amd64 emulation on Apple Silicon"**

Then:

```bash
docker compose up --build
```

## Project structure

```
main.py                          # Entry point — configure constraints here
utils/
  optic.py                       # Unified Planning engine wrapper for OPTIC
  constraint.py                  # ProhibitedAction and EnforcedAction helpers
  plan_diff.py                   # Side-by-side plan comparison and diff output
  config.py                      # Colour map and display config
*.pddl                           # Domain and problem files
optic-clp                        # OPTIC binary (linux/amd64 32-bit)
```

## Defining constraints

Edit `main.py` to change the domain, problem, and constraints:

```python
prohibited_actions = [
    ProhibitedAction('drive_truck', ['d1', 't1', 'a', 'b']),
]

contrastive_plan_comparison(
    domain_path='refrigerated_delivery_domain.pddl',
    problem_path='refrigerated_delivery_problem.pddl',
    constraint_question='Why did the driver drive from location a to location b?',
    prohibited_actions=prohibited_actions,
)
```

`ProhibitedAction(action_name, [param_objects])` prevents a specific action instance from being used in the constrained plan. `EnforcedAction` forces an action instance to appear.
