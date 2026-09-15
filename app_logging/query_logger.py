import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

LOG_DIR = PROJECT_ROOT / "runtime_logs"
LOG_PATH = LOG_DIR / "queries.jsonl"


def create_request_id():
    return str(uuid.uuid4())


def write_query_log(
    *,
    request_id,
    question=None,
    retrieved_tables=None,
    retrieval_scores=None,
    generated_sql=None,
    validation_status=None,
    validation_errors=None,
    execution_status=None,
    row_count=None,
    retrieval_time=None,
    generation_time=None,
    execution_time=None,
    total_time=None,
):
    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    record = {
        "request_id": request_id,
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "question": question,

        "retrieved_tables":
            retrieved_tables or [],

        "retrieval_scores":
            retrieval_scores or [],

        "generated_sql":
            generated_sql,

        "validation_status":
            validation_status,

        "validation_errors":
            validation_errors or [],

        "execution_status":
            execution_status,

        "row_count":
            row_count,

        "retrieval_time_seconds":
            retrieval_time,

        "generation_time_seconds":
            generation_time,

        "execution_time_seconds":
            execution_time,

        "total_time_seconds":
            total_time,
    }

    with LOG_PATH.open(
        "a",
        encoding="utf-8"
    ) as file:
        file.write(
            json.dumps(
                record,
                ensure_ascii=False
            )
            + "\n"
        )

    return record