from unified_planning.plans import SequentialPlan, TimeTriggeredPlan
from utils import config


def _format_cost(value):
    if value is None:
        return "N/A"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.2f}"
    return str(value)


def _plan_cost(plan):
    if isinstance(plan, TimeTriggeredPlan):
        if not plan.timed_actions:
            return 0.0
        # Cost for time-triggered plans is the makespan (max end time).
        return max(start + duration for start, _, duration in plan.timed_actions)
    if isinstance(plan, SequentialPlan):
        return len(plan.actions)
    return None

def plan_signature_list(plan):
    sigs = []

    action_list = []
    if isinstance(plan, SequentialPlan):
        action_list = plan.actions
    elif isinstance(plan, TimeTriggeredPlan):
        # For a TimeTriggeredPlan, actions are in timed_actions as (start, action, duration)
        action_list = [item[1] for item in plan.timed_actions]

    for ai in action_list:
        name = ai.action.name
        args = []
        for obj in ai.actual_parameters:
            if hasattr(obj, "name"):
                args.append(obj.name)
            elif obj.is_object_exp():
                args.append(obj.object().name)
            else:
                args.append(str(obj))
        sigs.append((name, tuple(args)))
    return sigs


def format_action(sig):
    name, args = sig
    if args:
        return f"{name}({', '.join(args)})"
    return name


def colorize(text, status):
    if not text:
        return text
    color = config.COLOR_MAP.get(status)
    if not color:
        return text
    return f"{color}{text}{config.COLOR_RESET}"


def diff_plans(plan_a, plan_b):
    cost_a = _format_cost(_plan_cost(plan_a))
    cost_b = _format_cost(_plan_cost(plan_b))

    sigs_a = plan_signature_list(plan_a)
    sigs_b = plan_signature_list(plan_b)
    positions_a = {}
    positions_b = {}
    for idx, sig in enumerate(sigs_a):
        positions_a.setdefault(sig, []).append(idx)
    for idx, sig in enumerate(sigs_b):
        positions_b.setdefault(sig, []).append(idx)
    paired_a_to_b = {}
    paired_b_to_a = {}
    for sig, idxs_a in positions_a.items():
        idxs_b = positions_b.get(sig, [])
        for ai, bi in zip(idxs_a, idxs_b):
            paired_a_to_b[ai] = bi
            paired_b_to_a[bi] = ai

    status_a = []
    for idx in range(len(sigs_a)):
        if idx in paired_a_to_b:
            if paired_a_to_b[idx] == idx:
                status_a.append("same")
            else:
                status_a.append("rescheduled")
        else:
            status_a.append("removed")

    status_b = []
    for idx in range(len(sigs_b)):
        if idx in paired_b_to_a:
            if paired_b_to_a[idx] == idx:
                status_b.append("same")
            else:
                status_b.append("rescheduled")
        else:
            status_b.append("added")

    formatted_a = [format_action(sig) for sig in sigs_a]
    formatted_b = [format_action(sig) for sig in sigs_b]
    col_width = max(
        max((len(text) for text in formatted_a), default=0),
        max((len(text) for text in formatted_b), default=0),
        20
    )
    header = (
        f"{'Step':>4} | "
        f"{'Original Plan':<{col_width}} | "
        f"{'Constrained Plan':<{col_width}}"
    )
    print("\nPlan comparison:")
    print(header)
    cost_header = f"{'Cost':>4} | {cost_a:<{col_width}} | {cost_b:<{col_width}}"
    print(cost_header)
    print("-" * len(header))

    row_count = max(len(sigs_a), len(sigs_b))
    for idx in range(row_count):
        if idx < len(sigs_a):
            left = colorize(formatted_a[idx].ljust(col_width), status_a[idx])
        else:
            left = " " * col_width

        if idx < len(sigs_b):
            right = colorize(formatted_b[idx].ljust(col_width), status_b[idx])
        else:
            right = " " * col_width

        print(f"{idx:>4} | {left} | {right}")

    print("\nLegend:")
    print(colorize("  Blue       : matching action in both plans", "same"))
    print(colorize("  Yellow     : action added relative to the other plan", "added"))
    print(colorize("  Red        : action removed relative to the other plan", "removed"))
    print(colorize("  Green      : action exists in both plans but moved", "rescheduled"))
