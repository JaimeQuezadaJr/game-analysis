from flask import Flask, request, jsonify
import cv2
import numpy as np
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


class FortniteAnalyzer:
    def __init__(self, debug=False):
        # Muzzle flash detection parameters
        self.muzzle_lower = np.array([220, 220, 220])
        self.muzzle_upper = np.array([255, 255, 255])
        self.min_muzzle_area = 50
        self.max_muzzle_area = 1000
        self.shot_cooldown = 0.15

        # Track last seen damage number
        self.last_damage_position = None
        self.last_damage_area = None
        self.hit_cooldown = 0.2

        # Center screen ROI (where most action happens)
        self.center_roi = {
            "width": 0.4,  # 40% of screen width
            "height": 0.4,  # 40% of screen height
        }

        self.debug = debug
        if debug:
            self.debug_dir = "debug_frames"
            os.makedirs(self.debug_dir, exist_ok=True)
            self.frame_count = 0
        self.last_damage_type = None  # Track the type of last damage detected

    def get_center_roi(self, frame):
        """Get the center region of interest"""
        h, w = frame.shape[:2]
        center_y, center_x = h // 2, w // 2

        roi_h = int(h * self.center_roi["height"])
        roi_w = int(w * self.center_roi["width"])

        y1 = center_y - roi_h // 2
        y2 = center_y + roi_h // 2
        x1 = center_x - roi_w // 2
        x2 = center_x + roi_w // 2

        return (x1, y1, x2, y2)

    def get_damage_roi(self, frame):
        """Get the region where damage numbers appear (right of crosshair)"""
        h, w = frame.shape[:2]
        center_y = h // 2
        center_x = w // 2

        # Focus on area just to the right of player model
        roi_h = int(h * 0.25)  # 25% of screen height
        roi_w = int(w * 0.25)  # 25% of screen width

        # Position ROI to the right of player model
        y1 = center_y - roi_h // 2  # Centered vertically
        y2 = center_y + roi_h // 2
        x1 = center_x - roi_w // 4  # Start closer to center
        x2 = center_x + roi_w  # Extend right but not too far

        return (x1, y1, x2, y2)

    def detect_shot(self, frame):
        """Detect shots by looking for muzzle flash in center"""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        original_frame = frame.copy()

        # Get center ROI
        x1, y1, x2, y2 = self.get_center_roi(frame)

        # Create mask for bright areas (muzzle flash)
        muzzle_mask = cv2.inRange(frame_rgb, self.muzzle_lower, self.muzzle_upper)

        # Focus on center portion
        roi_mask = np.zeros_like(muzzle_mask)
        roi_mask[y1:y2, x1:x2] = muzzle_mask[y1:y2, x1:x2]

        # Find bright areas
        contours, _ = cv2.findContours(
            roi_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        shot_detected = False
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.min_muzzle_area < area < self.max_muzzle_area:
                shot_detected = True
                if self.debug:
                    cv2.drawContours(original_frame, [contour], -1, (0, 255, 0), 2)
                    cv2.putText(
                        original_frame,
                        f"Muzzle Flash (area: {area:.1f})",
                        (x1 + 10, y1 + 20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        2,
                    )

        if self.debug:
            # Draw center ROI
            cv2.rectangle(original_frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(
                original_frame,
                "Center ROI",
                (x1 + 10, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 0, 0),
                2,
            )

            # Save debug image
            debug_img = np.vstack(
                [original_frame, cv2.cvtColor(roi_mask, cv2.COLOR_GRAY2BGR)]
            )
            cv2.imwrite(
                f"{self.debug_dir}/shot_detection_{self.frame_count}.jpg", debug_img
            )
            if shot_detected:
                print(f"Frame {self.frame_count}: Shot detected in center!")

        return shot_detected

    def detect_hit(self, frame):
        """Detect hits by looking for damage numbers to the right of player"""
        original_frame = frame.copy()
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Get damage number ROI (right of crosshair)
        x1, y1, x2, y2 = self.get_damage_roi(frame)

        # Create masks for damage numbers
        white_mask = cv2.inRange(
            frame_rgb, np.array([240, 240, 240]), np.array([255, 255, 255])
        )

        blue_mask = cv2.inRange(
            frame_hsv, np.array([85, 150, 200]), np.array([115, 255, 255])
        )

        # Focus only on the damage number area
        white_roi = np.zeros_like(white_mask)
        white_roi[y1:y2, x1:x2] = white_mask[y1:y2, x1:x2]

        blue_roi = np.zeros_like(blue_mask)
        blue_roi[y1:y2, x1:x2] = blue_mask[y1:y2, x1:x2]

        combined_mask = cv2.bitwise_or(white_mask, blue_mask)
        roi_mask = np.zeros_like(combined_mask)
        roi_mask[y1:y2, x1:x2] = combined_mask[y1:y2, x1:x2]

        # Find damage numbers
        contours, _ = cv2.findContours(
            roi_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        hit_detected = False
        for contour in contours:
            area = cv2.contourArea(contour)
            if 35 < area < 250:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = h / w

                # More strict criteria for damage numbers
                if 1.2 < aspect_ratio < 2.5:
                    # Ignore anything that looks like "XP" (usually wider)
                    if w > 50:  # XP numbers tend to be wider
                        continue

                    # Check if this is a different damage number
                    if (
                        self.last_damage_position is None
                        or abs(area - self.last_damage_area) > 10
                    ):
                        # Create masks for just this contour
                        number_mask = np.zeros_like(white_mask)
                        cv2.drawContours(number_mask, [contour], -1, 255, -1)

                        # Check if this number appears in blue mask
                        blue_pixels = cv2.countNonZero(
                            cv2.bitwise_and(blue_roi, number_mask)
                        )
                        white_pixels = cv2.countNonZero(
                            cv2.bitwise_and(white_roi, number_mask)
                        )

                        # More strict shield damage detection
                        # A shield hit must have significantly more blue pixels than white
                        is_shield = blue_pixels > white_pixels and blue_pixels > (
                            area * 0.5
                        )

                        self.last_damage_type = "Shield" if is_shield else "Health"
                        self.last_damage_position = (x, y)
                        self.last_damage_area = area
                        hit_detected = True

                        if self.debug:
                            cv2.drawContours(
                                original_frame, [contour], -1, (0, 0, 255), 2
                            )
                            color_type = "BLUE" if is_shield else "WHITE"
                            cv2.putText(
                                original_frame,
                                f"NEW {self.last_damage_type} Damage ({color_type}) - Area: {area:.1f}",
                                (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5,
                                (0, 0, 255),
                                2,
                            )
                            print(f"Frame {self.frame_count}: New damage detected!")
                            print(f"  Type: {self.last_damage_type}")
                            print(f"  Area: {area:.1f}")
                            print(f"  Position: ({x}, {y})")
                            print(f"  Blue pixels: {blue_pixels}")
                            print(f"  White pixels: {white_pixels}")
                            print(
                                f"  Ratio blue/total: {blue_pixels/(blue_pixels + white_pixels):.2f}"
                            )
                    break

        if self.debug:
            # Draw damage number ROI
            cv2.rectangle(original_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                original_frame,
                "Damage Number ROI",
                (x1 + 10, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
            )
            debug_img = np.vstack(
                [original_frame, cv2.cvtColor(roi_mask, cv2.COLOR_GRAY2BGR)]
            )
            cv2.imwrite(
                f"{self.debug_dir}/hit_detection_{self.frame_count}.jpg", debug_img
            )

        self.frame_count += 1
        return hit_detected


def process_video(video_path, debug=False):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_duration = total_frames / fps

    if video_duration > 120:  # 2 minutes max
        return {"error": "Video must be 2 minutes or shorter"}

    analyzer = FortniteAnalyzer(debug=debug)
    stats = {
        "total_shots": 0,
        "total_hits": 0,
        "shield_hits": 0,
        "health_hits": 0,
        "shield_break_hits": 0,
    }

    last_shot_time = None
    last_hit_time = None
    frame_id = 0
    first_shot_fired = False

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        current_time = frame_id / fps

        # Detect shots using muzzle flash
        if analyzer.detect_shot(frame):
            if (
                last_shot_time is None
                or (current_time - last_shot_time) > analyzer.shot_cooldown
            ):
                stats["total_shots"] += 1
                last_shot_time = current_time
                first_shot_fired = True

        # Only look for hits after first shot is fired
        if first_shot_fired:
            if analyzer.detect_hit(frame):
                if (
                    last_hit_time is None
                    or (current_time - last_hit_time) > analyzer.hit_cooldown
                ):
                    if analyzer.last_damage_type == "Shield":
                        stats["shield_hits"] += 1
                    else:
                        stats["health_hits"] += 1

                    stats["total_hits"] = stats["shield_hits"] + stats["health_hits"]
                    last_hit_time = current_time

        frame_id += 1

    cap.release()

    if debug:
        print("\nFinal stats:")
        print(f"Total shots: {stats['total_shots']}")
        print(f"Total hits: {stats['total_hits']}")
        print(f"  - Shield hits: {stats['shield_hits']}")
        print(f"  - Health hits: {stats['health_hits']}")
        print(f"  - Shield break hits: {stats['shield_break_hits']}")

    return {
        "total_shots": stats["total_shots"],
        "total_hits": stats["total_hits"],
        "shield_hits": stats["shield_hits"],
        "health_hits": stats["health_hits"],
        "shield_break_hits": stats["shield_break_hits"],
        "accuracy": round(
            (
                (stats["total_hits"] / stats["total_shots"] * 100)
                if stats["total_shots"] > 0
                else 0
            ),
            2,
        ),
        "video_duration": round(video_duration, 2),
        "processed_frames": total_frames,
        "total_frames": total_frames,
        "status": "complete",
        "progress": 100,
    }


@app.route("/upload", methods=["POST"])
def upload_video():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    debug_mode = request.form.get("debug", "false").lower() == "true"

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    try:
        report = process_video(file_path, debug=debug_mode)
        return jsonify(report)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


if __name__ == "__main__":
    app.run(debug=True)
