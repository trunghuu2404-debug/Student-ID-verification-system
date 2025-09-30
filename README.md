# Student ID Verification System

This project is a computer vision-based ID verification system that:
- Detects ID cards from a webcam feed
- Checks for presence of logo and specific patterns
- Detects and matches faces using FaceNet
- Extracts text using OCR (e.g., ID number, first name, last name)
- Shows annotated frames with bounding boxes
- Saves the annotated frame and cropped face image if all labels are detected
- Provides results through a RESTful API

## How to run locally

### 1.Start the Flask API server on one terminal
python api.py

- The server will start on http://127.0.0.1:5000/

- It will accept image uploads at POST /verifications

### 2.Then run the live detection client on another terminal

python test_realtime.py

- This will start your webcam.

- Frames are continuously sent to the API.

- Bounding boxes and label annotations are shown live.

- If all required labels are detected:

Annotated frame and face crop are saved inside a subfolder in results/.

The script will display the final frame and stop.



Output example
✅ All labels detected!
🧠 Face Match: True
🏷️ Logo Found: True
🔲 Pattern Count: 5
🔍 ID Number: 12345678
👤 First Name: John
👤 Last Name: Doe
🖼️ Annotated image saved and displayed. Stopping...

You will find the images saved in:
results/session_20250524_151230/
├── annotated.jpg
└── face_crop.jpg

This one is just for testing, dont need to run this

### 3. Run the GUI Application

python gui_app.py

- This will launch a user-friendly graphical interface
- Features include:
  - Live camera feed with Start/Stop button
  - Automatic face and ID card detection
  - Display of verification results with annotated image
  - OTP verification for successful matches
  - Security alarm system for unauthorized attempts
  - Results are logged to Excel for record keeping

The GUI provides a more intuitive way to interact with the verification system compared to the command-line interface.

When running, you will see it create 2 excel file, one for success verification and other for failed verification.
