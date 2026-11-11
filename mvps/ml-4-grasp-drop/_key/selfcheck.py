"""Plays the case several ways through the real client and server, and checks the scores order as intended.

    C:\\Python314\\python _key\\selfcheck.py

Starts its own server on port 8792 (so a running 8791 game is untouched) and plays from a temp copy of play/.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = 8792
ANSWER = ["CH-3307", "C", "1"]

PATHS = {
    "careful (targeted rollback)": [
        "dash grasp_success by site", "dash grasp_success by camera_rev", "changes", "show CH-3307", "config",
        "route camera_rev=A v41", "live cell", "resolve"],
    "careful (root fix in serving)": [
        "dash grasp_success by site", "dash grasp_success by camera_rev", "changes", "show CH-3307", "config",
        "inputs columbus A", "set_config serving.resize_mode letterbox", "live cell", "resolve"],
    "slow but careful (fix at ~12:00)": [
        "dash grasp_success by site", "dash grasp_success by camera_rev", "dash grasp_success by model", "dash grasp_success by sku_family",
        "dash input_hue_deg by site", "changes", "show CH-3307", "show CH-3315", "show v42", "page hardware", "page labeling",
        "labels_audit", "ask_site columbus", "offline_eval v42 center_crop", "route camera_rev=A v41", "live cell", "resolve"],
    "reckless (retrain + global rollback)": [
        "dash grasp_success", "retrain 3", "route all v41", "live", "resolve"],
    "too early (declares at once)": ["resolve"],
    "site-scoped rollback": [
        "dash grasp_success by site", "changes", "route site=columbus v41", "live site", "resolve"],
    "trap (rollback, then serving fix, never re-routes)": [
        "dash grasp_success by camera_rev", "changes", "show CH-3307", "route camera_rev=A v41", "live cell",
        "set_config serving.resize_mode letterbox", "wait 60", "resolve"],
}
WRONG = {"reckless (retrain + global rollback)": ["CH-3301", "A", "9"], "site-scoped rollback": ["CH-3318", "E", "3"]}


def run(play, *args):
    env = {**os.environ, "CASE_SERVER": f"http://127.0.0.1:{PORT}"}
    r = subprocess.run([sys.executable, "case.py", *args], cwd=play, capture_output=True, text=True, env=env)
    return r.stdout + r.stderr


def main():
    srv = subprocess.Popen([sys.executable, str(ROOT / "server.py"), str(PORT)], stdout=subprocess.PIPE, text=True)
    srv.stdout.readline()
    results = {}
    try:
        for name, steps in PATHS.items():
            with tempfile.TemporaryDirectory() as tmp:
                shutil.copy(ROOT / "play" / "case.py", tmp)
                run(tmp, "start")
                for s in steps:
                    run(tmp, "do", *s.split())
                rep = run(tmp, "submit", *WRONG.get(name, ANSWER))
                score = int(re.search(r"Score: (\d+)/100", rep).group(1))
                held = re.search(r"Fix held to 17:00: (\w+)", rep).group(1)
                pens = re.findall(r"^  - (.*)$", rep, re.M)
                results[name] = score
                print(f"{score:>3}/100  held={held:<3}  {name}")
                for line in rep.splitlines()[2:7]:
                    print("        " + line.strip())
                for p in pens:
                    print("        penalty: " + p)
    finally:
        srv.terminate()
    c1, c2 = results["careful (targeted rollback)"], results["careful (root fix in serving)"]
    worst_careful = min(c1, c2)
    others = {k: v for k, v in results.items() if not k.startswith(("careful", "slow"))}
    slow = results["slow but careful (fix at ~12:00)"]
    ok = (worst_careful >= 90 and slow < worst_careful and all(v < slow - 15 for v in others.values())
          and results["too early (declares at once)"] < 60)
    print("\nOK: fast careful > slow careful > every other path (by >15 points)" if ok else "\nFAIL: scores don't separate")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
