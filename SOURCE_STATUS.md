# 파일 출처 및 확보 상태 (2026-10-31)

| 대상 | 이번 ZIP 상태 | 운영 원본과 일치 여부 |
|---|---|---|
| FastAPI `main.py` | 첨부된 원본에 금요일 수정 코드를 반영한 전체 파일 | 원본 SHA와 이전 수정본 일치 확인, 현장 최신 추출본은 아님 |
| 웹 탐지 `web_threat_detector.py` | 대화에서 작성하고 Kali 적용을 보고받은 소스 | 사용자 적용 및 로그 가시화 확인 |
| FastAPI UI/계정 생성/관리자 쉘 | 첨부된 ZIP 그대로 보존 | 해당 ZIP 내용 이후 운영 변경은 별도 확인 필요 |
| CCTV 팀원 FastAPI/YOLO | **코드 발췌본 2개만** 원형 보존 | 전체 실행 코드/모델/정적 파일 없음 |
| WEB/AUTH/SSH/Fail2Ban 기존 LogQL | 첨부된 ZIP 원본 보존 | 실제 대시보드 JSON export 없음 |
| 웹 위협 LogQL/보안 Bar gauge | 대화에서 입력/확인된 쿼리 텍스트 추가 | 실제 패널 Override/Threshold는 별도 메모; JSON export 없음 |
| Grafana Alert 기존 5회/10분 | 재구성 참고 문서만 존재 | 전체 Rule export 없음, 재생성하지 않음 |
| Alloy | 첨부된 과거 config.alloy + 10/30 신규 수집 블록을 정리 | 현재 운영 전체 파일이 아니므로 직접 덮어쓰기 금지 |
| Prometheus/Nginx/BIND9/Fail2Ban 정책 | 첨부된 ZIP 원형 유지 | 실제 최신 운영 원본과 동기화는 별도 확인 필요 |
| Windows 시연 BAT | 10/31 신규 소스+사용 안내 포함 | 실제 Windows 실행 시험은 사용자가 별도 확인 필요 |
| Fail2Ban Bash 관리 | 첨부된 ZIP 원형 유지 | 수동 Ban/Unban은 사용자 실측, 자동 5회 Ban은 별도 미검증 |

**필수 구분:** 제출용 코드 스냅샷과 현장 최신 원본은 다를 수 있습니다. 기계적으로 파일을 통합했다고 실제 CCTV/운영 서버 통합 실행이 보장되는 것은 아닙니다.
