import cv2
import numpy as np
from pathlib import Path

image_path = '/Users/rafael/Library/CloudStorage/Dropbox-ArsenalCraft/Pasta da equipe Arsenal Craft/Miniaturas/RN Estudios/PRE-SUPPORTED 82 - March 2026 - RNEstudio/Roach Multipart Kit/Roach.jpg'
img = cv2.imread(image_path)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# The background is very black. Threshold to find non-black regions.
_, thresh = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)

# Morphological operations to close gaps and remove small noise
kernel = np.ones((15, 15), np.uint8)
closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
closed = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)

# Find contours
contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

boxes = []
min_area = (img.shape[0] * img.shape[1]) * 0.01 # At least 1% of the image
for c in contours:
    if cv2.contourArea(c) > min_area:
        x, y, w, h = cv2.boundingRect(c)
        boxes.append([x, y, x+w, y+h])

print(f"Detected {len(boxes)} boxes via OpenCV:")
print(boxes)
