"""Run the playground API locally: cd backend && python -m playground [--port 8000]"""
import argparse

import uvicorn

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--port", type=int, default=8000)
a = ap.parse_args()
uvicorn.run("playground:app", host="127.0.0.1", port=a.port)
