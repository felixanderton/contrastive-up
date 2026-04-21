"""
Test cases for all constraint classes using the IPC elevators-time domain.

Domain recap:
  Objects : fast0 (fast-elevator, cap 2, starts n0), slow0-0 (slow-elevator, cap 1, starts n3)
            p0, p1, p2 (passengers), n0..n3 (floors)
  Passengers: p0 n0->n3, p1 n3->n0, p2 n1->n2
  travel-fast: 6/10/14; travel-slow: 10/18/26
  Goal: p0@n3, p1@n0, p2@n2.  Minimise total-time.
  Likely optimal (parallel): slow takes p1 n3->n0 (~28s);
    fast sweeps n0->n1->n2->n3 doing p0+p2 (~22s).  Makespan ~28.
"""

import sys
import os
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO

DOMAIN = 'pddl/benchmarks/elevators/domain.pddl'
PROBLEM = 'pddl/benchmarks/elevators/instances/instance-1.pddl'

os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import contrastive_plan_comparison
from utils.constraint import (
    ProhibitedAction, EnforcedAction,
    ActionOrdering, AtomGoal, FluentChange, TimedLiteral, ActionCountLimit,
    Preference,
)

RESULTS_FILE = 'results/test_results_elevators.txt'

TEST_CASES = [
    # 1. ProhibitedAction — ban the direct n0->n3 fast hop that the baseline uses
    dict(
        name='ProhibitedAction: ban move-up-fast(fast0, n0, n3)',
        question='Why did fast0 go directly from n0 to n3?',
        constraints=[
            ProhibitedAction('move-up-fast', ['fast0', 'n0', 'n3']),
        ],
    ),

    # 2. EnforcedAction — force p0 onto the slow lift (slow must descend from n3 first)
    dict(
        name='EnforcedAction: enforce board(p0, slow0-0, n0, n0, n1)',
        question='What if p0 had to ride the slow elevator?',
        constraints=[
            EnforcedAction('board', ['p0', 'slow0-0', 'n0', 'n0', 'n1']),
        ],
    ),

    # 3. ActionOrdering — reverse baseline: leave p1 BEFORE leave p0
    #    Baseline drops p0 at t=15, p1 at t=45 — this forces the opposite.
    dict(
        name='ActionOrdering: leave(p0,fast0,n3) after leave(p1,fast0,n0)',
        question='Why was p0 delivered before p1?',
        constraints=[
            ActionOrdering(
                before_name='leave', before_params=['p1', 'fast0', 'n0', 'n1', 'n0'],
                after_name='leave',  after_params=['p0', 'fast0', 'n3', 'n1', 'n0'],
            ),
        ],
    ),

    # 4. AtomGoal — slow0-0 must end at n3 (baseline ends it at n1)
    dict(
        name='AtomGoal: slow0-0 must end at n3',
        question='What if the slow elevator had to return to floor 3?',
        constraints=[
            AtomGoal('lift-at', ['slow0-0', 'n3']),
        ],
    ),

    # 5. FluentChange — slow the n0<->n2 fast leg (10 -> 30).
    #    Baseline uses move-down-fast(fast0, n2, n0) (duration = travel-fast(n0,n2)).
    dict(
        name='FluentChange: travel-fast(n0,n2) 10 -> 30',
        question='What if the fast trip between n0 and n2 took 30 time units?',
        constraints=[
            FluentChange('travel-fast', ['n0', 'n2'], 30),
            FluentChange('travel-fast', ['n2', 'n0'], 30),
        ],
    ),

    # 6. TimedLiteral — fast0 loses access to n3 from t=0.001 (entire run).
    #    Forces p0 (n0 -> n3) to be carried by slow0-0.
    dict(
        name='TimedLiteral: fast0 cannot reach n3 (from t=0.001)',
        question='What if the fast elevator could never reach floor 3?',
        constraints=[
            TimedLiteral(0.001, 'reachable-floor', ['fast0', 'n3'], holds=False),
        ],
    ),

    # 7. ActionCountLimit — ban upward fast-elevator moves entirely.
    #    Forces all passenger ascents onto the slow (capacity-1) elevator,
    #    which must shuttle p0 (n0->n3) and p2 (n1->n2) separately.
    #    Problem remains solvable but cost rises well above baseline.
    dict(
        name='ActionCountLimit: move-up-fast limited to 0 uses',
        question='What if the fast elevator could never ascend?',
        constraints=[
            ActionCountLimit('move-up-fast', 0),
        ],
    ),

    # 8. Preference — sometime-before: when boarded(p0,fast0) holds,
    #    boarded(p2,fast0) must have held earlier.
    #    Baseline boards p0 at t=1 (before p2 at t=28) — so this VIOLATES.
    #    Both antecedent and consequent are reached in the baseline.
    dict(
        name='Preference: sometime-before — p2 boarded before p0 (penalty 100)',
        question='Why was p0 boarded before p2?',
        constraints=[
            Preference(
                name='pref_p2_before_p0',
                formula_type='sometime-before',
                args=[['boarded', 'p0', 'fast0'], ['boarded', 'p2', 'fast0']],
                penalty=100,
            ),
        ],
    ),
]


def run_all():
    output_lines = []

    def log(text=''):
        print(text)
        output_lines.append(text)

    log('=' * 70)
    log('CONTRASTIVE PLANNING — ELEVATORS CONSTRAINT TEST RESULTS')
    log('=' * 70)

    for i, tc in enumerate(TEST_CASES, 1):
        header = f"\n[Test {i}/{ len(TEST_CASES) }] {tc['name']}"
        log(header)
        log('-' * len(header.strip()))

        buf = StringIO()
        try:
            with redirect_stdout(buf):
                contrastive_plan_comparison(
                    domain_path=DOMAIN,
                    problem_path=PROBLEM,
                    constraint_question=tc['question'],
                    constraints=tc['constraints'],
                )
        except Exception as e:
            buf.write(f'\nERROR: {e}\n')

        captured = buf.getvalue()
        for line in captured.splitlines():
            print(line)
            output_lines.append(line)

    log('\n' + '=' * 70)
    log('ALL TESTS COMPLETE')
    log('=' * 70)

    Path(RESULTS_FILE).write_text('\n'.join(output_lines) + '\n')
    print(f'\nResults saved to {RESULTS_FILE}')


if __name__ == '__main__':
    run_all()
