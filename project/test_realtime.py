import cv2
import requests
import time
import numpy as np
import base64

API_URL = "http://127.0.0.1:5000/verifications"

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Cannot open camera")
    exit()

last_send_time = 0
send_interval = 0  # seconds
annotated_image = None

while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to grab frame")
        break

    current_time = time.time()

    # Display the most recent annotated image if available
    display_frame = annotated_image if annotated_image is not None else frame
    cv2.imshow("Live Detection", display_frame)

    # Send a frame every `send_interval` seconds
    if current_time - last_send_time > send_interval:
        _, img_encoded = cv2.imencode(".jpg", frame)
        try:
            print("📤 Sending frame to API...")
            response = requests.post(API_URL, files={"image": img_encoded.tobytes()})
            if response.status_code == 201:
                data = response.json()

                # Decode annotated image from base64
                base64_str = data.get("annotated_image_base64")
                if base64_str:
                    decoded_bytes = base64.b64decode(base64_str)
                    nparr = np.frombuffer(decoded_bytes, np.uint8)
                    annotated_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                # Display extracted details
                if data.get("all_labels_detected") == True:
                    print("\n✅ All labels detected!")
                    print("🧠 Face Match:", data.get("face_match_result"))
                    print("🏷️ Logo Found:", data.get("logo_found"))
                    print("🔲 Pattern Count:", data.get("pattern_count"))
                    print("🔍 ID Number:", data.get("id_number"))
                    print("👤 First Name:", data.get("first_name"))
                    print("👤 Last Name:", data.get("last_name"))

                    print("🖼️ Annotated image shown. Stopping...")
                    cv2.imshow("Final Verified Frame", annotated_image)
                    cv2.waitKey(0)
                    break
                else:
                    print("⚠️ Not all labels detected.")
            else:
                print("❌ Server Error:", response.text)

        except Exception as e:
            print(f"❌ Request failed: {e}")

        last_send_time = current_time

    key = cv2.waitKey(1)
    if key == ord("q"):
        print("👋 Exiting...")
        break
    # time.sleep(0.05)
cap.release()
cv2.destroyAllWindows()
