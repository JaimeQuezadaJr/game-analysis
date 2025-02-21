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

        # Damage number detection parameters
        self.damage_colors = [
            # White damage numbers
            (np.array([220, 220, 220]), np.array([255, 255, 255])),
            # Yellow shield damage (in HSV)
            (np.array([20, 150, 150]), np.array([40, 255, 255])),
        ]
        self.min_damage_area = 30
        self.max_damage_area = 300
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
        """Detect hits by looking for damage numbers next to enemies"""
        original_frame = frame.copy()
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Get center ROI where enemies are typically located
        x1, y1, x2, y2 = self.get_center_roi(frame)

        # Create masks for all damage numbers
        # White damage numbers
        white_mask = cv2.inRange(
            frame_rgb,
            np.array([240, 240, 240]),  # Bright white
            np.array([255, 255, 255]),
        )

        # Blue shield damage
        blue_mask = cv2.inRange(
            frame_hsv,
            np.array([90, 150, 200]),  # Bright blue
            np.array([110, 255, 255]),
        )

        # Yellow shield break
        yellow_mask = cv2.inRange(
            frame_hsv,
            np.array([25, 180, 180]),  # Bright yellow
            np.array([35, 255, 255]),
        )

        # Combine all damage number masks
        combined_mask = cv2.bitwise_or(
            cv2.bitwise_or(white_mask, yellow_mask), blue_mask
        )

        # Focus on center portion
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

                if 1.2 < aspect_ratio < 2.5:
                    # Determine damage type by color
                    roi = frame[y : y + h, x : x + w]
                    roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

                    damage_type = "Health"  # Default to white/health damage
                    if (
                        cv2.mean(
                            cv2.bitwise_and(
                                roi_hsv,
                                roi_hsv,
                                mask=cv2.inRange(
                                    roi_hsv,
                                    np.array([90, 150, 200]),
                                    np.array([110, 255, 255]),
                                ),
                            )
                        )[0]
                        > 0
                    ):
                        damage_type = "Shield"
                    elif (
                        cv2.mean(
                            cv2.bitwise_and(
                                roi_hsv,
                                roi_hsv,
                                mask=cv2.inRange(
                                    roi_hsv,
                                    np.array([25, 180, 180]),
                                    np.array([35, 255, 255]),
                                ),
                            )
                        )[0]
                        > 0
                    ):
                        damage_type = "Shield Break"

                    self.last_damage_type = damage_type  # Store the damage type
                    hit_detected = True

                    if self.debug:
                        cv2.drawContours(original_frame, [contour], -1, (0, 0, 255), 2)
                        cv2.putText(
                            original_frame,
                            f"{damage_type} Damage - Area: {area:.1f}, Ratio: {aspect_ratio:.2f}",
                            (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 0, 255),
                            2,
                        )
                        # Save the damage number region
                        damage_roi = frame[y : y + h, x : x + w]
                        cv2.imwrite(
                            f"{self.debug_dir}/damage_number_{self.frame_count}_{damage_type}_{x}_{y}.jpg",
                            damage_roi,
                        )
                        print(
                            f"Frame {self.frame_count}: {damage_type} damage detected!"
                        )
                        print(f"  Position: ({x}, {y})")
                        print(f"  Size: {w}x{h}")
                        print(f"  Area: {area:.1f}")
                        print(f"  Aspect ratio: {aspect_ratio:.2f}")

        if self.debug:
            # Draw ROI
            cv2.rectangle(original_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Save debug image showing all masks
            debug_img = np.vstack(
                [
                    original_frame,
                    cv2.cvtColor(white_mask, cv2.COLOR_GRAY2BGR),
                    cv2.cvtColor(blue_mask, cv2.COLOR_GRAY2BGR),
                    cv2.cvtColor(yellow_mask, cv2.COLOR_GRAY2BGR),
                    cv2.cvtColor(combined_mask, cv2.COLOR_GRAY2BGR),
                ]
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
                if debug:
                    print(f"Shot fired at {current_time:.2f}s (frame {frame_id})")

        # Detect hits by checking for damage numbers
        if analyzer.detect_hit(frame):
            if (
                last_hit_time is None
                or (current_time - last_hit_time) > analyzer.hit_cooldown
            ):
                stats["total_hits"] += 1
                # Track the type of hit
                if analyzer.last_damage_type == "Shield":
                    stats["shield_hits"] += 1
                elif analyzer.last_damage_type == "Health":
                    stats["health_hits"] += 1
                else:
                    stats["shield_break_hits"] += 1

                last_hit_time = current_time
                if debug:
                    print(
                        f"Hit confirmed at {current_time:.2f}s ({analyzer.last_damage_type})"
                    )

        if debug and frame_id % 30 == 0:  # Print progress every 30 frames
            print(f"Processing frame {frame_id}/{total_frames}")

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
