# SentinelHub 게임 스타일 로그인 + 웹 공격 징후 탐지 (2026-10-31 정리)

원본 `main.py`에 웹 탐지 미들웨어 연결 코드만 추가한 버전입니다. 웹 화면(`web/index.html`), 계정 생성(`create_user.py`), 기존 `sentinelhub-manager.sh`는 **업로드 ZIP의 내용을 변경하지 않았습니다.**

## 구성
- `main.py`: FastAPI 로그인, 세션 관리, 기존 보안 헤더 및 웹 탐지 연결
- `web_threat_detector.py`: 민감 경로, 404 경로 열거, 30초 요청 폭주, SQLi/XSS 의심 패턴을 읽기 전용으로 관찰
- `create_user.py`, `web/index.html`: 기존 로그인 UI와 계정 관리
- `tests/test_detector.py`: 격리 환경 회귀 테스트

## 운영 환경과 파일 경로
- Kali Purple, Nginx :80 → Uvicorn `127.0.0.1:8000 --workers 1`
- 기존 인증 이벤트: `/var/log/sentinelhub/security-events.jsonl` (`kali:alloy`, 640)
- 새 탐지 이벤트: `/var/log/sentinelhub/web-threat-events.jsonl` (`kali:alloy`, 640)
- 계정 DB: `data/sentinelhub.sqlite3` (ZIP에 포함하지 않음)
- 도메인: `http://sentinelhub.com` (내부 LAN 실습 전용)

## 탐지 규칙 요약
| 규칙 | 기본 조건 |
|---|---|
| WEB_SENSITIVE_PATH | `.env`, `.git` 등 민감 경로 접근 1회 |
| WEB_404_ENUMERATION | 동일 IP의 서로 다른 404 경로 60초에 5개 |
| WEB_REQUEST_BURST | 동일 IP의 30초당 60요청 (health 제외) |
| WEB_SQLI_SUSPECTED | URL/쿼리/기존 파싱된 사용자명의 SQLi 의심 패턴 |
| WEB_XSS_SUSPECTED | URL/쿼리/기존 파싱된 사용자명의 XSS 의심 패턴 |

- 동일 IP/규칙 중복 이벤트 기록은 약 60초 억제, 여러 규칙이 동시에 일치하면 한 JSONL 행에 병합합니다.
- 비밀번호, 쿠키, 세션 토큰, 요청 본문, 원본 URL/쿼리 값은 새 로그에 저장하지 않습니다.
- 기존 로그인 실패 제한과 Alert/Fail2Ban 설정은 변경하지 않습니다.
- 단일 워커의 프로세스 메모리 집계이며 재시작 시 초기화됩니다.
- 의심 입력 탐지이지 실제 공격 성공을 뜻하지 않습니다.

## 기존 서비스 적용 주의
이 ZIP은 코드 제출/보관을 위한 **소스 스냅샷**이며 재설치 지침이 아닙니다. 운영 서버에는 이미 적용했다는 사용자 확인이 있습니다. 실제 운영 서버 파일과 완전히 동일한지 증명하려면 **Kali 운영 원본을 별도 수집**해야 합니다.

```bash
cd /home/kali/sentinelhub_fastapi_login
./.venv/bin/python -m py_compile main.py web_threat_detector.py
./.venv/bin/python -c 'import main; print("IMPORT OK")'
```

실제 접속은 Nginx 뒤의 `sentinelhub.com`으로 하고, Uvicorn은 루프백에만 바인딩합니다. 신규 `main.py`와 `web_threat_detector.py`는 항상 같은 폴더에 있어야 합니다. 기존 DB·UI·인증 로그·기타 서비스는 덮어쓰지 마세요.
