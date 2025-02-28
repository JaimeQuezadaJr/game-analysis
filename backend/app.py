from flask import Flask, request, jsonify
import cv2
import numpy as np
import os
from flask_cors import CORS
import pytesseract
from PIL import Image

app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


class FortniteStatsExtractor:
    def __init__(self):
        self.stats_roi = {
            "victory": {
                "top": 0.05,  # 5% from top
                "height": 0.2,  # 20% of height
                "left": 0.35,  # 35% from left
                "width": 0.3,  # 30% of width
            },
            "match_stats": {
                "top": 0.2,  # 20% from top
                "height": 0.6,  # 60% of height
                "left": 0.1,  # 10% from left
                "width": 0.3,  # 30% of width
            },
        }

    def preprocess_image(self, image):
        """Preprocess image for better OCR results"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Increase contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # Apply thresholding to get white text
        _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

        return thresh

    def get_roi(self, image, roi_config):
        """Extract region of interest from image"""
        h, w = image.shape[:2]
        x1 = int(w * roi_config["left"])
        y1 = int(h * roi_config["top"])
        x2 = int(x1 + w * roi_config["width"])
        y2 = int(y1 + h * roi_config["height"])

        return image[y1:y2, x1:x2]

    def extract_text(self, image):
        """Extract text from image using OCR"""
        # Convert OpenCV image to PIL Image for Tesseract
        pil_image = Image.fromarray(image)

        # Extract text with specific configuration for better accuracy
        text = pytesseract.image_to_string(pil_image, config="--psm 6 --oem 3")

        return text.strip()

    def clean_stat_name(self, stat_name):
        """Clean up stat names for consistency"""
        # Remove common suffixes and clean up names
        stat_name = stat_name.replace("To Players", "")
        stat_name = stat_name.replace("To Structures", "")
        stat_name = stat_name.strip()
        return stat_name

    def clean_value(self, value):
        """Clean up and normalize stat values"""
        value = value.strip().lower()

        # Handle common OCR misreadings of zero
        if value in ["tt", "oo", "o0", "0o", "t1", "1t"]:
            return 0

        # Handle distance with unit
        if "km" in value:
            # First, clean up common OCR misreadings
            value = value.replace("gkm", "6 km")  # Common misreading
            value = value.replace("okm", "0 km")
            value = value.replace("ikm", "1 km")

            # Extract all digits before 'km'
            digits = "".join(c for c in value if c.isdigit() or c == ".")
            if digits:
                try:
                    return float(digits)
                except ValueError:
                    pass
            return 0  # Default to 0 if no valid number found

        # Handle percentage
        if "%" in value:
            try:
                return float(value.replace("%", ""))
            except ValueError:
                return value

        # Try to convert to integer
        try:
            return int(value)
        except ValueError:
            # If we can't convert, return original value
            return value

    def parse_stats(self, stats_text):
        """Parse the extracted stats text into structured data"""
        lines = stats_text.split("\n")
        stats = {}

        # Define expected stats with their default values
        expected_stats = {
            "Eliminations": 0,
            "Assists": 0,
            "Revives": 0,
            "Accuracy": 0,
            "Damage To Players": 0,
            "Head Shots": 0,
            "Distance Traveled": 0,
            "Materials Gathered": 0,
            "Materials Used": 0,
            "Damage Taken": 0,
            "Hits": 0,
            "Damage To Structures": 0,
        }

        for line in lines:
            line = line.strip()
            if not line or line.lower() == "match stats":
                continue

            # Try different splitting patterns
            parts = None
            if ":" in line:
                parts = line.split(":")
            else:
                # Look for the last number in the string
                text_parts = line.split()
                if text_parts:
                    value_part = text_parts[-1]
                    key_part = " ".join(text_parts[:-1])
                    parts = [key_part, value_part]

            if parts and len(parts) == 2:
                key = self.clean_stat_name(parts[0].strip())
                value = self.clean_value(parts[1].strip())

                # Special handling for Distance Traveled
                if key == "Distance Traveled" and isinstance(value, (int, float)):
                    stats[key] = value
                # Store other cleaned values
                elif key in expected_stats:
                    stats[key] = value

        # Ensure all expected stats are present
        for key, default_value in expected_stats.items():
            if key not in stats:
                stats[key] = default_value

        return stats

    def process_image(self, image_path):
        """Process the image and extract all relevant information"""
        # Read image
        image = cv2.imread(image_path)
        if image is None:
            return {"error": "Could not read image"}

        # Preprocess image
        processed = self.preprocess_image(image)

        # Extract victory text
        victory_roi = self.get_roi(processed, self.stats_roi["victory"])
        victory_text = self.extract_text(victory_roi)

        # Extract match stats
        stats_roi = self.get_roi(processed, self.stats_roi["match_stats"])
        stats_text = self.extract_text(stats_roi)

        # Parse the stats
        match_stats = self.parse_stats(stats_text)

        return {
            "placement": victory_text,
            "match_stats": match_stats,
            "status": "complete",
        }


@app.route("/upload", methods=["POST"])
def upload_image():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    # Verify file is an image
    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        return jsonify({"error": "File must be an image (PNG, JPG)"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    try:
        extractor = FortniteStatsExtractor()
        report = extractor.process_image(file_path)
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


if __name__ == "__main__":
    app.run(debug=True)
