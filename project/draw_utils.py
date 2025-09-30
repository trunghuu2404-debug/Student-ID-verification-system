# draw_utils.py
import cv2

class_colors = {
    0: (255, 255, 0),  # UTS ID
    1: (0, 0, 255),  # Other ID
    2: (255, 0, 255),  # ID Number
    3: (0, 255, 255),  # First Name
    4: (255, 165, 0),  # Last Name
    5: (0, 255, 0),  # Pattern
    6: (255, 0, 0),  # Logo
}


def draw_bounding_box(image, bbox, label, color):
    x, y, w, h = bbox
    cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
    cv2.putText(image, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
