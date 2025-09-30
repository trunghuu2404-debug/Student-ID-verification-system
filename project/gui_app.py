import customtkinter as ctk
import cv2
import requests
import numpy as np
import base64
from PIL import Image, ImageTk
import json
import threading
import time
from datetime import datetime
from excel_logger import VerificationLogger
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# SMTP Configuration
SMTP_SERVER = "smtp.gmail.com"  # Gmail SMTP server
SMTP_PORT = 587  # TLS port for Gmail

# Configure customtkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class VerificationApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("UTS Library Access Verification")
        self.geometry("1200x800")

        # Initialize variables
        self.cap = None
        self.is_capturing = False
        self.current_frame = None
        self.verification_result = None
        self.api_url = "http://127.0.0.1:5000"
        self.logger = VerificationLogger()
        self.annotated_image = None

        # Create main container
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Initialize camera view
        self.setup_camera_view()

    def setup_camera_view(self):
        """Setup the initial camera view with Start button"""
        # Clear main container
        for widget in self.main_container.winfo_children():
            widget.destroy()

        # Create camera frame
        self.camera_frame = ctk.CTkFrame(self.main_container)
        self.camera_frame.pack(side="left", fill="both", expand=True, padx=10)

        # Create camera label
        self.camera_label = ctk.CTkLabel(self.camera_frame, text="")
        self.camera_label.pack(fill="both", expand=True)

        # Create control frame
        control_frame = ctk.CTkFrame(self.main_container)
        control_frame.pack(side="right", fill="y", padx=10)

        # Create Start button
        self.start_button = ctk.CTkButton(
            control_frame, text="Start", command=self.toggle_capture
        )
        self.start_button.pack(pady=20)

        # Start camera
        self.start_camera()

    def setup_otp_view(self, student_id):
        """Setup the OTP verification view"""
        # Clear main container
        for widget in self.main_container.winfo_children():
            widget.destroy()

        # Create OTP frame
        otp_frame = ctk.CTkFrame(self.main_container)
        otp_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Add title
        title_label = ctk.CTkLabel(
            otp_frame, text="OTP Verification", font=("Arial", 24, "bold")
        )
        title_label.pack(pady=20)

        # Add message
        msg_label = ctk.CTkLabel(
            otp_frame,
            text=f"An OTP has been sent to {student_id}@student.uts.edu.au\nPlease enter the 4-digit code:",
            font=("Arial", 16),
        )
        msg_label.pack(pady=20)

        # Add OTP entry
        self.otp_entry = ctk.CTkEntry(otp_frame, width=200)
        self.otp_entry.pack(pady=20)

        # Add buttons frame
        buttons_frame = ctk.CTkFrame(otp_frame)
        buttons_frame.pack(pady=20)

        # Add Verify button
        verify_button = ctk.CTkButton(
            buttons_frame,
            text="Verify",
            command=lambda: self.verify_otp(student_id),
        )
        verify_button.pack(side="left", padx=10)

        # Add Back button
        back_button = ctk.CTkButton(
            buttons_frame,
            text="Back",
            command=self.setup_camera_view,
        )
        back_button.pack(side="left", padx=10)

    def setup_result_view(self, result_json, annotated_image):
        """Setup the view showing verification results"""
        # Clear main container
        for widget in self.main_container.winfo_children():
            widget.destroy()

        # Create result frame
        result_frame = ctk.CTkFrame(self.main_container)
        result_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Show annotated image
        img = Image.fromarray(cv2.cvtColor(annotated_image, cv2.COLOR_BGR2RGB))
        img = self.resize_image(img, 800, 600)
        photo = ImageTk.PhotoImage(img)

        image_label = ctk.CTkLabel(result_frame, image=photo, text="")
        image_label.image = photo
        image_label.pack(pady=20)

        # Show results text
        results_text = f"""
        Face Match: {result_json.get('face_match_result', 'N/A')}
        Logo Found: {result_json.get('logo_found', 'N/A')}
        Pattern Count: {result_json.get('pattern_count', 'N/A')}
        ID Number: {result_json.get('id_number', 'N/A')}
        Name: {result_json.get('first_name', 'N/A')} {result_json.get('last_name', 'N/A')}
        """
        text_label = ctk.CTkLabel(result_frame, text=results_text, font=("Arial", 16))
        text_label.pack(pady=20)

        # Add buttons frame
        buttons_frame = ctk.CTkFrame(result_frame)
        buttons_frame.pack(pady=20)

        student_id = result_json.get("id_number", "")
        verification_valid = result_json.get("verification_valid", False)

        if verification_valid:
            # Add Send OTP button
            otp_button = ctk.CTkButton(
                buttons_frame,
                text="Send OTP",
                command=lambda: self.send_otp(student_id),
            )
            otp_button.pack(side="left", padx=10)
        else:
            # Add Send Alarm button
            alarm_button = ctk.CTkButton(
                buttons_frame,
                text="Send Alarm",
                command=lambda: self.send_alarm(student_id, annotated_image),
            )
            alarm_button.pack(side="left", padx=10)

        # Add Back button
        back_button = ctk.CTkButton(
            buttons_frame,
            text="Back",
            command=self.setup_camera_view,
        )
        back_button.pack(side="left", padx=10)

    def start_camera(self):
        """Initialize and start the camera"""
        if self.cap is None:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("Cannot open camera")
                return

        # Start update loop
        self.update_camera()

    def update_camera(self):
        """Update camera feed"""
        if self.cap is not None:
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
                # Display frame
                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(img)
                img = self.resize_image(img, 800, 600)
                photo = ImageTk.PhotoImage(img)
                self.camera_label.configure(image=photo)
                self.camera_label.image = photo

                # If capturing is active, send frame to API
                if self.is_capturing:
                    self.send_frame_to_api(frame)

            # Schedule next update
            self.after(10, self.update_camera)

    def toggle_capture(self):
        """Toggle frame capture and sending to API"""
        self.is_capturing = not self.is_capturing
        self.start_button.configure(text="Stop" if self.is_capturing else "Start")

    def send_frame_to_api(self, frame):
        """Send frame to verification API"""
        try:
            # Encode frame as JPEG
            _, img_encoded = cv2.imencode(".jpg", frame)

            # Send to API
            response = requests.post(
                f"{self.api_url}/verifications", files={"image": img_encoded.tobytes()}
            )

            if response.status_code == 201:
                result_json = response.json()

                # If all labels detected, show results
                if result_json.get("all_labels_detected", False):
                    self.is_capturing = False
                    # Get annotated image from base64
                    img_data = base64.b64decode(result_json["annotated_image_base64"])
                    nparr = np.frombuffer(img_data, np.uint8)
                    annotated_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    # Store the result and image for later use
                    self.verification_result = result_json
                    self.annotated_image = annotated_image

                    # Show results view
                    self.setup_result_view(result_json, annotated_image)

        except Exception as e:
            print(f"Error sending frame to API: {e}")

    def send_otp(self, student_id):
        """Send OTP to student email"""
        try:
            response = requests.post(
                f"{self.api_url}/otp/send", json={"student_id": student_id}
            )

            if response.status_code == 200:
                # Show OTP verification view
                self.setup_otp_view(student_id)
            else:
                print(f"Error sending OTP: {response.json()['message']}")

        except Exception as e:
            print(f"Error sending OTP: {e}")

    def verify_otp(self, student_id):
        """Verify entered OTP"""
        otp_code = self.otp_entry.get()
        try:
            response = requests.post(
                f"{self.api_url}/otp/verify",
                json={"student_id": student_id, "otp_code": otp_code},
            )

            if response.status_code == 200 and response.json()["success"]:
                # Log the successful verification with image
                self.logger.log_successful_verification(
                    self.verification_result, self.annotated_image, otp_verified=True
                )
                # Show success message and return to camera view
                self.show_message("Success", "Access granted!")
                self.setup_camera_view()
            else:
                self.show_message("Error", "Invalid OTP code")

        except Exception as e:
            print(f"Error verifying OTP: {e}")

    def resize_image_for_email(self, image, max_size=(800, 600)):
        """Resize image for email attachment while maintaining aspect ratio"""
        height, width = image.shape[:2]

        # Calculate new dimensions
        if width > max_size[0] or height > max_size[1]:
            ratio = min(max_size[0] / width, max_size[1] / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            image = cv2.resize(
                image, (new_width, new_height), interpolation=cv2.INTER_AREA
            )

        return image

    def send_alarm(self, student_id, annotated_image):
        """Send alarm email and log the failed verification"""
        try:
            print("\n🚨 Starting alarm sending process...")
            print(f"Student ID: {student_id}")

            # Get the verification ID from the result
            verification_id = self.verification_result.get("id")
            print(f"Verification ID: {verification_id}")

            if not verification_id:
                raise ValueError("Verification ID not found in results")

            # Get the path to the saved annotated image
            img_path = os.path.join("results", verification_id, "annotated.jpg")
            print(f"Looking for image at: {img_path}")

            if not os.path.exists(img_path):
                print("Image file not found!")
                # Try to save the image directly
                print("Attempting to save image directly...")
                os.makedirs(os.path.join("results", verification_id), exist_ok=True)
                cv2.imwrite(img_path, annotated_image)
                if not os.path.exists(img_path):
                    raise ValueError(f"Failed to save image at {img_path}")
                print("Image saved successfully")

            # Send security alarm using the API endpoint
            print("Calling security alarm API endpoint...")
            response = requests.post(
                f"{self.api_url}/security/alarm",
                json={"student_id": student_id, "verification_id": verification_id},
            )

            if response.status_code == 200 and response.json()["success"]:
                # Log the failed verification
                print("Logging failed verification...")
                self.logger.log_failed_verification(
                    self.verification_result, annotated_image
                )
                self.show_message("Alert Sent", "Security has been notified")
                self.setup_camera_view()
            else:
                error_msg = response.json().get("message", "Unknown error")
                raise ValueError(f"Failed to send alarm: {error_msg}")

        except Exception as e:
            error_msg = str(e)
            print(f"Error in send_alarm: {error_msg}")
            if "Email credentials not found" in error_msg:
                self.show_message(
                    "Error",
                    "Email configuration is missing. Please check your .env file.",
                )
            elif "Verification ID not found" in error_msg:
                self.show_message(
                    "Error", "Could not find verification results. Please try again."
                )
            elif "Image file not found" in error_msg:
                self.show_message(
                    "Error", "Could not save or find the verification image."
                )
            else:
                self.show_message("Error", f"Failed to send alert: {error_msg}")

    def show_message(self, title, message):
        """Show a popup message"""
        popup = ctk.CTkToplevel(self)
        popup.title(title)
        popup.geometry("300x150")

        label = ctk.CTkLabel(popup, text=message)
        label.pack(pady=20)

        button = ctk.CTkButton(popup, text="OK", command=popup.destroy)
        button.pack(pady=10)

    def resize_image(self, img, max_width, max_height):
        """Resize image maintaining aspect ratio"""
        ratio = min(max_width / img.width, max_height / img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        return img.resize(new_size, Image.Resampling.LANCZOS)

    def on_closing(self):
        """Clean up resources when closing"""
        if self.cap is not None:
            self.cap.release()
        self.quit()


if __name__ == "__main__":
    app = VerificationApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
