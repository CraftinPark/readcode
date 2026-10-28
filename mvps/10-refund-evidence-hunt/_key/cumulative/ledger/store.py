"""The webhook store: one JSON line per delivery we accepted, plus the gateway's access log."""
import json
import os


class Store:
    def __init__(self, root):
        os.makedirs(root, exist_ok=True)
        self.events_path = os.path.join(root, "events.jsonl")
        self.gateway_path = os.path.join(root, "gateway.log")

    def append(self, record):
        with open(self.events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def records(self):
        if not os.path.exists(self.events_path):
            return []
        with open(self.events_path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def log_gateway(self, line):
        with open(self.gateway_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
