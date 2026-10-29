"""Reference. Measured on the telescope: B's discriminator always puts out 45 ns (width_b is ignored), so the
accidental window is width_a + 45 ns; both discriminators hold off 1.5 us after a pulse, so a muon is lost when
either channel is in hold-off (live fraction 1 - r*1.5us per channel, r = counted singles). board/config.json
delays A by 20 ns to line up with B (cable + new PMT)."""
B_WIDTH_NS = 45
HOLD_OFF_S = 1.5e-6


def muon_rate(counts, config):
    t = counts["seconds"]
    ra, rb, rab = counts["A"] / t, counts["B"] / t, counts["AB"] / t
    window = (config["width_a_ns"] + B_WIDTH_NS) * 1e-9
    live = (1 - ra * HOLD_OFF_S) * (1 - rb * HOLD_OFF_S)
    return (rab - ra * rb * window) / live
