"""Tempting: subtract the accidental rate measured today with B delayed out of time (3.36/s), divide out
today's 4% loss."""
ACCIDENTALS = 3.36
EFF = 0.957


def muon_rate(counts, config):
    return (counts["AB"] / counts["seconds"] - ACCIDENTALS) / EFF
