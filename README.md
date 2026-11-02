# SentinelHub — 통합 소스코드 패키지 (2026-10-31 갱신)

**입력 자료**: 사용자가 첨부한 `SentinelHub_소스코드.zip` (56개 항목), 10/30에 작성·사용자가 Kali 적용을 보고한 FastAPI 탐지 모듈 소스, 10/31 Windows BAT 시연 소스, 대화에서 확인된 Grafana LogQL/설정 내용.

## 폴더 구성

| 경로 | 내용/변경 |
|---|---|
| `01_FastAPI_Login/` | 게임 스타일 웹사이트, 로그인 기능, **신규 탐지 모듈과 수정 main.py** (10/30) |
| `02_CCTV_YOLO/` | 팀원 FastAPI·YOLO 핵심 코드 **원본 그대로 보존** (전체 프로젝트 아님) |
| `03_Grafana/` | 기존 쿼리 + 웹 탐지 상세/간략 로그, 24h 웹·SSH 및 10m 웹 로그인 통계, 패널 설정 메모 |
| `04_Log_Pipeline/` | 기존 Alloy 설정 참고본 + 신규 web-threat 수집 블록 |
| `05_Server_Configs/` | Nginx, BIND9, Prometheus 관련 업로드된 파일 유지 |
| `06_Fail2Ban/` | 관리 스크립트 및 정책 파일 유지 |
| `07_Scripts/` | 소스 수집 도구 + **Windows 탐지 시연 BAT** (10/31) |
| `08_Documents/` | 아키텍처, 기능 검증 매트릭스, 변경 기록 |
| `09_Original_Exports/BASE_20261029/` | 교체 전의 main.py, Alloy 설정과 코드 diff (대조용) |

## 사용 시 중요 사항
- 이 ZIP은 **코드 보관·제출용 통합본**이며, 운영 서버 자동 배포/재설치 도구가 아닙니다.
- `01_FastAPI_Login/main.py`와 `web_threat_detector.py`는 **같은 폴더**에 두어야 합니다.
- 기존 계정 DB, 비밀번호, 세션, 실제 로그(JSONL), 개인키, CCTV 영상/얼굴 데이터 및 모델 가중치는 포함하지 않습니다.
- 기존 정상 동작 중인 웹 UI/SQLite/인증 로그/Fail2Ban/다른 Grafana 패널을 임의로 초기화하지 마세요.
- 실제 운영의 최신 Alloy 전체 파일/대시보드 JSON/Alert export는 별도로 받지 않았으므로 일부 설정은 대화 기반 참고본입니다. `SOURCE_STATUS.md`로 구분하세요.
- `02_CCTV_YOLO` 파일 2개는 팀원 코드 발췌본이며, **단독 실행 불가**입니다. 동작 확인은 전체 팀원 소스가 필요합니다.
- Windows 시연 BAT는 내부 실습 대상 `192.168.0.4`에만 제한된 GET 요청을 보냅니다. 실제 공격 성공을 재현하는 코드가 아닙니다.

## 검증
- FastAPI 소스 및 웹 탐지 모듈 정적 문법 검증
- 탐지 테스트는 격리 환경에서 실행 (아래 별도 기록)
- 업로드 ZIP에서 보존된 팀원·기존 파일 해시 일치 검증
- ZIP CRC 및 모든 파일 SHA-256 목록은 `MANIFEST_SHA256.txt`에 기록

## 출처/적용 전 체크
- `SOURCE_STATUS.md`: 원본/추가/재구성 내용 구분
- `FILE_ORIGINS.json`: 파일별 해시와 출처
- `SUBMISSION_CHECKLIST.md`: 실제 제출 전 확인해야 할 내용

자세한 변경 내역: `08_Documents/CHANGELOG_20261030_31.md`.
