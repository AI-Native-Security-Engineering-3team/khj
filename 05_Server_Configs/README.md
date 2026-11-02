# 인프라 설정 파일 확보 대상

기존에 설치된 설정의 **원본**을 Kali에서 추출해야 합니다. 이 ZIP의 Prometheus YAML은 대화 기반 재구성본입니다.

- BIND9: `/etc/bind/named.conf.options`, `/etc/bind/named.conf.local`, `/etc/bind/db.sentinelhub.com`
- Nginx: `/etc/nginx/sites-available/default` (메인 FastAPI와 Grafana의 도메인 분리)
- Prometheus: `/etc/prometheus/prometheus.yml` (node exporter 5초 수집)

기본 운영 주소:
- `sentinelhub.com` → 내부 Kali 192.168.0.4 → Nginx → FastAPI 127.0.0.1:8000
- `grafana.sentinelhub.com` → 내부 Kali 192.168.0.4 → Nginx → Grafana 127.0.0.1:3000
- `cctv.sentinelhub.com` 실제 프록시 여부는 원본 확인 필요; 팀원 CCTV 192.168.0.108:5001 표시 이력

> 수정된 실제 설정을 추출하되, 비밀값이 있을 수 있으므로 제출하기 전 검토합니다.
