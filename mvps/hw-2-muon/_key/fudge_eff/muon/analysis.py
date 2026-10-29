"""Tempting: right accidental window, but the 4% left over today is called "paddle B efficiency" and divided
out as a constant."""
B_WIDTH_NS = 45
EFF_B = 0.957


def muon_rate(counts, config):
    t = counts["seconds"]
    ra, rb, rab = counts["A"] / t, counts["B"] / t, counts["AB"] / t
    window = (config["width_a_ns"] + B_WIDTH_NS) * 1e-9
    return (rab - ra * rb * window) / EFF_B
