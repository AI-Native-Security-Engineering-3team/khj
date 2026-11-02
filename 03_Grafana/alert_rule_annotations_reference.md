# Alert rule의 확인된 한국어 주석 참고본 (운영 Export 아님)

- 데이터 소스: `loki`
- 조건: 동일 `client_ip`, WEB `LOGIN_FAILED` + SSH `Failed password` 최근 **10분** 합계 **5회 이상**
- Evaluation interval: 1m / Pending: 0s / Keep firing for: 0s
- Alert name: `SentinelHub - 인증 실패 5회 이상 (10분)`
- Folder: `sentinelhub` / Group: `sentinelhub_security` (화면에서 확인된 명칭)
- Contact point: `empty` (외부 알림 없음), 대시보드 Alert list 연동 확인

## Summary

```text
{{ if ge $values.A.Value 5.0 }}[SentinelHub 보안 경고]{{ else }}[SentinelHub 정상]{{ end }} IP {{ $labels.client_ip }} | 최근 10분 인증 실패 {{ printf "%.0f" $values.A.Value }}회
```

## Description

```text
{{ if ge $values.A.Value 5.0 }}반복 인증 실패가 감지되어 보안 경고가 발생했습니다.{{ else }}인증 실패 횟수가 경고 기준 미만으로 정상 상태입니다.{{ end }}

접속 IP: {{ $labels.client_ip }}
인증 실패 횟수: {{ printf "%.0f" $values.A.Value }}회
집계 범위: 최근 10분
탐지 대상: WEB 로그인 실패 + SSH 인증 실패
경고 기준: 동일 IP에서 5회 이상

{{ if ge $values.A.Value 5.0 }}권장 조치: 해당 IP의 인증 기록을 확인하고 반복적인 접근 시도를 분석하세요.{{ else }}현재 추가 조치가 필요하지 않습니다.{{ end }}
```

**검증 사례**: 정상 2회, Firing 9회, Alertmanager API에서 Firing 14회가 확인된 이력이 있습니다.
규칙 자체의 JSON/YAML 원본은 Grafana UI에서 별도 export 필요.
