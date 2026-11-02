# SentinelHub 통합 소스코드 (2026-10-31)

SentinelHub 보안 관제 프로젝트의 통합 소스 제출본입니다. FastAPI 로그인 서비스와 웹 위협 탐지, CCTV YOLO 사람 감지, Alloy·Loki·Grafana 로그 관제, Fail2Ban 차단 정책, 내부 DNS·Nginx 설정을 기능별로 정리했습니다.

## 폴더 구성

| 경로 | 내용 |
|---|---|
| `01_FastAPI_Login/` | 게임 스타일 웹사이트, 로그인 기능, 웹 위협 탐지 모듈(`web_threat_detector.py`)과 연동한 `main.py`, 테스트 |
| `02_CCTV_YOLO/` | 팀원 CCTV FastAPI·YOLO 핵심 코드 |
| `03_Grafana/` | WEB/AUTH/SSH/Fail2Ban 쿼리, 웹 위협 상세·요약 로그, 24시간·10분 통계 쿼리, 패널 설정 |
| `04_Log_Pipeline/` | Alloy 수집 설정 (인증 로그, Nginx 접속 로그, 웹 위협 이벤트) |
| `05_Server_Configs/` | Nginx, BIND9, Prometheus 설정 |
| `06_Fail2Ban/` | Fail2Ban 정책과 관리 스크립트 |
| `07_Scripts/` | 소스 수집 도구, Windows 탐지 시연 BAT |
| `08_Documents/` | 아키텍처, 기능 검증 매트릭스, 변경 기록 |
| `09_Original_Exports/BASE_20261029/` | 웹 탐지 연동 전 `main.py`·Alloy 설정과 변경 diff (대조용) |

## 사용 시 참고
- 코드 보관·제출용 패키지이며 운영 서버 자동 배포 도구가 아닙니다. 운영 서버 설정을 이 파일로 통째로 덮어쓰지 마세요.
- `01_FastAPI_Login/main.py`와 `web_threat_detector.py`는 같은 폴더에 두어야 합니다.
- 계정 DB, 비밀번호, 세션, 실제 로그(JSONL), 개인키, CCTV 영상·얼굴 데이터, 모델 가중치는 포함하지 않습니다.
- Windows 시연 BAT는 내부 실습 대상 `192.168.0.4`에만 제한된 GET 요청을 보냅니다. 실제 공격을 수행하는 코드가 아닙니다.

## 검증
- FastAPI 소스와 웹 탐지 모듈 정적 문법 검증
- 탐지 모듈 테스트는 격리 환경에서 실행 (`01_FastAPI_Login/tests/`)
- 기존 파일과 팀원 코드는 원본과 해시 일치 확인
- 모든 파일의 SHA-256은 `MANIFEST_SHA256.txt`에 기록

## 관련 문서
- `SOURCE_STATUS.md`: 구성 요소별 출처
- `FILE_ORIGINS.json`: 파일별 해시와 출처
- `SUBMISSION_CHECKLIST.md`: 제출 구성 체크리스트
- `08_Documents/CHANGELOG_20261030_31.md`: 변경 내역
