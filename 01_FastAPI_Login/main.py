"""SentinelHub educational login site (FastAPI, SQLite, Argon2id)."""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from web_threat_detector import WebThreatDetector

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
WEB = BASE / "web" / "index.html"
DATABASE = DATA / "sentinelhub.sqlite3"
EVENTS = Path("/var/log/sentinelhub/security-events.jsonl")
COOKIE = "sentinelhub_session"
SESSION_AGE = 12 * 60 * 60
REMEMBER_AGE = 7 * 24 * 60 * 60
WINDOW_SECONDS = 5 * 60
FAIL_LIMIT = 5
# For internal HTTP testing only. Set SENTINELHUB_SECURE_COOKIES=1 after HTTPS is configured.
SECURE_COOKIES = os.environ.get("SENTINELHUB_SECURE_COOKIES", "0") == "1"
password_hasher = PasswordHasher()
# Independent audit trail; does not modify existing authentication events.
threat_detector = WebThreatDetector("/var/log/sentinelhub/web-threat-events.jsonl")


def connect_db():
    con = sqlite3.connect(DATABASE, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout = 10000")
    return con


def init_db():
    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name == "posix":
        DATA.chmod(0o700)
    with connect_db() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                client_ip TEXT NOT NULL,
                success INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_login_attempts_time
                ON login_attempts(created_at);
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                expires_at INTEGER NOT NULL
            );
        """)
    if os.name == "posix" and DATABASE.exists():
        DATABASE.chmod(0o600)


def log_event(event: str, client_ip: str, username: str | None = None, **details):
    # Never log raw passwords, cookies or access tokens.
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "sentinelhub-login",
        "event": event,
        "client_ip": client_ip,
    }
    if username:
        record["username"] = username
    record.update(details)
    DATA.mkdir(parents=True, exist_ok=True)
    with EVENTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    if os.name == "posix":
        EVENTS.chmod(0o640)


def client_ip(request: Request) -> str:
    remote = request.client.host if request.client else "unknown"
    # Only trust X-Real-IP when the immediate peer is our local Nginx.
    if remote in ("127.0.0.1", "::1"):
        forwarded = request.headers.get("x-real-ip", "")
        try:
            return str(ipaddress.ip_address(forwarded))
        except ValueError:
            pass
    return remote


def verify_same_origin(request: Request):
    # Browser sends Origin for cross-origin POSTs. SameSite=Lax offers another layer.
    origin = request.headers.get("origin")
    if origin:
        parsed = urlsplit(origin)
        host = request.headers.get("host", "")
        if parsed.scheme not in ("http", "https") or parsed.netloc.lower() != host.lower():
            raise HTTPException(status_code=403, detail="허용되지 않은 요청 출처입니다.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="SentinelHub Login Lab", docs_url=None, redoc_url=None, lifespan=lifespan)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    # Observe only after the normal response is produced; NEVER read the body.
    # Detection failures must not affect HTTP results or authentication.
    try:
        threat_detector.observe(
            client_ip=client_ip(request),
            method=request.method,
            path=request.url.path,
            query_string=request.scope.get("query_string", b""),
            http_status=response.status_code,
            username=getattr(request.state, "threat_username", None),
        )
    except Exception:
        pass  # The detector independently emits rate-limited diagnostics.
    return response


class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)
    remember: bool = False


@app.get("/", include_in_schema=False)
def homepage():
    return FileResponse(WEB, media_type="text/html", headers={"Cache-Control": "no-cache"})


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "sentinelhub-login"}


def current_username(request: Request) -> str | None:
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    digest = hashlib.sha256(token.encode()).hexdigest()
    now = int(time.time())
    with connect_db() as con:
        row = con.execute("SELECT username FROM sessions WHERE token_hash=? AND expires_at>?", (digest, now)).fetchone()
    return row["username"] if row else None


@app.get("/api/session")
def session_info(request: Request):
    user = current_username(request)
    return {"authenticated": bool(user), "username": user}


@app.post("/api/login")
def login(payload: LoginInput, request: Request, response: Response):
    verify_same_origin(request)
    now = int(time.time())
    username = payload.username.strip().lower()
    ip = client_ip(request)
    # Only this validated, already-parsed field is passed to the detector.
    request.state.threat_username = username
    if not username or len(username) > 32:
        raise HTTPException(status_code=400, detail="아이디 형식을 확인하세요.")

    # Two scopes: a source IP and a username. This is a learning-friendly throttle,
    # not a fully distributed rate limiter (one Uvicorn worker is recommended).
    with connect_db() as con:
        failed_recently = con.execute("""
            SELECT COUNT(*) AS n FROM login_attempts
            WHERE created_at >= ? AND success=0 AND (client_ip=? OR username=?)
        """, (now - WINDOW_SECONDS, ip, username)).fetchone()["n"]
        if failed_recently >= FAIL_LIMIT:
            log_event("LOGIN_RATE_LIMITED", ip, username, recent_failures=failed_recently)
            raise HTTPException(status_code=429, detail="로그인 시도가 너무 많습니다. 잠시 후 다시 시도하세요.",
                                headers={"Retry-After": "300"})
        user = con.execute("SELECT password_hash FROM users WHERE username=?", (username,)).fetchone()

    verified = False
    # Always perform a password-hash check, including nonexistent usernames.
    hash_to_check = user["password_hash"] if user else DUMMY_HASH
    try:
        verified = password_hasher.verify(hash_to_check, payload.password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        verified = False
    if not (user and verified):
        with connect_db() as con:
            con.execute("INSERT INTO login_attempts(username, client_ip, success, created_at) VALUES(?,?,0,?)",
                        (username, ip, now))
        log_event("LOGIN_FAILED", ip, username, recent_failures=failed_recently + 1)
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode()).hexdigest()
    lifetime = REMEMBER_AGE if payload.remember else SESSION_AGE
    with connect_db() as con:
        con.execute("INSERT INTO login_attempts(username, client_ip, success, created_at) VALUES(?,?,1,?)",
                    (username, ip, now))
        con.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
        con.execute("INSERT INTO sessions(token_hash, username, expires_at) VALUES(?,?,?)",
                    (digest, username, now + lifetime))
    response.set_cookie(
        COOKIE, token, httponly=True, samesite="lax", secure=SECURE_COOKIES,
        max_age=REMEMBER_AGE if payload.remember else None, path="/"
    )
    log_event("LOGIN_SUCCESS", ip, username)
    return {"authenticated": True, "username": username}


@app.post("/api/logout")
def logout(request: Request, response: Response):
    verify_same_origin(request)
    user = current_username(request)
    token = request.cookies.get(COOKIE)
    if token:
        with connect_db() as con:
            con.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))
    response.delete_cookie(COOKIE, path="/")
    if user:
        log_event("LOGOUT", client_ip(request), user)
    return {"authenticated": False}


# Slow down account enumeration via timing differences when username does not exist.
# No demo passwords or secrets are stored in the source tree.
DUMMY_HASH = password_hasher.hash(secrets.token_urlsafe(20))
