"""What the queue does with a user's job: compile, execute, mitigate readout. Returns {bitstring: probability}."""
from qc import backend
from qc.compile import compile
from qc.mitigate import mitigate


def run(circuit, shots=4000):
    counts = backend.execute(compile(circuit), shots)
    return mitigate({k: v / shots for k, v in counts.items()})
