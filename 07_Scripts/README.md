# SentinelHub 관리/시연 스크립트

- `collect_sentinelhub_sources.py`: Kali 운영 소스/설정을 **읽기 전용**으로 사본 수집하는 도구(기존 파일 보존).
- `SentinelHub_Attack_Demo.bat`: Windows 10/11 내부망 웹 공격 징후 **탐지 시연용** 번호 선택 메뉴. 10/31 버전, CP949/CRLF 인코딩.
- `SentinelHub_Attack_Demo_README.txt`: BAT 동작·안전한 사용법.

BAT는 내부 웹서버 `192.168.0.4:80`으로만 HTTP GET 요청을 보내도록 고정되어 있으며, 실제 취약점을 공격하거나 파일·DB를 변경하는 기능이 아닙니다. 전체 시연 요청은 제한되어 있고, 동일 IP/규칙은 60초간 중복 기록 억제가 적용됩니다.

변경한 코드/설정은 운영에 자동 적용되지 않습니다. 설치·서비스 재시작 및 Grafana 수정은 포함하지 않습니다.
