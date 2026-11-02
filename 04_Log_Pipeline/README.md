# SentinelHub 로그 파이프라인 — 2026-10-31 소스 정리

| Loki Job | 수집 원본 |
|---|---|
| `sentinelhub-auth` | `/var/log/sentinelhub/security-events.jsonl` |
| `sentinelhub-web` | `/var/log/nginx/sentinelhub-access.log` |
| `sentinelhub-ssh` | systemd journal (`ssh.service`) |
| `sentinelhub-fail2ban` | `/var/log/fail2ban.log` |
| `sentinelhub-web-threat` | `/var/log/sentinelhub/web-threat-events.jsonl` — 신규 |

새 파일 권한: `kali:alloy` 640, 디렉터리 2750. 기존 auth 로그 파일·그룹·권한을 변경하지 않습니다.

**중요**: 패키지의 `config.alloy`는 이번 ZIP에 들어 있던 과거 설정에 10/30의 신규 수집 블록을 **추가한 재구성 통합본**입니다. 사용자 보고에 따르면 운영 서버에서는 신규 Loki Job 및 Grafana 표시가 정상 동작했지만, **실제 현재 `/etc/alloy/config.alloy` 원본을 재수집한 것은 아닙니다**. 이 파일을 운영 서버에 그대로 덮어쓰지 마세요. `WEB_THREAT_ONLY.alloy`도 비교 자료입니다.
