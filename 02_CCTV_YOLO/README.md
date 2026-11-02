# SentinelHub CCTV — FastAPI · YOLO 코드 설명

웹캠 영상에서 **등록된 범인**을 찾아 경보하고, 일반인 얼굴은 자동으로 블러 처리하는 CCTV 서버의 핵심 코드입니다.
전체 코드(`main.py`)에서 **FastAPI**와 **YOLO**를 사용하는 부분만 꺼내 두 파일로 나눴습니다.

- 전체 저장소: https://github.com/rjs2317/sentinel-cctv (v10, 2026-10-29)
- 팀 프로젝트: SentinelHub (Grafana · Prometheus · Loki 기반 사이버·물리 융합 보안관제)

> FastAPI와 YOLO **라이브러리 자체의 코드**는 들어 있지 않습니다. 둘 다 `pip install`로 설치해서 쓰고,
> 이 코드는 **우리 CCTV가 두 라이브러리를 어떻게 연결해서 구성했는지**를 보여줍니다.

---

## 파일 구성

| 파일 | 내용 |
|---|---|
| `README.md` | 이 설명서 |
| `01_fastapi_code.py` | FastAPI 사용 코드: 웹 서버, 영상 스트리밍, 버튼 API |
| `02_yolo_code.py` | YOLO 사용 코드: 사람 찾기, 박스 그리기 |

두 파일은 `main.py`에서 잘라낸 발췌본이라 **단독으로는 실행되지 않습니다.** `...`는 중간을 생략한 곳입니다.
실행은 전체 저장소에서 합니다(아래 "실행 방법").

---

## 전체 동작 흐름

```
웹캠 ──▶ [카메라 스레드] OpenCV로 최신 화면만 보관
              │
              ├──▶ [AI 스레드]  YOLO로 사람 찾기 ──▶ YuNet으로 얼굴 찾기 ──▶ SFace로 범인과 비교
              │                  (02_yolo_code.py)         연속 2번 일치하면 경보
              │
              └──▶ [화면 스레드] 박스 · 일반인 얼굴 블러 · 빨간 테두리를 그려 JPEG로
                                        │
                                        ▼
                         FastAPI 웹 서버 (01_fastapi_code.py)
                         /video  /embed  /status  /enroll  /camera/on|off
                                        │
                                        ▼
                     관리자 페이지 · Grafana CCTV 패널 (브라우저)
```

| 역할 | 사용 기술 |
|---|---|
| 웹 서버 · 영상 전송 · 버튼 API | **FastAPI** (+ uvicorn) |
| 카메라 읽기 · 그리기 · 블러 | OpenCV |
| 사람 찾기 | **YOLO** (ultralytics, `yolo26n.pt`) |
| 얼굴 찾기 · 범인 판별 | OpenCV YuNet + SFace |

> 범인인지 판단하는 건 YOLO가 아니라 얼굴 인식 모델(YuNet + SFace)입니다. YOLO는 "사람이 어디 있는지"만 찾습니다.

---

## 1. FastAPI 코드 (`01_fastapi_code.py`)

FastAPI는 CCTV를 **웹 서버**로 만들어 줍니다.

### 코드 순서

| 순서 | 코드 | main.py 위치 | 하는 일 |
|---|---|---|---|
| ① | `from fastapi import ...` | 28~29줄 | FastAPI 불러오기 |
| ② | `lifespan()` | 483~499줄 | 서버가 켜질 때 카메라 · 화면 · AI 스레드 3개 실행 |
| ③ | `app = FastAPI(...)` | 501줄 | 웹 서버(앱) 만들기 |
| ④ | `mjpeg_stream()` | 507~518줄 | 새 화면이 생겼을 때만 JPEG를 이어 보내기 |
| ⑤ | `@app.get(...)` / `@app.post(...)` | 521~625줄 | 주소별 처리 (아래 표) |

### 주소(엔드포인트)

| 방식 | 주소 | 하는 일 |
|---|---|---|
| GET | `/` | 관리자 페이지 (카메라 켜기/끄기, 범인 등록, 경보 기록) |
| GET | `/embed` | Grafana 패널에 넣는 관제 화면 |
| GET | `/alarm-sound` | 경보음 파일 |
| GET | `/video` | 실시간 영상 (MJPEG 스트리밍) |
| GET | `/status` | 현재 상태 JSON (경보 여부, 사람 수, 버전 등) |
| POST | `/enroll` | 지금 화면의 얼굴을 범인으로 등록 (사진 대신 특징값만 저장) |
| POST | `/enroll/reset` | 범인 등록 초기화 |
| POST | `/camera/on` · `/camera/off` | 카메라 켜기 / 끄기 |
| GET | `/metrics` | Prometheus 지표 |

### 핵심 포인트

- **스레드 3개 구조**: 카메라 · AI · 화면을 따로 돌려서, AI가 느려도 영상은 밀리지 않습니다.
- **새 화면만 전송**: `mjpeg_stream()`이 같은 화면을 반복해서 보내지 않아 지연이 쌓이지 않습니다.
- `StreamingResponse`로 JPEG를 이어 보내서, 브라우저에서는 `<img src="/video">` 하나로 실시간 영상처럼 보입니다.
- 실행 명령: `uvicorn main:app --host 0.0.0.0 --port 5001` (Dockerfile에 들어 있음)

---

## 2. YOLO 코드 (`02_yolo_code.py`)

YOLO는 화면에서 **사람의 위치**를 박스로 찾습니다.

### 코드 순서

| 순서 | 코드 | main.py 위치 | 하는 일 |
|---|---|---|---|
| ① | `from ultralytics import YOLO` | 31줄 | YOLO 불러오기 |
| ② | `MODEL_PATH`, `CONFIDENCE` 등 | 48~49, 61~62, 80줄 | 설정값 |
| ③ | `model = YOLO(MODEL_PATH)` | `ai_loop()` 시작 부분 | 모델 불러오기 |
| ④ | `model(small, classes=[0], ...)` | `ai_loop()` 안 | 화면을 줄여서 사람만 찾고, 박스를 원래 크기로 되돌리기 |
| ⑤ | `for p in persons:` | `render_loop()` 안 | 범인이면 빨간 `SUSPECT`, 아니면 초록 `VISITOR` 박스 그리기 |

### 설정값 (`docker-compose.yml`에서 코드 수정 없이 변경)

| 설정 | 값 | 의미 |
|---|---|---|
| `YOLO_MODEL` | `yolo26n.pt` | 사용할 YOLO 모델 (가벼운 nano 모델, CPU에서 동작) |
| `CONFIDENCE` | 0.5 | 이 확신도 이상만 사람으로 인정 |
| `AI_WIDTH` | 640 | AI 판별용으로 줄이는 화면 폭 (속도용) |
| `YOLO_IMGSZ` | 320 | YOLO 입력 크기 (낮을수록 빠름) |
| `PERSON_CLASS_ID` | 0 | YOLO에서 0번 = 사람 |

### 핵심 포인트

- 사람이 없으면 얼굴 모델을 돌리지 않습니다. YOLO가 먼저 걸러줘서 CPU를 아낍니다.
- `torch.set_num_threads()`로 AI가 쓰는 CPU 코어 수를 제한해서 영상이 끊기지 않게 했습니다.
- 모델 파일(`yolo26n.pt`)은 Docker 빌드 때 미리 내려받아 둡니다.

---

## 실행 방법 (전체 저장소 기준, Kali Linux)

```bash
git clone https://github.com/rjs2317/sentinel-cctv.git
cd sentinel-cctv
sudo docker compose up -d --build
# 브라우저: http://<Kali IP>:5001   (Grafana 패널용: /embed)
```

설치되는 라이브러리 (`requirements.txt`)

```
fastapi
uvicorn[standard]
opencv-python
ultralytics
prometheus-client
```

---

## 개인정보 보호

- 일반인 얼굴은 서버에서 **블러 처리한 뒤** 화면으로 내보냅니다.
- 범인 등록 시 **사진 원본은 저장하지 않고** 얼굴 특징값(숫자)만 저장합니다.
- 로그에는 실명 대신 가명 ID(`suspect-01`)만 남습니다.
- 얼굴 특징값(`*.npy`)과 로그는 GitHub에 올리지 않습니다.
- 내부망 실습용이며, 촬영과 얼굴 등록은 동의한 팀원만 대상으로 합니다.
