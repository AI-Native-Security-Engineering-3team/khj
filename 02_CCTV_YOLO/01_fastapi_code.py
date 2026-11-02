from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    global grabber
    suspect_embeddings.extend(load_embeddings())
    M_ENROLLED.set(len(suspect_embeddings))
    M_CAM_ENABLED.set(1 if CAMERA_ON_START else 0)
    with state_lock:
        state["jpeg"] = placeholder("LOADING AI MODELS...")
    grabber = FrameGrabber(enabled=CAMERA_ON_START)
    threading.Thread(target=render_loop, daemon=True).start()
    threading.Thread(target=ai_loop, daemon=True).start()
    if LOKI_URL:
        threading.Thread(target=loki_worker, daemon=True).start()
    print(f"SentinelHub CCTV {APP_VERSION}", flush=True)
    write_event("server_start", version=APP_VERSION.split()[0])
    yield


app = FastAPI(title="SentinelHub CCTV", lifespan=lifespan)
enroll_lock = threading.Lock()
enroll_engine = None
grabber: "FrameGrabber | None" = None


def mjpeg_stream():
    last = -1
    while True:
        with state_lock:
            seq, jpg = state["seq"], state["jpeg"]
        if jpg and seq != last:
            last = seq
            yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                   + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n")
        else:
            time.sleep(0.01)


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "static" / "index.html",
                        headers={"Cache-Control": "no-store"})


@app.get("/embed")
def embed():
    return FileResponse(BASE_DIR / "static" / "embed.html",
                        headers={"Cache-Control": "no-store"})


ALARM_TYPES = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg", ".m4a": "audio/mp4"}


@app.get("/alarm-sound")
def alarm_sound():
    for ext, mime in ALARM_TYPES.items():
        path = BASE_DIR / "static" / f"alarm{ext}"
        if path.exists():
            return FileResponse(path, media_type=mime, headers={"Cache-Control": "no-store"})
    return JSONResponse({"ok": False, "message": "static 폴더에 alarm.mp3 파일이 없습니다."}, status_code=404)


@app.get("/video")
def video():
    return StreamingResponse(mjpeg_stream(), media_type="multipart/x-mixed-replace; boundary=frame",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@app.get("/status")
def status():
    with state_lock:
        return {
            "version": APP_VERSION,
            "alert": state["alert"],
            "person_count": state["person_count"],
            "visitor_count": state["visitor_count"],
            "camera_ok": state["camera_ok"],
            "camera_enabled": bool(grabber and grabber.enabled),
            "resolution": state["resolution"],
            "enrolled": len(suspect_embeddings),
            "last_event": state["last_event"],
            "loki": loki_status["state"],
            "loki_error": loki_status["error"],
        }


@app.post("/enroll")
def enroll():
    global enroll_engine
    ok, _, frame = grabber.read() if grabber else (False, 0, None)
    if not ok:
        return JSONResponse({"ok": False, "message": "카메라가 꺼져 있거나 영상이 아직 없습니다."}, status_code=400)
    h, w = frame.shape[:2]
    scale = w / AI_WIDTH if w > AI_WIDTH else 1.0
    small = cv2.resize(frame, (int(w / scale), int(h / scale))) if scale > 1 else frame
    with enroll_lock:
        if enroll_engine is None:
            enroll_engine = FaceEngine()
        faces = enroll_engine.detect(small)
        if len(faces) != 1:
            return JSONResponse({"ok": False,
                                 "message": f"얼굴이 {len(faces)}개 보입니다. 1명만 정면으로 보이게 해주세요."},
                                status_code=400)
        feat = enroll_engine.embed(small, faces[0])
    with state_lock:
        suspect_embeddings.append(feat)
        save_embeddings(suspect_embeddings)
        n = len(suspect_embeddings)
    M_ENROLLED.set(n)
    write_event("suspect_enrolled", subject=SUSPECT_ID, templates=n)
    return {"ok": True, "templates": n}


@app.post("/enroll/reset")
def enroll_reset():
    with state_lock:
        suspect_embeddings.clear()
        save_embeddings(suspect_embeddings)
    M_ENROLLED.set(0)
    write_event("suspect_enrollment_reset", subject=SUSPECT_ID)
    return {"ok": True, "templates": 0}


@app.post("/camera/{action}")
def camera_control(action: str):
    if action not in ("on", "off"):
        return JSONResponse({"ok": False, "message": "on 또는 off만 가능합니다."}, status_code=400)
    on = action == "on"
    if grabber.enabled != on:
        grabber.set_enabled(on)
        M_CAM_ENABLED.set(1 if on else 0)
        write_event("camera_on" if on else "camera_off")
    return {"ok": True, "camera_enabled": on}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
