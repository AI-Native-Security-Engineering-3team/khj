# SentinelHub 보안관제 구성도 (2026-10-31)

```text
Windows 관리자 PC 192.168.0.3
        │   내부 LAN / BIND9 sentinelhub.com
        ▼
Kali Purple VM 192.168.0.4
 ├── Nginx :80
 │   ├── sentinelhub.com → FastAPI :8000 (루프백, 1 worker)
 │   │   ├── SQLite 계정 / 로그인 / 세션
 │   │   ├── security-events.jsonl (AUTH)
 │   │   └── web-threat-events.jsonl (웹 의심 요청)
 │   └── grafana.sentinelhub.com → Grafana :3000
 ├── Prometheus + Node Exporter (시스템 CPU·RAM·네트워크)
 ├── Alloy → Loki :3100 → Grafana (WEB/AUTH/SSH/Fail2Ban/WEB THREAT)
 └── Fail2Ban sshd → nftables (수동 ban/unban 검증)

별도 팀원 CCTV 서버 192.168.0.108:5001 (상황에 따라 이동 시 부재)
 ├── FastAPI 웹 영상 / YOLO 사람 탐지 (팀원 코드 발췌본 제공)
 └── Loki :3101 / Grafana CCTV 및 이벤트 연동 (사용자 보고)
```

Grafana 통합·상세 Logs, 보안 사건 통계 Bar gauge 및 WEB+SSH 인증 실패 5회 이상 Alert list를 운영. CCTV 서버 미연결 시 Hide response 사용 실측. 팀원 CCTV 전체 소스/실제 운영 Dashboard JSON은 이 패키지에 없음.
