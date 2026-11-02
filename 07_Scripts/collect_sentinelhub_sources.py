#!/usr/bin/env python3
"""SentinelHub: collect existing code/config in a private STAGING folder.

IMPORTANT: No services are modified, and no source is fabricated. Do not share
staging files until reviewing them for credentials, personal data, and licenses.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import pwd
import shutil
import stat
import sys
from pathlib import Path

MAX_FILE = 5 * 1024 * 1024
ALLOWED_SUFFIX = {'.py', '.sh', '.html', '.css', '.js', '.svg', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.ico', '.toml', '.md', '.txt', '.service'}
ALLOWED_NAMES = {'Dockerfile', 'Makefile', 'requirements.txt', 'pyproject.toml', 'README', 'README.md', 'README.txt'}
SKIP_SUFFIX = {'.db', '.sqlite', '.sqlite3', '.jsonl', '.log', '.pem', '.key', '.p12', '.pfx', '.crt', '.bak', '.zip'}
SKIP_DIRS = {'.git', '.venv', 'venv', 'env', '.env', '__pycache__', '.mypy_cache', '.pytest_cache', 'node_modules', 'data', 'logs', 'log', 'instance', 'sessions', 'snapshots', 'uploads', 'secrets', 'credentials'}
SKIP_PARTS = ('password', 'credential', 'token', 'private', 'secret', 'id_rsa', 'id_ed25519')
# These are only *known locations*, not guesses at running configurations.
ETC_FILES = {
    '04_Log_Pipeline/config.alloy': 'alloy/config.alloy',
    '05_Server_Configs/prometheus.yml': 'prometheus/prometheus.yml',
    '05_Server_Configs/nginx/default': 'nginx/sites-available/default',
    '05_Server_Configs/bind9/named.conf.options': 'bind/named.conf.options',
    '05_Server_Configs/bind9/named.conf.local': 'bind/named.conf.local',
    '05_Server_Configs/bind9/db.sentinelhub.com': 'bind/db.sentinelhub.com',
    '06_Fail2Ban/99-sentinelhub.local': 'fail2ban/jail.d/99-sentinelhub.local',
}


def identity():
    who = os.environ.get('SUDO_USER') or pwd.getpwuid(os.getuid()).pw_name
    entry = pwd.getpwnam(who)
    return who, Path(entry.pw_dir), entry.pw_uid, entry.pw_gid


def is_safe_app_file(base: Path, p: Path) -> bool:
    if p.is_symlink() or not p.is_file():
        return False
    rel = p.relative_to(base)
    if any(part.lower() in SKIP_DIRS for part in rel.parts[:-1]):
        return False
    name = p.name.lower()
    if name.startswith('.') or any(marker in name for marker in SKIP_PARTS):
        return False
    if p.suffix.lower() in SKIP_SUFFIX:
        return False
    if not (p.suffix.lower() in ALLOWED_SUFFIX or p.name in ALLOWED_NAMES):
        return False
    try:
        if p.stat().st_size > MAX_FILE:
            return False
    except OSError:
        return False
    return True


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.umask(0o077)  # private export; no world-readable temporary directories
    parser = argparse.ArgumentParser(description='Read-only SentinelHub source/config collector (private staging).')
    parser.add_argument('--user-home', type=Path, help='override home directory for testing')
    parser.add_argument('--etc-root', type=Path, default=Path('/etc'), help='override /etc root for testing')
    parser.add_argument('--dest', type=Path, help='new private output directory; must not exist')
    args = parser.parse_args()
    who, detected_home, uid, gid = identity()
    home = args.user_home or detected_home
    name = 'SentinelHub_Export_' + dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    out = args.dest or (home / name)
    if out.exists():
        parser.error(f'output directory already exists (will not overwrite): {out}')
    out.mkdir(mode=0o700, parents=True)
    copied, missing, skipped = [], [], []

    def copy_one(src: Path, relative: str):
        try:
            if src.is_symlink() or not src.is_file():
                missing.append(str(src))
                return
            dst = out / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            os.chmod(dst, 0o600)
            copied.append((str(src), relative, sha256(dst)))
        except (OSError, PermissionError) as exc:
            missing.append(f'{src} ({type(exc).__name__}: {exc})')

    source = home / 'sentinelhub_fastapi_login'
    if source.is_dir():
        for base, dirs, files in os.walk(source, followlinks=False):
            basedir = Path(base)
            dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS and not (basedir / d).is_symlink()]
            for filename in files:
                p = basedir / filename
                if is_safe_app_file(source, p):
                    copy_one(p, '01_FastAPI_Login/' + str(p.relative_to(source)))
                else:
                    skipped.append(str(p))
    else:
        missing.append(str(source))

    for filename in ('sentinelhub-manager.sh', 'sentinelhub-fail2ban-manager.sh'):
        path = home / filename
        if path.is_file():
            target = ('06_Fail2Ban/' if 'fail2ban' in filename else '07_Scripts/') + filename
            copy_one(path, target)
        else:
            missing.append(str(path))

    for dest_rel, src_rel in ETC_FILES.items():
        copy_one(args.etc_root / src_rel, dest_rel)

    for folder in ('02_CCTV_YOLO', '03_Grafana', '08_Documents'):
        (out / folder).mkdir(exist_ok=True)
    (out / '02_CCTV_YOLO/TEAM_SOURCE_REQUIRED.txt').write_text('다른 팀원 PC의 FastAPI+YOLO 원본은 해당 작성자로부터 별도 확보하세요. 이 파일은 실제 소스가 아닙니다.\n', encoding='utf-8')
    (out / '03_Grafana/DASHBOARD_AND_ALERT_EXPORT_REQUIRED.txt').write_text('Grafana cctv Dashboard JSON과 SentinelHub Alert rule export는 Grafana UI에서 각각 별도 내보내기 후 수동 추가하세요.\n', encoding='utf-8')
    (out / 'SECURITY_REVIEW_REQUIRED.md').write_text(
        '# 외부 제출 전 보안 검토 필수\n\n'
        '이 폴더는 실제 Kali에서 **읽기만** 하여 복사한 비공개 검토용 사본입니다. '
        '의도적으로 DB, .env, JSONL, 로그, 키 등을 제외했지만 Python/HTML/JS/시스템 설정 파일 내부에 '
        '비밀번호·API 키·개인정보가 들어 있을 수 있습니다. 파일별로 직접 검토하고 마스킹하세요.\n\n'
        '- Grafana Dashboard JSON 및 Alert 규칙은 UI에서 수동 내보내기 필요\n'
        '- 팀원 YOLO 소스는 작성자 허락을 받은 후 추가\n'
        '- IP/도메인/사용자 이름 등 외부 공개 부적절한 값 별도 검토\n'
        '- 이 디렉터리를 검토 전 그대로 제출하지 마세요.\n', encoding='utf-8')
    inventory = ['# SentinelHub 현장 파일 수집 결과', '', f'- 생성 시각: {dt.datetime.now().isoformat(timespec="seconds")}',
                 f'- 수집 대상 계정: {who}', f'- 수집 파일: {len(copied)}개', '', '## 복사된 파일 (원본 경로 → 제출 경로, SHA256)', '']
    inventory.extend(f'- `{src}` → `{rel}` | `{hashv}`' for src, rel, hashv in copied)
    inventory.extend(['', '## 발견되지 않았거나 읽지 못한 대상', ''])
    inventory.extend(f'- `{p}`' for p in missing)
    inventory.extend(['', f'## 자동 제외한 소스 디렉터리 파일: {len(skipped)}개', ''])
    inventory.extend(f'- `{p}`' for p in skipped[:100])
    if len(skipped) > 100:
        inventory.append(f'- ... 그 밖에 {len(skipped)-100}개')
    (out / 'COLLECTION_MANIFEST.md').write_text('\n'.join(inventory) + '\n', encoding='utf-8')

    # Non-root users must be able to review their private export via FileZilla.
    if os.geteuid() == 0 and (out.resolve().is_relative_to(home.resolve())):
        for base, dirs, files in os.walk(out):
            os.chown(base, uid, gid)
            os.chmod(base, 0o700)
            for f in files:
                p = Path(base) / f
                os.chown(p, uid, gid)
                os.chmod(p, 0o600)
    print(f'수집 완료: {out}')
    print(f'파일 {len(copied)}개 복사, 경로 오류 {len(missing)}개. 기존 설정과 서비스는 변경하지 않았습니다.')
    print('주의: 실제 원본이 복사된 검토용 사본입니다. 비밀값 점검 후에만 제출하세요.')


if __name__ == '__main__':
    main()
