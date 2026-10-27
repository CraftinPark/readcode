"""Run a 10-minute shift with the current firmware. Passes if the line never e-stops and the conveyor stays within 5 degrees."""
from _sim import plant
from firmware.drive import Drive

log = plant.run(Drive, seconds=600)
worst = max(abs(x) for x in log["shaft_angle_error_deg"])
if "estop_at" in log:
    print(f"FAIL: e-stop at {log['estop_at']}s")
    raise SystemExit(1)
print(f"{'ok' if worst <= 5 else 'FAIL'}: 600 s, worst position error {worst} deg")
raise SystemExit(0 if worst <= 5 else 1)
