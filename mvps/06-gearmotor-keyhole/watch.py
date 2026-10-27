"""The 'video': what the line camera saw on the last long job. Free to watch as often as you like.

    python watch.py
"""
from _sim import plant
from firmware.drive import Drive

log = plant.run(Drive)
W = 50
print("conveyor, line 3 (one frame per second; # = carrier, | = where it should be)\n")
for i in range(0, len(log["t"]), 100):
    err = log["shaft_angle_error_deg"][i]
    should = 10
    pos = max(0, min(W - 1, should + int(err / 3)))
    row = [" "] * W
    row[should] = "|"
    row[pos] = "#"
    print(f"{log['t'][i]:5.1f}s  {''.join(row)}")
if "estop_at" in log:
    err = log["shaft_angle_error_deg"][-1]
    row = [" "] * W
    row[10] = "|"
    row[max(0, min(W - 1, 10 + int(err / 3)))] = "#"
    print(f"{log['t'][-1]:5.1f}s  {''.join(row)}")
    print(f"{log['estop_at']:5.1f}s  E-STOP: the PLC stopped the line (conveyor ran away)")
