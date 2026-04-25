import io
import json

from vtf.logging import Logger


def test_text_mode_writes_to_stderr():
    buf = io.StringIO()
    log = Logger(stream=buf, json_mode=False, quiet=False)
    log.info("hello", step="fetch")
    out = buf.getvalue()
    assert "hello" in out
    assert "fetch" in out


def test_json_mode_emits_jsonl():
    buf = io.StringIO()
    log = Logger(stream=buf, json_mode=True, quiet=False)
    log.warn("degraded", step="emit", data={"reason": "412"})
    line = buf.getvalue().strip()
    rec = json.loads(line)
    assert rec["level"] == "warn"
    assert rec["step"] == "emit"
    assert rec["msg"] == "degraded"
    assert rec["data"]["reason"] == "412"
    assert "ts" in rec


def test_quiet_suppresses_info_keeps_error():
    buf = io.StringIO()
    log = Logger(stream=buf, json_mode=False, quiet=True)
    log.info("should be hidden", step="fetch")
    log.error("visible", step="download")
    out = buf.getvalue()
    assert "should be hidden" not in out
    assert "visible" in out