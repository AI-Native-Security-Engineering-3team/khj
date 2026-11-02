# 구성 요소별 출처 (2026-10-31)

| 대상 | 출처 |
|---|---|
| FastAPI `main.py` | 기존 원본에 웹 탐지 미들웨어 연동 코드 반영 (변경 전 원본은 `09_Original_Exports/BASE_20261029/`) |
| 웹 탐지 `web_threat_detector.py` | 10/30 신규 작성, Kali 서버 적용 및 Grafana 로그 표시 확인 |
| FastAPI UI/계정 생성/관리자 쉘 | 기존 원본 유지 |
| CCTV 팀원 FastAPI/YOLO | 팀원 핵심 코드 원형 유지 |
| WEB/AUTH/SSH/Fail2Ban LogQL | 기존 원본 유지 |
| 웹 위협 LogQL/보안 Bar gauge | 10/30~31 신규 쿼리, 패널 설정은 `03_Grafana/PANEL_OPTIONS_20261031.md` |
| Grafana Alert (인증 실패 5회/10분) | 규칙 주석 정리본 `03_Grafana/alert_rule_annotations_reference.md` |
| Alloy | 기존 `config.alloy`에 10/30 웹 위협 수집 블록 추가 |
| Prometheus/Nginx/BIND9/Fail2Ban 정책 | 기존 원본 유지 |
| Windows 시연 BAT | 10/31 신규 작성, 사용 안내 포함 |
| Fail2Ban Bash 관리 | 기존 원본 유지 |
