from flask import Flask, request, jsonify, send_from_directory
import os
import uuid
import cv2
import numpy as np
import base64
from verify import verify_id_image
from otp import generate_otp, verify_otp, send_otp_email, send_security_alarm

app = Flask(__name__)
RESULTS_FOLDER = "results"
os.makedirs(RESULTS_FOLDER, exist_ok=True)

verifications = {}  # Temporary in-memory store


@app.route("/verifications", methods=["POST"])
def create_verification():
    print("\nReceived POST request to /verifications")

    if "image" not in request.files:
        print("No image uploaded.")
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    img_array = np.frombuffer(file.read(), np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if frame is None:
        print("Frame could not be decoded.")
        return jsonify({"error": "Invalid image format"}), 400

    print("Image successfully decoded. Running verify_id_image...")

    try:
        result_json, annotated_image, face_crop = verify_id_image(frame)
    except Exception as e:
        print(f"Error in verify_id_image: {e}")
        return jsonify({"error": "Verification processing error"}), 500

    if annotated_image is None or not isinstance(annotated_image, np.ndarray):
        print("Invalid annotated image.")
        return jsonify({"error": "Verification failed"}), 500

    _, buffer = cv2.imencode(".jpg", annotated_image)
    result_json["annotated_image_base64"] = base64.b64encode(buffer).decode("utf-8")

    if result_json.get("all_labels_detected"):
        verification_id = str(uuid.uuid4())
        verification_folder = os.path.join(RESULTS_FOLDER, verification_id)
        os.makedirs(verification_folder, exist_ok=True)

        print(f"All labels detected. Saving to: {verification_folder}")

        # Save files, result image, face crop and text result
        cv2.imwrite(os.path.join(verification_folder, "annotated.jpg"), annotated_image)
        if face_crop is not None:
            cv2.imwrite(os.path.join(verification_folder, "face.jpg"), face_crop)
            result_json["face_image_url"] = f"/verifications/{verification_id}/face"
        else:
            result_json["face_image_url"] = None

        with open(os.path.join(verification_folder, "ocr.txt"), "w") as f:
            f.write(f"ID Number: {result_json.get('id_number', 'N/A')}\n")
            f.write(f"First Name: {result_json.get('first_name', 'N/A')}\n")
            f.write(f"Last Name: {result_json.get('last_name', 'N/A')}\n")

        with open(os.path.join(verification_folder, "log.txt"), "w") as f:
            f.write(
                f"Face Match Result: {result_json.get('face_match_result', 'N/A')}\n"
            )
            f.write(f"Logo Found: {result_json.get('logo_found', 'N/A')}\n")
            f.write(f"Pattern Count: {result_json.get('pattern_count', 'N/A')}\n")
            f.write(
                f"All Labels Detected: {result_json.get('all_labels_detected', 'N/A')}\n"
            )
            if not result_json.get("all_labels_detected"):
                f.write("Missing labels detected.\n")

        # Update JSON with download URLs
        result_json.update(
            {
                "id": verification_id,
                "annotated_image_url": f"/verifications/{verification_id}/image",
                "ocr_text_url": f"/verifications/{verification_id}/ocr.txt",
                "debug_log_url": f"/verifications/{verification_id}/log.txt",
            }
        )

        # Store in memory
        verifications[verification_id] = result_json
    else:
        print("Not all labels detected. No save.")

    print("Returning response.")
    return jsonify(result_json), 201


@app.route("/verifications/<verification_id>", methods=["GET"])
def get_verification(verification_id):
    print(f"\nGET request for verification ID: {verification_id}")
    result = verifications.get(verification_id)
    if not result:
        print("Verification not found.")
        return jsonify({"error": "Verification not found"}), 404
    return jsonify(result)


@app.route("/verifications/<verification_id>/<filename>", methods=["GET"])
def get_verification_file(verification_id, filename):
    folder = os.path.join(RESULTS_FOLDER, verification_id)
    file_path = os.path.join(folder, filename)
    if not os.path.exists(file_path):
        print(f"File not found: {filename}")
        return jsonify({"error": "File not found"}), 404
    print(f"Serving file: {filename}")
    return send_from_directory(folder, filename)


@app.route("/otp/send", methods=["POST"])
def send_otp():
    """
    Generate and send OTP to student email
    """
    data = request.get_json()
    if not data or "student_id" not in data:
        return jsonify({"success": False, "message": "Student ID is required"}), 400

    student_id = data["student_id"]

    # Validate student ID format (assuming 8 digits)
    if not student_id.isdigit() or len(student_id) != 8:
        return jsonify({"success": False, "message": "Invalid student ID format"}), 400

    # Generate OTP
    otp_code = generate_otp(student_id)

    # Send OTP via email
    success, message = send_otp_email(student_id, otp_code)

    if success:
        return (
            jsonify(
                {
                    "success": True,
                    "message": "OTP sent successfully to your student email",
                }
            ),
            200,
        )
    else:
        return (
            jsonify({"success": False, "message": f"Failed to send OTP: {message}"}),
            500,
        )


@app.route("/otp/verify", methods=["POST"])
def verify_otp_code():
    """
    Verify the OTP code provided by the student
    """
    data = request.get_json()
    if not data or "student_id" not in data or "otp_code" not in data:
        return (
            jsonify(
                {"success": False, "message": "Student ID and OTP code are required"}
            ),
            400,
        )

    student_id = data["student_id"]
    otp_code = data["otp_code"]

    # Validate student ID format
    if not student_id.isdigit() or len(student_id) != 8:
        return jsonify({"success": False, "message": "Invalid student ID format"}), 400

    # Validate OTP format (4 digits)
    if not otp_code.isdigit() or len(otp_code) != 4:
        return jsonify({"success": False, "message": "Invalid OTP format"}), 400

    # Verify OTP
    success, message = verify_otp(student_id, otp_code)

    return jsonify({"success": success, "message": message}), 200 if success else 400


@app.route("/security/alarm", methods=["POST"])
def send_security_alarm_endpoint():
    """
    Send security alarm email for unauthorized access
    """
    data = request.get_json()
    if not data or "student_id" not in data or "verification_id" not in data:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Student ID and verification ID are required",
                }
            ),
            400,
        )

    student_id = data["student_id"]
    verification_id = data["verification_id"]

    # Validate student ID format
    if not student_id.isdigit() or len(student_id) != 8:
        return jsonify({"success": False, "message": "Invalid student ID format"}), 400

    # Get the verification result
    verification_result = verifications.get(verification_id)
    if not verification_result:
        return jsonify({"success": False, "message": "Verification not found"}), 404

    # Get the path to the saved annotated image
    img_path = os.path.join(RESULTS_FOLDER, verification_id, "annotated.jpg")
    if not os.path.exists(img_path):
        return jsonify({"success": False, "message": "Annotated image not found"}), 404

    # Send security alarm with embedded image
    success, message = send_security_alarm(student_id)

    return jsonify({"success": success, "message": message}), 200 if success else 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
