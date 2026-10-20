import json
import logging
import sys

from app.logs import JsonFormatter, request_id


def make_record(**extra) -> logging.LogRecord:
    record = logging.LogRecord(
        "app", logging.WARNING, __file__, 1, "Disk %s", ("full",), None
    )
    record.__dict__.update(extra)
    return record


def test_formats_a_record_as_one_json_line():
    line = JsonFormatter().format(make_record())

    entry = json.loads(line)
    assert "\n" not in line
    assert entry["level"] == "WARNING"
    assert entry["logger"] == "app"
    assert entry["message"] == "Disk full"
    assert entry["time"].endswith("+00:00")


def test_adds_the_current_request_id():
    token = request_id.set("abc-123")
    try:
        entry = json.loads(JsonFormatter().format(make_record()))
    finally:
        request_id.reset(token)

    assert entry["request_id"] == "abc-123"


def test_merges_structured_fields():
    entry = json.loads(JsonFormatter().format(make_record(fields={"status": 200})))

    assert entry["status"] == 200


def test_includes_the_traceback():
    try:
        raise ValueError("bad")
    except ValueError:
        record = make_record()
        record.exc_info = sys.exc_info()

    entry = json.loads(JsonFormatter().format(record))

    assert "ValueError: bad" in entry["exception"]
