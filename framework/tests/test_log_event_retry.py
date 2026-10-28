import importlib
import os
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("DATABRICKS_HOST", "host")
os.environ.setdefault("DATABRICKS_HTTP_PATH", "path")
os.environ.setdefault("DATABRICKS_TOKEN", "token")

databricks_module = types.ModuleType("databricks")
databricks_module.sql = types.SimpleNamespace()
sys.modules.setdefault("databricks", databricks_module)

log_event = importlib.import_module("framework.monitoring.log_event")


class _FakeCursor:
    def __init__(self, state):
        self.state = state

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, *_args, **_kwargs):
        self.state["calls"] += 1
        if self.state["calls"] < 3:
            raise Exception("Deadlock found when trying to get lock; try restarting transaction")


class _FakeConn:
    def __init__(self, state):
        self.state = state

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return _FakeCursor(self.state)


def main():
    state = {"calls": 0}
    sleeps = []

    original_connect = getattr(log_event.sql, "connect", None)
    original_sleep = log_event.time.sleep

    try:
        log_event.sql.connect = lambda **_kwargs: _FakeConn(state)
        log_event.time.sleep = lambda seconds: sleeps.append(seconds)
        log_event.main()
    finally:
        if original_connect is None:
            delattr(log_event.sql, "connect")
        else:
            log_event.sql.connect = original_connect
        log_event.time.sleep = original_sleep

    assert state["calls"] == 3, f"expected 3 execute attempts, got {state['calls']}"
    assert sleeps == [1, 2], f"expected backoff [1, 2], got {sleeps}"
    print("✅ log_event retries deadlocks and succeeds")


if __name__ == "__main__":
    main()
