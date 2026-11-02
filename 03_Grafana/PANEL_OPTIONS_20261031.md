# Grafana cctv 대시보드 설정 메모 (2026-10-30~31)

**자료 출처**: 대화에서 사용자가 설정·확인한 내용. 실제 Dashboard JSON 및 Alert Rule export가 없어서 그대로 가져오기(import)할 수 있는 파일은 아닙니다.

## 1. 로그 패널
- 통합 보안 로그: WEB/AUTH/SSH/Fail2Ban 기존 A~D 쿼리 유지, `E_WEB_THREAT_DETAIL_한국어.logql`을 추가.
- 기존 로그 패널: `WEB_THREAT_SHORT_한국어.logql`로 웹 공격 징후 간략 표시.
- 동일 로그를 2개 패널에서 조회해도 Loki에 이벤트가 중복 **저장**되지는 않습니다.

## 2. 웹·SSH 보안 이벤트 통계 (Bar gauge)
- Query A: `WEB_THREAT_BY_EVENT_24h.logql`; Type `Instant`.
- Query B: `SSH_FAILED_24h.logql`; Type `Instant`.
- 집계 범위: LogQL 안의 `[24h]`. 대시보드 상단 시간 선택과 별개로 최근 24시간을 집계.
- Legend만으로 `Value #A/B`가 변경되지 않아, `Overrides`에서 **Fields returned by query** 또는 **Fields with name**을 선택하고 `Standard options → Display name` 지정해 해결한 것까지 사용자 확인.
- 유형별 이름을 유지하려면 Query A의 이벤트 `event` 라벨에 따라 동적 Display name을 검토(현재 고정 Display name 사용 시 유형이 합쳐 보일 수 있음).
- Threshold는 프로젝트 시연 기준에 따라 패널별로 독립 지정.

## 3. 별도 웹 로그인 실패 게이지
- Query A: `WEB_LOGIN_FAILED_10m.logql`; Type `Instant`.
- 표시명 예: `10분간 웹로그인 실패`.
- 단일 Bar gauge는 작은 패널에서 내부 이름이 안 보일 수 있으므로 `Panel options → Title`을 지정하는 것이 확실함.
- Threshold mode를 `Absolute`로 지정하는 초기 예: `Base 0 = Green`, `1 = Orange`, `5 = Red`.
- **참고**: 이 게이지는 모든 IP의 웹 로그인 실패 합계. 기존 Alert은 **동일 IP**의 WEB+SSH 실패 합계 ≥5이므로 숫자/색상과 경고 상태가 직접 대응하지 않습니다.

## 4. 기존 인증 실패 Alert (신규 생성 아님)
- `Alerting`: WEB `LOGIN_FAILED` + SSH `Failed password`, 동일 IP 최근 10분 5회 이상.
- Evaluation 1분, Pending 0초, 연락처 `empty`, 화면은 Alert list.
- Alert list는 `Normal` 상태만 필터에서 제외하여 현재 필요한 경고 중심으로 표시.
- **10/30~31에 웹 공격 징후 전용 Alert rule을 추가로 생성하지 않았음** (설계 아이디어만 논의).

## 5. 이동 환경에서 CCTV 서버가 없을 때
- CCTV 별도 Loki 서버 `192.168.0.108:3101` 부재 시 `no route to host` 오류.
- CCTV 쿼리에 `Hide response`를 적용하면 오류 메시지는 남지만 다른 로그 갱신은 진행됨을 사용자가 실측 확인.
- CCTV 쿼리 삭제/별도 백업은 하지 않기로 결정함. 원래 환경 복귀 시 필요하면 `Hide response` 해제.
- 이 설정은 현재 Dashboard JSON이 없으므로 여기에는 **작업 기록만** 포함함.

## 6. Grafana 대시보드 전용 URL
- `&hideLogo=true`로 하단 Powered by Grafana 표시를 숨기는 방법을 사용자 확인함. 이는 서버 소스 수정이 아니라 URL 옵션이며, 환경/버전에 따라 달라질 수 있음.
