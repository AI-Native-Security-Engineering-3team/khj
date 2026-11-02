# 탐지 모듈 테스트 (Kali 운영 서버가 아닌 별도 테스트 환경에서 실행)

Python 가상환경에 FastAPI, Argon2, pytest, httpx가 설치되어 있어야 합니다.

```bash
cd 01_FastAPI_Login
python -m pytest -q tests/test_detector.py
```

테스트는 tempfile 경로에 계정 DB와 JSONL을 만들며 운영 서버의 `/var/log/sentinelhub`를 변경하지 않습니다.
`02_CCTV_YOLO`의 팀원 코드 발췌본은 단독 실행 소스가 아니므로 이 테스트 대상에서 제외했습니다.
