"""Create one local lab user with an Argon2id password hash (no public registration)."""
import argparse
import getpass
import re
import sqlite3
import time

from main import connect_db, init_db, log_event, password_hasher


def main():
    parser = argparse.ArgumentParser(description="SentinelHub login-lab user management")
    parser.add_argument("--username", required=True, help="3-32 chars: letters, numbers, _, . or -")
    parser.add_argument("--reset-password", action="store_true", help="Change an existing user's password")
    args = parser.parse_args()
    username = args.username.strip().lower()
    if not re.fullmatch(r"[a-z0-9_.-]{3,32}", username):
        parser.error("Use 3-32 lowercase letters, numbers, _, . or -")

    init_db()
    with connect_db() as con:
        exists = con.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone() is not None
    if exists and not args.reset_password:
        parser.error("User already exists. Use --reset-password to change its password.")
    if not exists and args.reset_password:
        parser.error("Cannot reset: user does not exist.")

    p1 = getpass.getpass("Password (at least 1 char): ")
    p2 = getpass.getpass("Confirm password: ")
    if len(p1) < 1 or len(p1) > 256:
        parser.error("Password must be 1-256 characters")
    if p1 != p2:
        parser.error("Passwords do not match")

    digest = password_hasher.hash(p1)
    with connect_db() as con:
        if exists:
            con.execute("UPDATE users SET password_hash=? WHERE username=?", (digest, username))
            con.execute("DELETE FROM sessions WHERE username=?", (username,))
        else:
            con.execute("INSERT INTO users(username,password_hash,created_at) VALUES(?,?,?)",
                        (username, digest, int(time.time())))
    log_event("PASSWORD_RESET" if exists else "ACCOUNT_CREATED", "127.0.0.1", username)
    print(f"User '{username}' {'password updated' if exists else 'created'} successfully.")


if __name__ == "__main__":
    main()
