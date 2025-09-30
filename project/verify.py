import cv2
import torch
import numpy as np
import mediapipe as mp
from facenet_pytorch import InceptionResnetV1
from ultralytics import YOLO
import torch.nn.functional as F
import pytesseract
import re
from draw_utils import draw_bounding_box, class_colors

# Set Tesseract path if necessary
pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"

# Setup device
device = "cuda" if torch.cuda.is_available() else "cpu"

# Initialize models
facenet = InceptionResnetV1(pretrained="vggface2").eval().to(device)
yolo_model = YOLO("models/best.pt")
mp_face_detection = mp.solutions.face_detection
face_detector = mp_face_detection.FaceDetection(min_detection_confidence=0.6)
FACE_MATCH_THRESHOLD = 0.6


def boxes_overlap(boxA, boxB):
    ax, ay, aw, ah = boxA
    bx, by, bw, bh = boxB
    return not (ax + aw < bx or bx + bw < ax or ay + ah < by or by + bh < ay)


def extract_text_from_bbox(image, bbox):
    x1, y1, x2, y2 = bbox
    roi = image[y1:y2, x1:x2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray).strip()
    return re.sub(r"[^a-zA-Z0-9\s]", "", text)


def extract_face(frame, bbox):
    x, y, w, h = bbox
    face = frame[y : y + h, x : x + w]
    if face.size == 0 or face.shape[0] < 10 or face.shape[1] < 10:
        return None
    try:
        face = cv2.resize(face, (160, 160))
    except cv2.error:
        return None
    face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
    face = face.astype(np.float32) / 255.0
    face = (face - 0.5) / 0.5
    face = np.transpose(face, (2, 0, 1))
    return torch.tensor(face).unsqueeze(0).to(device)


def get_embedding(face_tensor):
    with torch.no_grad():
        return facenet(face_tensor)


def compute_similarity(emb1, emb2):
    return F.cosine_similarity(emb1, emb2).item()


def verify_id_image(frame):
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    display_frame = frame.copy()

    yolo_results = yolo_model(frame, imgsz=320, conf=0.5)[0]
    boxes = yolo_results.boxes.xyxy.cpu().numpy()
    classes = yolo_results.boxes.cls.cpu().numpy().astype(int)
    detected_classes = set(classes)

    if 1 in detected_classes:
        for box, cls in zip(boxes, classes):
            if cls == 1:
                x1, y1, x2, y2 = map(int, box)
                draw_bounding_box(
                    display_frame,
                    (x1, y1, x2 - x1, y2 - y1),
                    "Please show valid ID",
                    class_colors[1],
                )
        return display_frame, {"error": "Other ID detected"}

    logo_found = 6 in detected_classes
    pattern_count = sum(1 for c in classes if c == 5)
    uts_id_bbox = None
    id_number_text, first_name_text, last_name_text = "", "", ""

    for box, cls in zip(boxes, classes):
        x1, y1, x2, y2 = map(int, box)
        w, h = x2 - x1, y2 - y1
        label = ""
        color = class_colors.get(cls, (255, 255, 255))

        if cls == 0:
            label = "UTS ID"
            uts_id_bbox = (x1, y1, w, h)
        elif cls == 2:
            label = "ID Number"
            id_number_text = extract_text_from_bbox(frame, (x1, y1, x2, y2))
            label += f": {id_number_text}"
        elif cls == 3:
            label = "First Name"
            first_name_text = extract_text_from_bbox(frame, (x1, y1, x2, y2))
            label += f": {first_name_text}"
        elif cls == 4:
            label = "Last Name"
            last_name_text = extract_text_from_bbox(frame, (x1, y1, x2, y2))
            label += f": {last_name_text}"
        elif cls == 5:
            label = "Pattern"
        elif cls == 6:
            label = "Logo"

        if label:
            draw_bounding_box(display_frame, (x1, y1, w, h), label, color)

    real_face_bbox = None
    id_face_bbox = None

    if uts_id_bbox is not None:
        x, y, w, h = uts_id_bbox
        id_crop = frame[y : y + h, x : x + w]
        id_crop_rgb = cv2.cvtColor(id_crop, cv2.COLOR_BGR2RGB)
        id_result = face_detector.process(id_crop_rgb)
        if id_result.detections:
            ih, iw, _ = id_crop.shape
            bboxC = id_result.detections[0].location_data.relative_bounding_box
            fx = int(bboxC.xmin * iw)
            fy = int(bboxC.ymin * ih)
            fw = int(bboxC.width * iw)
            fh = int(bboxC.height * ih)
            if fw > 0 and fh > 0:
                id_face_bbox = (x + fx, y + fy, fw, fh)

    results = face_detector.process(frame_rgb)
    ih, iw, _ = frame.shape
    if results.detections:
        for detection in results.detections:
            bboxC = detection.location_data.relative_bounding_box
            x = int(bboxC.xmin * iw)
            y = int(bboxC.ymin * ih)
            w = int(bboxC.width * iw)
            h = int(bboxC.height * ih)
            if uts_id_bbox is None or not boxes_overlap((x, y, w, h), uts_id_bbox):
                real_face_bbox = (x, y, w, h)
                break

    face_match_result = "incomplete"
    face_match_exist = False
    if real_face_bbox and id_face_bbox:
        face1_tensor = extract_face(frame, real_face_bbox)
        face2_tensor = extract_face(frame, id_face_bbox)
        if face1_tensor is not None and face2_tensor is not None:
            emb1 = get_embedding(face1_tensor)
            emb2 = get_embedding(face2_tensor)
            similarity = compute_similarity(emb1, emb2)
            match_text = "match" if similarity > FACE_MATCH_THRESHOLD else "no match"
            face_match_result = match_text
            face_match_exist = True
            color = (0, 255, 0) if similarity > FACE_MATCH_THRESHOLD else (0, 0, 255)
            draw_bounding_box(display_frame, real_face_bbox, match_text, color)
            draw_bounding_box(display_frame, id_face_bbox, match_text, color)
    elif real_face_bbox:
        draw_bounding_box(display_frame, real_face_bbox, "Need ID face", (0, 165, 255))
    elif id_face_bbox:
        draw_bounding_box(display_frame, id_face_bbox, "Need real face", (0, 165, 255))

    summary_text = (
        f"Logo: {'Yes' if logo_found else 'No'}, Pattern: {pattern_count} Found"
    )
    summary_color = (
        (0, 255, 0)
        if pattern_count >= 2
        else (0, 255, 255) if pattern_count == 1 else (0, 0, 255)
    )
    cv2.putText(
        display_frame,
        summary_text,
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        summary_color,
        2,
    )

    # Check if all labels are detected (logo, pattern, face match, face present)
    # Also the labels for id_num, fisrt and last name can not be null
    # Determine label detection status
    all_labels_detected = (
        logo_found
        and pattern_count >= 1
        and face_match_exist == True
        and real_face_bbox is not None
        and id_number_text.strip() != ""
        and first_name_text.strip() != ""
        and last_name_text.strip() != ""
    )

    # Determine if verification passes all strict criteria
    verification_valid = (
        face_match_result == "match" and logo_found and pattern_count == 2
    )

    # Collect failure reasons (for retry feedback)
    failure_reasons = []
    if face_match_result != "match":
        failure_reasons.append("Face does not match")

    if pattern_count < 2:
        failure_reasons.append("Less than 2 patterns found")

    # Extract cropped face image from real_face_bbox if available
    # we want to save this to the databasae so next time, if
    # someone is checked and already saved in the database
    # the system would check that frame, and see if they have been
    # checked by comparing information and face

    face_crop = None
    if real_face_bbox:
        x, y, w, h = real_face_bbox
        face_crop = frame[y : y + h, x : x + w]

    # Return result
    return (
        {
            "id_number": id_number_text,
            "first_name": first_name_text,
            "last_name": last_name_text,
            "logo_found": logo_found,
            "pattern_count": pattern_count,
            "face_match_result": face_match_result,
            "all_labels_detected": all_labels_detected,
            "verification_valid": verification_valid,
            "failure_reasons": failure_reasons,
        },
        display_frame,
        face_crop,
    )
