"""Standalone offline checks: no changes to the running Kali server."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from web_threat_detector import WebThreatDetector


def observe(detector: WebThreatDetector, *, path="/", t=0., ip="192.0.2.15", status=200, query=b"", username=None):
    return detector.observe(
        client_ip=ip, method="GET", path=path, query_string=query,
        http_status=status, username=username, now=t,
    )


def rows(path: Path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


@pytest.fixture
def log(tmp_path):
    return tmp_path / "web-threat-events.jsonl"


@pytest.fixture
def detector(log):
    return WebThreatDetector(log)


def test_normal_request_no_threat_log(detector, log):
    assert observe(detector, path="/", t=1.) is None
    assert observe(detector, path="/api/session", t=2.) is None
    assert not log.exists()


def test_repeated_same_404_path_not_enumeration(detector, log):
    for index in range(7):
        assert observe(detector, path="/missing", status=404, t=float(index)) is None
    assert not log.exists()


def test_distinct_404_paths_trigger_once_with_cooldown(detector, log):
    for index in range(4):
        assert observe(detector, path=f"/missing{index}", status=404, t=float(index)) is None
    event = observe(detector, path="/missing4", status=404, t=4.)
    assert event["event"] == "WEB_404_ENUMERATION"
    assert event["distinct_404_paths_60s"] == 5
    for index in range(5, 10):
        assert observe(detector, path=f"/missing{index}", status=404, t=float(index)) is None
    assert len(rows(log)) == 1


def test_sensitive_path_and_credential_query_redaction(detector, log):
    event = observe(detector, path="/.env", status=404, t=0., query=b"password=mySecret42&access_token=123abc")
    assert event["event"] == "WEB_SENSITIVE_PATH"
    assert event["path_category"] == "ENV_FILE"
    encoded = log.read_text()
    for secret in ("mySecret42", "123abc", "password", "access_token", "/.env"):
        assert secret not in encoded


def test_sqli_username_indicators_without_username_logging(detector, log):
    injection = "' OR '1'='1"
    event = observe(detector, path="/api/login", t=1., status=401, username=injection)
    assert event["event"] == "WEB_SQLI_SUSPECTED"
    assert injection not in log.read_text()
    assert "username" not in event


def test_xss_query_and_double_encoded_query(detector, log):
    event = observe(detector, t=0., query=b"q=%3Cscript%3Ealert(1)%3C%2Fscript%3E")
    assert event["event"] == "WEB_XSS_SUSPECTED"
    assert "<script>" not in log.read_text()
    second = observe(detector, t=1., ip="192.0.2.16", query=b"q=%253Cscript%253Ealert(1)%253C/script%253E")
    assert second["event"] == "WEB_XSS_SUSPECTED"


def test_simultaneous_signals_one_event(detector, log):
    event = observe(detector, path="/.git/config", t=1., status=404, query=b"q=%3Cscript%3E")
    assert event["event"] == "WEB_SENSITIVE_PATH"
    assert event["matched_rules"] == ["WEB_SENSITIVE_PATH", "WEB_XSS_SUSPECTED"]
    assert len(rows(log)) == 1


def test_burst_only_after_sixty_requests(detector, log):
    for i in range(59):
        assert observe(detector, path="/api/session", t=i / 10) is None
    event = observe(detector, path="/api/session", t=5.9)
    assert event["event"] == "WEB_REQUEST_BURST"
    assert event["request_count_30s"] == 60
    for i in range(60, 70):
        assert observe(detector, path="/api/session", t=i / 10) is None
    assert len(rows(log)) == 1


def test_health_checks_excluded_from_burst(detector, log):
    for i in range(80):
        assert observe(detector, path="/api/health", t=i / 100) is None
    assert observe(detector, path="/", t=1.) is None
    assert not log.exists()


def test_invalid_ip_is_not_aggregated(detector, log):
    assert observe(detector, ip="unknown", path="/.env", status=404) is None
    assert not log.exists()


def test_bounded_ip_state(detector):
    for i in range(5_010):
        ip = f"10.{i // 65536}.{(i // 256) % 256}.{i % 256}"
        assert observe(detector, ip=ip, path="/", t=0.) is None
    assert len(detector._states) <= 5_000
    assert len(next(iter(detector._states.values())).requests) <= 128


def test_log_failure_preserves_response_and_recovers(tmp_path):
    target = tmp_path / "missing" / "web-threat-events.jsonl"
    detector = WebThreatDetector(target)
    assert observe(detector, path="/.env", status=404, t=1.) is None
    target.parent.mkdir()
    assert observe(detector, path="/.env", status=404, t=2.)["event"] == "WEB_SENSITIVE_PATH"
    assert len(rows(target)) == 1


def test_cooldown_uses_monotonic_time(detector, log):
    assert observe(detector, path="/.env", status=404, t=5.) is not None
    assert observe(detector, path="/.git/config", status=404, t=6.) is None
    assert observe(detector, path="/.git/config", status=404, t=65.) is not None
    assert len(rows(log)) == 2


def test_query_secret_field_is_not_scanned(detector, log):
    assert observe(detector, t=1., query=b"access_token=%3Cscript%3E") is None
    assert observe(detector, t=2., query=b"q=normal+SQL+SELECT+word") is None
    assert not log.exists()


def test_standalone_fastapi_regression_in_isolated_directory(tmp_path, monkeypatch):
    """Copy-only test: original uploaded main.py is NOT changed or executed in place."""
    original_source = (Path(__file__).resolve().parents[1] / "main.py").read_text()
    testing_main = tmp_path / "main.py"
    testing_main.write_text(original_source)
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "index.html").write_text("<html>stand-in</html>")
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    spec = importlib.util.spec_from_file_location("sentinelhub_draft_test_main", testing_main)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.EVENTS = tmp_path / "security-events.jsonl"
    threat_log = tmp_path / "web-threat-events.jsonl"
    module.threat_detector = WebThreatDetector(threat_log)

    with TestClient(module.app, client=("127.0.0.1", 40000), headers={"X-Real-IP": "192.0.2.15"}) as api:
        health = api.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        assert health.headers["x-content-type-options"] == "nosniff"
        assert api.get("/").status_code == 200
        assert api.get("/api/session").json()["authenticated"] is False
        assert api.post("/api/login", json={"username": "ghost", "password": "wrong"}).status_code == 401
        with module.connect_db() as db:
            db.execute("INSERT INTO users(username,password_hash,created_at) VALUES (?,?,?)", (
                "alice", module.password_hasher.hash("CorrectHorseBatteryStaple!"), 1
            ))
        success = api.post("/api/login", json={"username": "alice", "password": "CorrectHorseBatteryStaple!"})
        assert success.status_code == 200
        assert api.get("/api/session").json()["authenticated"] is True
        assert api.post("/api/logout").json()["authenticated"] is False
        assert api.get("/.env").status_code == 404
        assert api.get("/missing").status_code == 404
        assert api.get("/api/health").headers["cache-control"] == "no-store"

    auth_events = [r["event"] for r in rows(module.EVENTS)]
    assert auth_events == ["LOGIN_FAILED", "LOGIN_SUCCESS", "LOGOUT"]
    threat_events = rows(threat_log)
    assert len(threat_events) == 1
    assert threat_events[0]["event"] == "WEB_SENSITIVE_PATH"
    assert threat_events[0]["client_ip"] == "192.0.2.15"
    assert "CorrectHorseBatteryStaple!" not in threat_log.read_text()
    assert "CorrectHorseBatteryStaple!" not in module.EVENTS.read_text()
    assert (tmp_path / "data" / "sentinelhub.sqlite3").exists()
