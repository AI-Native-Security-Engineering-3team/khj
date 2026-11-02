from ultralytics import YOLO

MODEL_PATH = os.getenv("YOLO_MODEL", "yolo26n.pt")
CONFIDENCE = float(os.getenv("CONFIDENCE", "0.5"))
AI_WIDTH = int(os.getenv("AI_WIDTH", "640"))
YOLO_IMGSZ = int(os.getenv("YOLO_IMGSZ", "320"))
PERSON_CLASS_ID = 0

def ai_loop():
    try:
        import torch
        torch.set_num_threads(AI_THREADS)
    except Exception:
        pass
    model = YOLO(MODEL_PATH)
    engine = FaceEngine()
    ...

        h, w = frame.shape[:2]
        scale = w / AI_WIDTH if w > AI_WIDTH else 1.0
        small = cv2.resize(frame, (int(w / scale), int(h / scale))) if scale > 1 else frame

        result = model(small, classes=[PERSON_CLASS_ID], conf=CONFIDENCE, imgsz=YOLO_IMGSZ, verbose=False)[0]
        persons = [tuple(int(v * scale) for v in b.xyxy[0].tolist()) for b in result.boxes]
        ...

        for p in persons:
            is_suspect = any(center_inside(fb, p) for fb in suspect_faces)
            color = RED if is_suspect else GREEN
            label = "SUSPECT" if is_suspect else "VISITOR"
            cv2.rectangle(frame, (p[0], p[1]), (p[2], p[3]), color, thick)
            cv2.putText(frame, label, (p[0], max(p[1] - 10, 24)), cv2.FONT_HERSHEY_SIMPLEX, font, color, 2)
