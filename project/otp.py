import os
import pyotp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = os.getenv("EMAIL_USERNAME")
SMTP_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Store OTP secrets temporarily (in a real application, use a database)
otp_store = {}


def generate_otp(student_id):
    """
    Generate a new OTP for a student ID and store it
    """
    print(f"\nGenerating OTP for student ID: {student_id}")

    # Generate a new random secret for this student
    secret = pyotp.random_base32()

    # Create a TOTP object with 4 digits, valid for 5 minutes
    totp = pyotp.TOTP(secret, interval=300, digits=4)  # 300 seconds = 5 minutes

    # Generate the current OTP
    otp_code = totp.now()
    print(f"Generated OTP: {otp_code}")

    # Store the secret and expiration time
    otp_store[student_id] = {
        "secret": secret,
        "expires_at": datetime.now() + timedelta(minutes=5),
        "otp_code": otp_code,  # Store the actual OTP for verification
    }

    return otp_code


def verify_otp(student_id, otp_code):
    """
    Verify an OTP code for a student ID
    """
    print(f"\nVerifying OTP for student ID: {student_id}")
    print(f"Received OTP code: {otp_code}")

    if student_id not in otp_store:
        print("No OTP found for this student ID")
        return False, "No OTP was generated for this student ID"

    stored_data = otp_store[student_id]
    print(f"Stored OTP: {stored_data['otp_code']}")

    # Check if OTP has expired
    if datetime.now() > stored_data["expires_at"]:
        print("OTP has expired")
        del otp_store[student_id]  # Clean up expired OTP
        return False, "OTP has expired"

    # Direct comparison with stored OTP
    if otp_code == stored_data["otp_code"]:
        print("OTP verified successfully")
        del otp_store[student_id]  # Clean up used OTP
        return True, "OTP verified successfully"

    print("Invalid OTP")
    return False, "Invalid OTP"


def send_otp_email(student_id, otp_code):
    """
    Send OTP code to student's UTS email
    """
    student_email = f"{student_id}@student.uts.edu.au"
    print(f"\nStarting OTP email process...")
    print(f"Sending to: {student_email}")
    print(f"From: {SMTP_USERNAME}")

    # Create message
    msg = MIMEMultipart()
    msg["From"] = SMTP_USERNAME
    msg["To"] = student_email
    msg["Subject"] = "Your UTS Library Access Verification Code"

    body = f"""
    Hello UTS Student,
    
    Your verification code for UTS Library Access is: {otp_code}
    
    This code will expire in 5 minutes.
    
    If you did not request this code, please ignore this email.
    
    Best regards,
    UTS Library Security System
    """

    msg.attach(MIMEText(body, "plain"))

    try:
        print("Connecting to SMTP server...")
        # Create SMTP session
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        print("Starting TLS...")
        server.starttls()
        print("Logging in to SMTP server...")
        server.login(SMTP_USERNAME, SMTP_PASSWORD)

        # Send email
        print("Sending email...")
        server.send_message(msg)
        server.quit()
        print(f"OTP email sent successfully to {student_email}")
        return True, "OTP sent successfully"
    except Exception as e:
        error_details = str(e)
        print(f"Failed to send OTP email: {error_details}")
        print(f"SMTP Server: {SMTP_SERVER}")
        print(f"SMTP Port: {SMTP_PORT}")
        print(f"Username: {SMTP_USERNAME}")
        return False, error_details


def send_security_alarm(student_id):
    """
    Send security alarm email when unauthorized access is detected
    Args:
        student_id: Student ID number
    Returns:
        tuple: (success: bool, message: str)
    """
    student_email = f"{student_id}@student.uts.edu.au"
    print(f"\nStarting security alarm email process...")
    print(f"Sending to: {student_email}")
    print(f"From: {SMTP_USERNAME}")

    # Create message
    msg = MIMEMultipart()
    msg["From"] = SMTP_USERNAME
    msg["To"] = student_email
    msg["Subject"] = "SECURITY ALERT - Unauthorized Student ID Card Usage"

    body = f"""
    Dear Student,

    Our security system has detected that your student ID card (ID: {student_id}) is being used by someone who does not match the ID photo.
    This incident has been logged and campus security has been notified.

    Time of incident: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


    Please report to the UTS Student Centre immediately if you have lost your card or if you believe it has been stolen.

    Best regards,
    UTS Library Security System
    """

    msg.attach(MIMEText(body, "plain"))

    try:
        # Create SMTP session
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)

        # Send email
        server.send_message(msg)
        server.quit()
        print(f"Security alarm email sent successfully to {student_email}")
        return True, "Security alarm sent successfully"
    except Exception as e:
        print(f"Failed to send security alarm: {e}")
        return False, str(e)
