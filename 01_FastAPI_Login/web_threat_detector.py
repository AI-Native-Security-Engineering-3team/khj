"""Read-only HTTP threat-signal detector for SentinelHub.

This module observes completed requests, never blocks them, and writes only
structured, minimized, suspicious-event metadata. No request bodies, passwords,
cookies, tokens, raw URLs, or usernames are retained in the output.

Prototype for single-worker FastAPI installations. Production deployment is
NOT implied by the presence of this file.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import os
import re
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, unquote

LOGGER = logging.getLogger("sentinelhub.web_threat_detector")

NOT_FOUND_WINDOW = 60.0
NOT_FOUND_DISTINCT_LIMIT = 5
REQUEST_WINDOW = 30.0
REQUEST_LIMIT = 60
REPORT_COOLDOWN = 60.0
STATE_IDLE_TTL = 600.0
CLEANUP_INTERVAL = 60.0
MAX_TRACKED_IPS = 5_000
MAX_REQUEST_TIMES_PER_IP = 128
MAX_404_PATHS_PER_IP = 64
MAX_PATH_CHARS = 2_048
MAX_QUERY_BYTES = 4_096
MAX_QUERY_FIELDS = 32
MAX_VALUE_CHARS = 2_048

REASONS = {
    "WEB_SENSITIVE_PATH": "민감한 웹 경로 접근 의심",
    "WEB_SQLI_SUSPECTED": "SQL Injection 의심 입력 패턴",
    "WEB_XSS_SUSPECTED": "XSS 의심 입력 패턴",
    "WEB_404_ENUMERATION": "서로 다른 존재하지 않는 경로 반복 탐색",
    "WEB_REQUEST_BURST": "짧은 시간 내 과도한 HTTP 요청",
}
# Stable priority if multiple rules match the same request.
RULE_PRIORITY = tuple(REASONS)

SQLI_PATTERNS = (
    re.compile(r"\bunion\s+(?:all\s+)?select\b", re.IGNORECASE),
    re.compile(r"['\"]\s*(?:or|and)\s+['\"]?[a-z0-9_]+['\"]?\s*=\s*['\"]?[a-z0-9_]+", re.IGNORECASE),
    re.compile(r";\s*drop\s+table\b", re.IGNORECASE),
    re.compile(r"\b(?:sleep|benchmark)\s*\(\s*\d+", re.IGNORECASE),
)
XSS_PATTERNS = (
    re.compile(r"<\s*script(?:\s|>)", re.IGNORECASE),
    re.compile(r"<\s*(?:svg|img|iframe|body)\b[^>]{0,160}\bon(?:error|load|click|mouseover)\s*=", re.IGNORECASE),
    re.compile(r"\bjavascript\s*:", re.IGNORECASE),
)


@dataclass
class _IpState:
    last_seen: float
    requests: deque[float] = field(default_factory=lambda: deque(maxlen=MAX_REQUEST_TIMES_PER_IP))
    not_found_paths: deque[tuple[float, bytes]] = field(
        default_factory=lambda: deque(maxlen=MAX_404_PATHS_PER_IP)
    )
    last_reported: dict[str, float] = field(default_factory=dict)


def _normalize_path(path: str) -> str:
    # Starlette's ASGI path is usually already decoded. Decode at most one
    # additional layer; never resolve or log user-supplied path content.
    return unquote(path[:MAX_PATH_CHARS]).lower()


def _sensitive_path_category(path: str) -> str | None:
    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        return None
    if ".env" in segments or any(s.startswith(".env.") for s in segments):
        return "ENV_FILE"
    if ".git" in segments or ".svn" in segments:
        return "VCS_METADATA"
    if "wp-admin" in segments or "phpmyadmin" in segments:
        return "ADMIN_INTERFACE"
    if segments[-1] in {"admin", "administrator", "config.json", "config.php", "web.config"}:
        return "ADMIN_OR_CONFIG"
    return None


def _secret_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    if normalized in {"pwd", "pass", "key", "code", "api_key", "apikey"}:
        return True
    return any(marker in normalized for marker in (
        "password", "passwd", "secret", "token", "session", "cookie",
        "auth", "credential", "api_key"
    ))


def _scan_values(path: str, query_string: bytes, username: str | None) -> set[str]:
    # All inputs are bounded. Query keys used for credentials are NEVER scanned
    # or written; only innocuous query values are examined transiently.
    values = [path]
    if len(query_string) <= MAX_QUERY_BYTES:
        try:
            pairs = parse_qsl(
                query_string.decode("utf-8", errors="replace"),
                keep_blank_values=True, max_num_fields=MAX_QUERY_FIELDS,
            )
        except (ValueError, UnicodeError):
            pairs = []
        for key, value in pairs:
            if not _secret_key(key):
                values.append(unquote(value[:MAX_VALUE_CHARS]))
    if username is not None:
        values.append(username[:MAX_VALUE_CHARS])

    hits: set[str] = set()
    for value in values:
        if any(pattern.search(value) for pattern in SQLI_PATTERNS):
            hits.add("WEB_SQLI_SUSPECTED")
        if any(pattern.search(value) for pattern in XSS_PATTERNS):
            hits.add("WEB_XSS_SUSPECTED")
    return hits


class WebThreatDetector:
    """Bounded in-process aggregation, safe event logging, no request blocking."""

    def __init__(self, log_path: str | Path):
        self.log_path = Path(log_path)
        self._states: OrderedDict[str, _IpState] = OrderedDict()
        self._lock = threading.Lock()
        self._next_cleanup = 0.0
        self._last_error_report: float | None = None

    def _warn_once(self, message: str, now: float) -> None:
        # Never include URLs, query parameters, usernames, or credentials.
        with self._lock:
            if self._last_error_report is not None and now - self._last_error_report < REPORT_COOLDOWN:
                return
            self._last_error_report = now
        LOGGER.warning("SentinelHub 웹 탐지 로그 오류: %s", message)

    def _cleanup(self, now: float) -> None:
        if now < self._next_cleanup:
            return
        self._next_cleanup = now + CLEANUP_INTERVAL
        # LRU order means inactive entries are at the front.
        while self._states:
            _ip, state = next(iter(self._states.items()))
            if now - state.last_seen < STATE_IDLE_TTL:
                break
            self._states.popitem(last=False)

    def _get_state(self, ip: str, now: float) -> _IpState:
        state = self._states.get(ip)
        if state is None:
            if len(self._states) >= MAX_TRACKED_IPS:
                self._states.popitem(last=False)
            state = _IpState(last_seen=now)
            self._states[ip] = state
        else:
            self._states.move_to_end(ip)
            state.last_seen = now
        return state

    def _write_event(self, record: dict[str, object]) -> None:
        data = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        flags |= getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.log_path, flags, 0o640)
        try:
            if os.name == "posix":
                os.fchmod(fd, 0o640)
            written = os.write(fd, data)
            if written != len(data):
                raise OSError("partial JSONL write")
        finally:
            os.close(fd)

    def observe(
        self,
        *,
        client_ip: str,
        method: str,
        path: str,
        query_string: bytes,
        http_status: int,
        username: str | None = None,
        now: float | None = None,
    ) -> dict[str, object] | None:
        """Observe one completed HTTP request, optionally returning its recorded event.

        `username` must be the already-parsed login username, not raw body text.
        All failures are handled internally to preserve original HTTP behavior.
        `now` is a monotonic-clock injection used only in deterministic tests.
        """
        tick = time.monotonic() if now is None else now
        try:
            # Unknown or malformed source IPs are not pooled together.
            ip = str(ipaddress.ip_address(client_ip))
            normalized_path = _normalize_path(path)
            category = _sensitive_path_category(normalized_path)
            flags = _scan_values(normalized_path, query_string, username)
            if category:
                flags.add("WEB_SENSITIVE_PATH")
            path_hash = hashlib.blake2b(normalized_path.encode("utf-8"), digest_size=16).digest()
            status = int(http_status)

            with self._lock:
                self._cleanup(tick)
                state = self._get_state(ip, tick)
                # Exclude infrastructure health polling from burst statistics.
                if normalized_path != "/api/health":
                    state.requests.append(tick)
                while state.requests and tick - state.requests[0] > REQUEST_WINDOW:
                    state.requests.popleft()
                while state.not_found_paths and tick - state.not_found_paths[0][0] > NOT_FOUND_WINDOW:
                    state.not_found_paths.popleft()
                if status == 404:
                    state.not_found_paths.append((tick, path_hash))
                distinct_paths = len({digest for _at, digest in state.not_found_paths})
                req_count = len(state.requests)
                if status == 404 and distinct_paths >= NOT_FOUND_DISTINCT_LIMIT:
                    flags.add("WEB_404_ENUMERATION")
                # The health endpoint can be polled by infrastructure normally.
                if normalized_path != "/api/health" and req_count >= REQUEST_LIMIT:
                    flags.add("WEB_REQUEST_BURST")

                eligible = [
                    rule for rule in RULE_PRIORITY
                    if rule in flags and (
                        rule not in state.last_reported
                        or tick - state.last_reported[rule] >= REPORT_COOLDOWN
                    )
                ]
                if not eligible:
                    return None
                # Reserve cooldown before I/O so concurrent requests cannot
                # emit duplicate records for a single IP/rule pair.
                for rule in eligible:
                    state.last_reported[rule] = tick

            record: dict[str, object] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "sentinelhub-web-threat",
                "event": eligible[0],
                "matched_rules": eligible,
                "client_ip": ip,
                "method": method.upper() if method.upper() in {
                    "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"
                } else "OTHER",
                "http_status": status,
                "severity": "LOW" if eligible == ["WEB_REQUEST_BURST"] else "MEDIUM",
                "reason": REASONS[eligible[0]],
            }
            if "WEB_SENSITIVE_PATH" in eligible and category:
                record["path_category"] = category
            if "WEB_404_ENUMERATION" in eligible:
                record["distinct_404_paths_60s"] = distinct_paths
            if "WEB_REQUEST_BURST" in eligible:
                record["request_count_30s"] = req_count
            try:
                self._write_event(record)
                return record
            except OSError as exc:
                # Roll back reserved cooldowns so the next event can retry.
                with self._lock:
                    state = self._states.get(ip)
                    if state is not None:
                        for rule in eligible:
                            if state.last_reported.get(rule) == tick:
                                state.last_reported.pop(rule, None)
                self._warn_once(type(exc).__name__, tick)
                return None
        except Exception as exc:
            self._warn_once(type(exc).__name__, tick)
            return None
