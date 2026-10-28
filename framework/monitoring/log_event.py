import os
import time

from databricks import sql

HOST = os.environ["DATABRICKS_HOST"]
HTTP_PATH = os.environ["DATABRICKS_HTTP_PATH"]
TOKEN = os.environ["DATABRICKS_TOKEN"]

RUN_ID = os.environ.get("RUN_ID", "manual")
STAGE = os.environ.get("STAGE", "unknown")
STATUS = os.environ.get("STATUS", "unknown")
DETAILS = os.environ.get("DETAILS", "")


def _is_deadlock_error(exc: Exception) -> bool:
    return "deadlock found when trying to get lock" in str(exc).lower()


def main():
    # Cada stage deja su registro: con esto se mide duración, MTTR y costo
    for attempt in range(3):
        try:
            with sql.connect(server_hostname=HOST, http_path=HTTP_PATH, access_token=TOKEN) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO gameday.ops_event_log VALUES (?, current_timestamp(), ?, ?, ?)",
                        (RUN_ID, STAGE, STATUS, DETAILS),
                    )
            break
        except Exception as exc:
            if attempt == 2 or not _is_deadlock_error(exc):
                raise
            time.sleep(1 + attempt)
    print(f"✅ Event logged: stage={STAGE} status={STATUS}")


if __name__ == "__main__":
    main()
