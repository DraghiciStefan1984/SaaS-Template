import json
import logging

from apps.common.logging import JsonFormatter


def test_json_formatter_emits_structured_log_record():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="apps.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-1"
    record.environment = "test"
    record.deploy_version = "unit"

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "apps.test"
    assert payload["message"] == "hello"
    assert payload["request_id"] == "req-1"
    assert payload["environment"] == "test"
    assert payload["deploy_version"] == "unit"
