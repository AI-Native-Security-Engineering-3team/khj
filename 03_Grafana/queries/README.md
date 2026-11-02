# SentinelHub Grafana LogQL / PromQL 쿼리 백업

업로드된 기존 `A_WEB`·`B_AUTH`·`C_SSH`·`D_FAIL2BAN`, Fail IP 집계 및 PromQL 파일은 원형을 보존했습니다. 추가된 파일은 10월 30~31일 대화에서 사용한 쿼리 텍스트입니다.

| 파일 | 사용 위치 |
|---|---|
| `E_WEB_THREAT_DETAIL_한국어.logql` | 통합 보안 로그 패널의 신규 웹 공격 징후 쿼리 |
| `WEB_THREAT_SHORT_한국어.logql` | 기존 로그 패널의 웹 공격 징후 간략 쿼리 |
| `WEB_THREAT_BY_EVENT_24h.logql` | Bar gauge: 웹 공격 징후 24시간 통계 |
| `SSH_FAILED_24h.logql` | Bar gauge: SSH 인증 실패 24시간 통계 |
| `WEB_LOGIN_FAILED_10m.logql` | 별도 Bar gauge: 웹 로그인 실패 10분 통계 |
| `FAIL_IP_10m_WEB_SSH.logql` | 기존 IP별 WEB+SSH 실패 합계 (변경 없음) |

이 파일들은 **쿼리별 저장본**이고, Grafana Dashboard 전체 JSON 또는 Alert rules export는 아닙니다. 실제 화면 옵션은 `../PANEL_OPTIONS_20261031.md` 참조.
