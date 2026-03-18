"""
Run contrastive plan comparison on Modal (native linux/amd64, no emulation).

Usage:
    pip install modal
    modal setup          # one-time browser auth
    modal run modal_run.py
"""
import os
import modal

app = modal.App("contrastive-up")

image = (
    modal.Image.debian_slim(python_version="3.11")
    # 32-bit libs in case the OPTIC binary needs them
    .apt_install("libc6-i386", "lib32stdc++6")
    .pip_install(
        "unified-planning==1.2.0",
        "tarski==0.8.2",
        "antlr4-python3-runtime==4.7.2",
        "pyparsing==3.2.5",
        "networkx==3.6",
        "multipledispatch==1.0.0",
    )
)

# Mount all project files (exclude venv and cache)
project_mount = modal.Mount.from_local_dir(
    ".",
    remote_path="/app",
    condition=lambda p: (
        ".venv" not in p
        and "__pycache__" not in p
        and not p.endswith(".pyc")
        and "optic-clp-release" not in p
    ),
)


@app.function(image=image, mounts=[project_mount], timeout=300)
def run_contrastive(
    domain_path: str = "refrigerated_delivery_domain.pddl",
    problem_path: str = "refrigerated_delivery_problem.pddl",
    constraint_question: str = "Why did the driver drive from location a to location b?",
    prohibited: list[tuple[str, list[str]]] = [("drive_truck", ["d1", "t1", "a", "b"])],
    enforced: list[tuple[str, list[str]]] = [],
):
    import sys

    os.chdir("/app")
    os.chmod("/app/optic-clp", 0o755)
    sys.path.insert(0, "/app")

    from main import contrastive_plan_comparison
    from utils.constraint import ProhibitedAction, EnforcedAction

    contrastive_plan_comparison(
        domain_path=f"/app/{domain_path}",
        problem_path=f"/app/{problem_path}",
        constraint_question=constraint_question,
        prohibited_actions=[ProhibitedAction(name, objs) for name, objs in prohibited],
        enforced_actions=[EnforcedAction(name, objs) for name, objs in enforced],
    )


@app.local_entrypoint()
def main():
    run_contrastive.remote()
