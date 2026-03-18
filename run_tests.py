"""
Test cases for all constraint classes using the refrigerated delivery domain.

Domain recap:
  Objects : t1, t2 (trucks), d1 (driver), m (meat), ce (cereal), a/b/c (locations)
  t2 is refrigerated.  Distances: a-b=20, b-c=15, a-c=10
  TIL: can_deliver(m) expires at t=22 (meat must be kept cool or extended)
  Goal: meat at b, cereal at c.
  Optimal plan: t2 goes a→c(10) deliver ce, c→b(15) extend_meat_life deliver m. Cost=25.032
"""

import sys
import os
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO

DOMAIN = 'refrigerated_delivery_domain.pddl'
PROBLEM = 'refrigerated_delivery_problem.pddl'

os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

from main import contrastive_plan_comparison
from utils.constraint import (
    ProhibitedAction, EnforcedAction,
    ActionOrdering, AtomGoal, FluentChange, TimedLiteral, ActionCountLimit,
)

RESULTS_FILE = 'test_results.txt'

TEST_CASES = [
    # -------------------------------------------------------------------------
    # 1. ProhibitedAction — ban the key drive that makes the optimal route work
    # -------------------------------------------------------------------------
    dict(
        name='ProhibitedAction: ban drive_truck(d1, t2, a, c)',
        question='Why did the driver take truck t2 directly from a to c?',
        constraints=[
            ProhibitedAction('drive_truck', ['d1', 't2', 'a', 'c']),
        ],
    ),

    # -------------------------------------------------------------------------
    # 2. EnforcedAction — force the driver onto the slower truck/route
    # -------------------------------------------------------------------------
    dict(
        name='EnforcedAction: enforce board_truck(d1, t1, a)',
        question='What if the driver had to use truck t1 (non-refrigerated)?',
        constraints=[
            EnforcedAction('board_truck', ['d1', 't1', 'a']),
        ],
    ),

    # -------------------------------------------------------------------------
    # 3. ActionOrdering — force extend_meat_life to happen AFTER delivery,
    #    meaning the extension can no longer enable a late delivery.
    #    The planner must instead deliver meat before t=22 without the extension.
    # -------------------------------------------------------------------------
    dict(
        name='ActionOrdering: extend_meat_life only after deliver_produce(m, t2, b)',
        question='Why did the driver extend meat life before delivering it?',
        constraints=[
            ActionOrdering(
                before_name='deliver_produce', before_params=['m', 't2', 'b'],
                after_name='extend_meat_life', after_params=['m', 't2'],
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # 4. AtomGoal — add requirement that t2 must end up back at c after delivery
    # -------------------------------------------------------------------------
    dict(
        name='AtomGoal: truck t2 must also end at location c',
        question='What if truck t2 also needed to return to location c?',
        constraints=[
            AtomGoal('at', ['t2', 'c']),
        ],
    ),

    # -------------------------------------------------------------------------
    # 5. FluentChange — make the a→b road much shorter (5 vs 20)
    #    This should make the t1 direct route (a→b(5)+b→c(15)=20) competitive
    #    with the t2 route (a→c(10)+c→b(15)=25) and change the optimal plan
    # -------------------------------------------------------------------------
    dict(
        name='FluentChange: time_to_drive(a, b) changed from 20 to 5',
        question='What if the road from a to b only took 5 time units?',
        constraints=[
            FluentChange('time_to_drive', ['a', 'b'], 5),
            FluentChange('time_to_drive', ['b', 'a'], 5),
        ],
    ),

    # -------------------------------------------------------------------------
    # 6. TimedLiteral — re-enable can_deliver(m) at t=23, just after the TIL
    #    that removes it at t=22.  Gives the planner a second delivery window,
    #    potentially removing the need for extend_meat_life.
    # -------------------------------------------------------------------------
    dict(
        name='TimedLiteral: can_deliver(m) re-enabled at t=23',
        question='What if meat could be delivered again after a brief cooling period at t=23?',
        constraints=[
            TimedLiteral(23, 'can_deliver', ['m'], holds=True),
        ],
    ),

    # -------------------------------------------------------------------------
    # 7. ActionCountLimit — limit drive_truck to 2 uses (exactly the minimum
    #    needed by the optimal plan). Confirms the constraint is non-restrictive
    #    when the limit equals what the optimal plan already uses.
    # -------------------------------------------------------------------------
    dict(
        name='ActionCountLimit: drive_truck limited to 2 uses',
        question='What if the truck could only be driven at most 2 times?',
        constraints=[
            ActionCountLimit('drive_truck', 2),
        ],
    ),
]


def run_all():
    output_lines = []

    def log(text=''):
        print(text)
        output_lines.append(text)

    log('=' * 70)
    log('CONTRASTIVE PLANNING — CONSTRAINT TEST RESULTS')
    log('=' * 70)

    for i, tc in enumerate(TEST_CASES, 1):
        header = f"\n[Test {i}/{ len(TEST_CASES) }] {tc['name']}"
        log(header)
        log('-' * len(header.strip()))

        # Capture the contrastive_plan_comparison output
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
        # Print and collect
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
