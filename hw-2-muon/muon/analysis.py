"""Muon rate through the telescope from one run of the CB-2 board.

The board counts singles on A and B and AB coincidences (A and B output pulses overlapping). Some coincidences
are accidental: two unrelated pulses that happen to overlap. Their rate is rA * rB * (wA + wB).

Paddle B's replacement PMT gives pulses about 45 ns long, and the board stretches B's output to that whatever
width_b says (measured on the telescope: accidentals window 65 ns at widths 20/20, 55 ns at 10/20, 65 ns at 20/10).

Channel B is also dead for about 1.7 us after each pulse, and its PMT is noisy (25-35k pulses/s at 9-15 C, rising
with temperature), so it misses a share of muons that grows with rB. Measured with the Sr-90 source on B: muon rate
at rB 79k/s over rB 29k/s = 0.911 +- 0.021, so tau = 1.7 +- 0.4 us, and nothing else is lost.
"""

B_PULSE_NS = 45
B_DEAD_NS = 1700


def muon_rate(counts, config):
    """counts: {"A", "B", "AB", "seconds", ...} from the board; config: board/config.json. Returns muons/s."""
    t = counts["seconds"]
    ra, rb, rab = counts["A"] / t, counts["B"] / t, counts["AB"] / t
    window = (config["width_a_ns"] + max(config["width_b_ns"], B_PULSE_NS)) * 1e-9
    return (rab - ra * rb * window) / (1 - rb * B_DEAD_NS * 1e-9)
