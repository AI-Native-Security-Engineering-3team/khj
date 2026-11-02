# SentinelHub 기능 검증 현황 (2026-10-31 기준)

| 기능 | 상태 | 확인 방법/제한 |
|---|---|---|
| DHCP 예약, 내부 BIND9/Nginx | 사용자 완료 확인 | 운영장소가 바뀌어도 .3/.4 재구성 |
| FastAPI 로그인, 세션, 계정 DB | 기존 정상 및 10/30 격리 회귀 테스트 통과 | 운영 계정 DB는 ZIP에 없음 |
| 웹 공격 징후 탐지 FastAPI 모듈 | 운영 적용/로그 표시 사용자 확인 | 원본 기반 `main.py` + 탐지 모듈 소스 확보 |
| 신규 JSONL Alloy → Loki | 운영 동작 사용자 확인 | 실제 최신 운영 `config.alloy` 미수집 |
| WEB/AUTH/SSH/Fail2Ban 한국어 로그 | 사용자 확인 | 기존 쿼리 보존 |
| WEB 위협 상세/간략 Logs | 통합 로그 및 기존 로그 패널에서 사용자 확인 | 신규 쿼리 백업 포함 |
| 웹 공격 징후·SSH 인증 실패 통계 | 사용자 확인 | 24시간 집계, Overrides 이름 지정 |
| 웹 로그인 실패 단독 Bar gauge | 사용자 확인 | `LOGIN_FAILED` 10분 집계 및 패널 Title |
| WEB+SSH 동일 IP 인증 실패 ≥5/10m Alert | 실제 Firing 사용자 확인 | 기존 경고 규칙 유지 (원본 export 없음) |
| Alert list 상태 표시 | 사용자 확인 | Normal 숨김 권장/선호 |
| Fail2Ban 수동 Ban/Unban + nftables | 사용자 검증 | 실패 5회 자동 Ban 전체 과정은 별도 미검증 |
| CCTV YOLO 사람 감지 | 사용자 확인 | 첨부 팀원 발췌본은 단독 실행 불가 |
| CCTV 경고 연동 | 사용자 완료 보고 | 실제 전체 코드 확인 전 세부 내용 단정 금지 |
| CCTV 없는 장소에서 Hide response | 사용자 실측 | 에러 문구 남지만 다른 로그 갱신 유지 |
| Windows 공격 징후 시연 BAT | 소스 제작/정적 점검 | 실제 Windows CMD 실행 결과는 별도 미검증 |

**이 파일의 확인 상태는 사용자의 보고/대화 근거이며**, 모든 서버에서 동일한 소스를 다시 추출했다는 뜻은 아닙니다.
