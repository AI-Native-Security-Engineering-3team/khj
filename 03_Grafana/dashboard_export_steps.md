# Grafana `cctv` 대시보드 실제 JSON 내보내기

1. Grafana `SentinelHub` 폴더에서 기존 **`cctv` 대시보드** 열기.
2. 대시보드 설정 또는 공유/내보내기 메뉴에서 **Export dashboard JSON** 선택(버전별 메뉴 위치 상이).
3. 운영 데이터 소스 참조를 확인하고 JSON 파일을 저장.
4. 제출 준비본의 `03_Grafana/`에 원본 내보내기 JSON을 넣고, 내부 IP/토큰/민감 필드 검토.

> 현재 ZIP에는 사용자가 꾸민 Canvas, CCTV iframe, Logs, Table, Alert list의 실제 레이아웃을 담은 운영 Dashboard JSON이 없습니다. `queries/`는 핵심 LogQL/PromQL의 재구성 기록일 뿐 대시보드 대체물이 아닙니다.

## Alert rule 별도 Export

Grafana → Alerting → Alert rules → SentinelHub 규칙/그룹 → **Export** → JSON 또는 YAML 선택 → 파일 다운로드.
대시보드 JSON에 Grafana Alerting 규칙이 모두 포함된다고 간주하지 마세요.

Grafana 공식 문서: https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/export-alerting-resources/
