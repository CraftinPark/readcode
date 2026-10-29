"""The QPU queue. Every shot is charged to this attempt's budget: 400,000 shots."""
import os

from _sim import qpu

BUDGET = 400_000
USED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".shots_used")
FREE = False   # the acceptance check runs in the vendor's slot and is not charged


def execute(program, shots):
    """Runs a native program (see qc/compile.py). Returns {bitstring: count}, character k = qubit k."""
    if not FREE:
        used = shots_used()
        if used + shots > BUDGET:
            raise SystemExit(f"shot budget spent: {used} of {BUDGET} used")
        open(USED, "w").write(str(used + shots))
    return qpu.run(program, shots)


def shots_used():
    return int(open(USED).read()) if os.path.exists(USED) else 0
