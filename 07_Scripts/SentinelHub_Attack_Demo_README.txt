SentinelHub 웹 보안 탐지 시연 v1.0 — 사용 안내
=============================================

1. 사용 방법
- Windows 10/11 PC에서 SentinelHub_Attack_Demo.bat를 더블클릭합니다.
- 관리자 권한은 필요하지 않습니다.
- 같은 내부 LAN에서 Kali Purple 웹서버(192.168.0.4)에 접근 가능해야 합니다.
- Windows의 curl.exe 및 choice.exe를 사용합니다.
- 파일 인코딩: CP949, 줄바꿈: CRLF (한국어 CMD 출력용).

2. 메뉴 / 요청 횟수
[1] 연결 상태: /api/health 1회
[2] 민감 경로: /.env 1회 + 연결 검사 1회
[3] 서로 다른 404 경로: 5회 + 연결 검사 1회
[4] SQLi 의심 구문: GET /api/health?q=UNION+SELECT 1회 + 연결 검사 1회
[5] XSS 의심 구문: GET /api/health?q=javascript:demo 1회 + 연결 검사 1회
[6] 전체 자동 실행: 탐지용 GET 8회 + 연결 검사 1회(최대 9회)
[0] 종료

3. 안전 설계
- 대상은 sentinelhub.com:80을 192.168.0.4로 강제 연결합니다(--resolve).
- 프록시를 우회하고(--noproxy '*'), 다른 사이트로 리디렉션을 따라가지 않습니다.
- 테스트 요청은 HTTP GET이며 로그인 비밀번호 대입/SSH 요청/서버 파일 변경/대량 요청을 수행하지 않습니다.
- SQLi/XSS 시연 문자열은 /api/health의 무해한 쿼리 파라미터로만 전달됩니다.
  실제 데이터베이스 쿼리나 브라우저 스크립트가 실행되는 방식이 아닙니다.
- 각 요청은 연결 3초/전체 8초 타임아웃을 적용합니다.
- 전체 시연은 매우 제한된 요청 수를 사용합니다. 강제 초당 요청 폭주 시연은 제외했습니다.
- User-Agent: SentinelHub-Detection-Demo/1.0 (Nginx 접근 로그 식별 가능)

4. 예상 HTTP 코드
- /api/health: 200
- /.env: 404
- /__sentinelhub_demo_missing_01__ ~ 05__: 404
- SQLi/XSS 문자열을 붙인 /api/health: 200

5. Grafana 확인
- 기존 통합 로그 또는 웹 공격 징후 로그 패널에서 job=sentinelhub-web-threat 조회.
- 예상 탐지 규칙: WEB_SENSITIVE_PATH, WEB_404_ENUMERATION,
  WEB_SQLI_SUSPECTED, WEB_XSS_SUSPECTED.
- 한 요청에서 여러 규칙이 일치하면 JSONL 한 행에 통합될 수 있습니다.
- 동일 IP/동일 탐지 규칙은 60초간 중복 기록이 억제되어 연속 실행 시
  로그가 즉시 추가되지 않을 수 있습니다. 로그 수집/Grafana 표시도 갱신 주기의 영향을 받습니다.
- 이 테스트 로그는 실습 중 의도적으로 발생시킨 이벤트로, 실제 침해의 증거가 아닙니다.

6. 적용 범위
- Kali Purple의 main.py / Nginx / Alloy / Loki / Grafana 설정 변경 없음.
- 현재 설치된 web_threat_detector.py의 탐지 규칙을 확인한 뒤 생성했습니다.
- SHA 및 ZIP 무결성 검증을 거쳤습니다. 다만 실제 Windows CMD에서 실행한 결과는
  별도로 검증되지 않았으므로 최초에는 [1] 연결 확인 후 [2] 단일 탐지를 권장합니다.
