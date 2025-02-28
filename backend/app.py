from flask import Flask, request, jsonify
import cv2
import numpy as np
import os
from flask_cors import CORS
import pytesseract
from PIL import Image
import openai
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict

load_dotenv()

app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")

# Simple in-memory rate limiting
RATE_LIMIT = 10  # requests per minute
request_counts = defaultdict(list)


def is_rate_limited(ip):
    """Basic rate limiting check"""
    now = datetime.now()
    minute_ago = now - timedelta(minutes=1)

    # Clean old requests
    request_counts[ip] = [
        timestamp for timestamp in request_counts[ip] if timestamp > minute_ago
    ]

    # Check if under rate limit
    if len(request_counts[ip]) >= RATE_LIMIT:
        return True

    # Add new request
    request_counts[ip].append(now)
    return False


class FortniteStatsExtractor:
    def __init__(self):
        self.stats_roi = {
            "victory": {
                "top": 0.15,  # 15% from top
                "height": 0.15,  # 15% of height
                "left": 0.3,  # 30% from left
                "width": 0.4,  # 40% of width
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

    def clean_victory_text(self, text):
        """Clean up victory text"""
        text = text.strip().upper()
        if "VICTORY" in text and "ROYALE" in text:
            return "#1 VICTORY ROYALE"
        return text

    def get_placement_number(self, text):
        """Extract placement number from victory/placement text"""
        if "VICTORY" in text.upper() or "#1" in text:
            return "1st"
        # For other placements (future use)
        numbers = "".join(c for c in text if c.isdigit())
        if numbers:
            num = int(numbers)
            if num == 1:
                return "1st"
            elif num == 2:
                return "2nd"
            elif num == 3:
                return "3rd"
            else:
                return f"{num}th"
        return None

    def process_image(self, image_path):
        """Process the image and extract all relevant information"""
        # Read image
        image = cv2.imread(image_path)
        if image is None:
            return {"error": "Could not read image"}

        # Preprocess image
        processed = self.preprocess_image(image)

        # Extract match stats first
        stats_roi = self.get_roi(processed, self.stats_roi["match_stats"])
        stats_text = self.extract_text(stats_roi)
        match_stats = self.parse_stats(stats_text)

        # Always set placement to "1st" for Victory Royale screens
        match_stats["Placement"] = "1st"

        # Create structured JSON response
        response = {
            "match_summary": {
                "placement": match_stats["Placement"],
                "combat_stats": {
                    "eliminations": match_stats["Eliminations"],
                    "damage_dealt": match_stats["Damage To Players"],
                    "damage_taken": match_stats["Damage Taken"],
                    "accuracy": match_stats["Accuracy"],
                    "hits": match_stats["Hits"],
                    "headshots": match_stats["Head Shots"],
                },
                "support_stats": {
                    "assists": match_stats["Assists"],
                    "revives": match_stats["Revives"],
                },
                "resource_stats": {
                    "materials_gathered": match_stats["Materials Gathered"],
                    "materials_used": match_stats["Materials Used"],
                    "damage_to_structures": match_stats["Damage To Structures"],
                },
                "movement_stats": {
                    "distance_traveled": match_stats["Distance Traveled"]
                },
            },
            "raw_stats": match_stats,  # Include original stats for reference
            "status": "complete",
        }

        return response


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


@app.route("/analyze", methods=["POST"])
def analyze_stats():
    try:
        # Basic rate limiting
        if is_rate_limited(request.remote_addr):
            return (
                jsonify({"error": "Rate limit exceeded. Please try again later."}),
                429,
            )

        match_data = request.json.get("match_data")
        if not match_data:
            return jsonify({"error": "No match data provided"}), 400

        # Prepare the prompt for GPT
        prompt = f"""
        As a Fortnite expert, analyze these match statistics and provide 3-4 key insights about the player's performance:

        Placement: {match_data['placement']}
        
        Combat Stats:
        - Eliminations: {match_data['combat_stats']['eliminations']}
        - Damage Dealt: {match_data['combat_stats']['damage_dealt']}
        - Damage Taken: {match_data['combat_stats']['damage_taken']}
        - Accuracy: {match_data['combat_stats']['accuracy']}%
        - Hits: {match_data['combat_stats']['hits']}
        - Headshots: {match_data['combat_stats']['headshots']}
        
        Support Stats:
        - Assists: {match_data['support_stats']['assists']}
        - Revives: {match_data['support_stats']['revives']}
        
        Resource Stats:
        - Materials Gathered: {match_data['resource_stats']['materials_gathered']}
        - Materials Used: {match_data['resource_stats']['materials_used']}
        - Damage to Structures: {match_data['resource_stats']['damage_to_structures']}
        
        Movement:
        - Distance Traveled: {match_data['movement_stats']['distance_traveled']}km

        Focus on:
        1. Combat effectiveness and accuracy
        2. Resource management and building strategy
        3. Overall performance and areas for improvement
        
        Keep insights concise and actionable.
        """

        # Get analysis from GPT-3.5 Turbo
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert Fortnite coach providing concise, actionable insights.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,  # Slightly creative but still focused
            max_tokens=200,  # Limit response length
        )

        # Extract and format insights
        analysis = response.choices[0].message.content.split("\n")
        analysis = [insight.strip() for insight in analysis if insight.strip()]

        return jsonify(
            {
                "analysis": analysis,
                "tokens_used": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            }
        )

    except openai.error.RateLimitError:
        return (
            jsonify({"error": "AI service is currently busy. Please try again later."}),
            429,
        )
    except openai.error.AuthenticationError:
        return jsonify({"error": "AI service configuration error."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
