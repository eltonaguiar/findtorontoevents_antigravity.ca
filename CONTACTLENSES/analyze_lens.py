#!/usr/bin/env python3
"""
Contact Lens Orientation Analyzer v2.0 using OpenCV.

Enhanced analysis with:
  - Multi-pass adaptive thresholding (replaces single threshold)
  - Rim-specific curvature analysis with inflection point detection
  - Convex hull solidity check
  - Aspect ratio validation (side-profile enforcement)
  - Brightness / backlighting quality check
  - NO random noise in scoring (deterministic results)

Uses HSV color segmentation to mask skin tones (finger) and analyzes
the lens curvature using contour analysis and rim inflection detection.

Usage:
    python analyze_lens.py <image_path>

Returns JSON with status, message, confidence_pct, factors, and debug info.
"""

import cv2
import numpy as np
import sys
import json
import os


def assess_quality(img):
    """Assess image quality for lens analysis."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    return {
        "brightness": round(brightness, 1),
        "contrast": round(contrast, 1),
        "too_dark": brightness < 40,
        "low_contrast": contrast < 15,
    }


def mask_skin(img):
    """Create a mask that removes skin-tone regions (the finger)."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Multiple skin tone ranges for different lighting / skin colors
    masks = []
    ranges = [
        ((0, 20, 70), (20, 255, 255)),   # lighter
        ((0, 10, 60), (25, 255, 255)),    # darker / redder
        ((160, 20, 70), (180, 255, 255)), # pinkish wrap-around
    ]
    for (lo, hi) in ranges:
        masks.append(cv2.inRange(hsv, np.array(lo, np.uint8), np.array(hi, np.uint8)))

    skin_mask = masks[0]
    for m in masks[1:]:
        skin_mask = cv2.bitwise_or(skin_mask, m)

    # Dilate to cover finger edges
    kernel = np.ones((7, 7), np.uint8)
    skin_mask = cv2.dilate(skin_mask, kernel, iterations=2)
    return cv2.bitwise_not(skin_mask)


def find_lens_contour(img, not_skin):
    """
    Find the largest non-skin contour (the lens) using multi-pass adaptive thresholding.
    Returns the best contour or None.
    """
    gray = cv2.cvtColor(cv2.bitwise_and(img, img, mask=not_skin), cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    best_contour = None
    best_area = 0
    h, w = gray.shape

    # Try multiple threshold methods
    binaries = []

    # Adaptive threshold
    binaries.append(cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    ))

    # Otsu threshold
    _, otsu_bin = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    binaries.append(otsu_bin)

    # Fixed thresholds
    for t in [15, 30, 50]:
        _, fb = cv2.threshold(gray, t, 255, cv2.THRESH_BINARY)
        binaries.append(fb)

    kernel = np.ones((5, 5), np.uint8)
    min_area = w * h * 0.005  # at least 0.5% of image

    for binary in binaries:
        # Clean up
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > min_area and area > best_area:
                best_area = area
                best_contour = cnt

    return best_contour


def analyze_rim_curvature(contour, bbox):
    """
    Analyze the rim (top portion) of the lens contour for inflection / flare.

    Returns:
        inflection_score: positive = flare detected (inside-out), negative = smooth (correct)
        tip_flare_left: flare amount on left rim
        tip_flare_right: flare amount on right rim
    """
    x, y, w, h = bbox
    center_x = x + w / 2
    top_cutoff = y + h * 0.25  # top 25%

    # Extract top-rim points
    top_points = []
    for pt in contour:
        px, py = pt[0]
        if py <= top_cutoff:
            top_points.append((float(px), float(py)))

    if len(top_points) < 10:
        return {"inflection_score": 0, "tip_flare_left": 0, "tip_flare_right": 0, "rim_points": len(top_points)}

    # Split into left and right
    margin = w * 0.1
    left_pts = [p for p in top_points if p[0] < center_x - margin]
    right_pts = [p for p in top_points if p[0] > center_x + margin]

    def measure_flare(pts, center, side):
        """Bin points by distance from center, check for inflection."""
        if len(pts) < 5:
            return 0, 0

        # Sort by distance from center
        pts_sorted = sorted(pts, key=lambda p: abs(p[0] - center))
        n_bins = min(6, len(pts_sorted) // 2)
        if n_bins < 3:
            return 0, 0

        bin_size = len(pts_sorted) // n_bins
        bins = []
        for i in range(n_bins):
            start = i * bin_size
            end = start + bin_size if i < n_bins - 1 else len(pts_sorted)
            chunk = pts_sorted[start:end]
            avg_y = np.mean([p[1] for p in chunk])
            avg_dist = np.mean([abs(p[0] - center) for p in chunk])
            bins.append({"y": avg_y, "dist": avg_dist})

        # Check for inflection: slope goes from negative (going up) to positive (going down)
        inflection = 0
        prev_slope = None
        for i in range(1, len(bins)):
            slope = bins[i]["y"] - bins[i - 1]["y"]
            if prev_slope is not None:
                if prev_slope < -0.5 and slope > 0.5:
                    inflection += 1
            prev_slope = slope

        # Tip flare: compare outermost to second-outermost
        tip = bins[-1]["y"] - bins[-2]["y"]
        y_range = abs(bins[0]["y"] - bins[-1]["y"]) if len(bins) > 1 else 1
        normalized_flare = tip / max(y_range, 1)

        return inflection, normalized_flare

    left_inf, left_flare = measure_flare(left_pts, center_x, "left")
    right_inf, right_flare = measure_flare(right_pts, center_x, "right")

    return {
        "inflection_score": (left_inf + right_inf) / 2,
        "tip_flare_left": round(left_flare, 4),
        "tip_flare_right": round(right_flare, 4),
        "rim_points": len(top_points),
    }


def analyze_lens(image_path):
    """
    Analyze a contact lens image to determine orientation.

    Returns dict with status, message, confidence_pct, factors, and debug info.
    """
    if not os.path.exists(image_path):
        return {"status": "error", "message": "File not found", "confidence_pct": 0}

    img = cv2.imread(image_path)
    if img is None:
        return {"status": "error", "message": "Invalid image format or corrupted file", "confidence_pct": 0}

    height, width = img.shape[:2]

    # 1. QUALITY CHECK
    quality = assess_quality(img)
    if quality["too_dark"]:
        return {
            "status": "uncertain",
            "message": "Image is too dark. Use backlighting (bright screen or window behind the lens).",
            "confidence_pct": 15,
            "tip": "Hold the lens in front of a bright white surface.",
            "factors": [{"name": "Brightness", "value": quality["brightness"], "status": "bad"}],
        }

    # 2. SKIN MASKING
    not_skin = mask_skin(img)

    # 3. FIND LENS CONTOUR (multi-pass)
    contour = find_lens_contour(img, not_skin)

    if contour is None:
        return {
            "status": "uncertain",
            "message": "No lens detected. Ensure lens is visible against a contrasting background.",
            "confidence_pct": 20,
            "tip": "Use a plain background with good lighting.",
            "factors": [
                {"name": "Lens detected", "value": "No", "status": "bad"},
                {"name": "Brightness", "value": quality["brightness"], "status": "good" if not quality["too_dark"] else "bad"},
            ],
        }

    area = cv2.contourArea(contour)
    x, y, w, h = cv2.boundingRect(contour)

    # 4. RIM CURVATURE ANALYSIS
    rim = analyze_rim_curvature(contour, (x, y, w, h))

    # 5. CONVEXITY
    hull = cv2.convexHull(contour)
    hull_area = cv2.contourArea(hull)
    solidity = area / max(hull_area, 1)

    # 6. ASPECT RATIO (side-profile check)
    aspect_ratio = w / max(h, 1)
    is_side_profile = aspect_ratio > 1.2

    # 7. SCORING (NO RANDOM NOISE)
    inverted_score = 0
    correct_score = 0
    factors = []

    # Factor 1: Rim inflection
    avg_inflection = rim["inflection_score"]
    if avg_inflection > 0.3:
        inverted_score += 3
        factors.append({"name": "Rim inflection (flare)", "value": "Detected", "status": "bad"})
    elif avg_inflection < -0.1:
        correct_score += 3
        factors.append({"name": "Rim curvature", "value": "Smooth inward", "status": "good"})
    else:
        factors.append({"name": "Rim curvature", "value": "Ambiguous", "status": "neutral"})

    # Factor 2: Tip flare
    avg_flare = (rim["tip_flare_left"] + rim["tip_flare_right"]) / 2
    if avg_flare > 0.4:
        inverted_score += 2
        factors.append({"name": "Edge tip direction", "value": "Flaring out", "status": "bad"})
    elif avg_flare < -0.2:
        correct_score += 2
        factors.append({"name": "Edge tip direction", "value": "Curving in", "status": "good"})
    else:
        factors.append({"name": "Edge tip direction", "value": "Neutral", "status": "neutral"})

    # Factor 3: Corner fill (from v1, improved)
    top_margin = int(h * 0.10)
    gray_full = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    roi_top = gray_full[y:y + max(top_margin, 1), x:x + w]
    if roi_top.size > 0:
        corner_w = max(int(w * 0.15), 1)
        left_corner = roi_top[:, :corner_w]
        right_corner = roi_top[:, -corner_w:]
        total_px = left_corner.size + right_corner.size
        bright_px = np.sum(left_corner > 50) + np.sum(right_corner > 50)
        corner_ratio = bright_px / max(total_px, 1)

        if corner_ratio > 0.12:
            inverted_score += 1.5
            factors.append({"name": "Corner fill ratio", "value": f"{corner_ratio:.1%}", "status": "bad"})
        elif corner_ratio < 0.03:
            correct_score += 1.5
            factors.append({"name": "Corner fill ratio", "value": f"{corner_ratio:.1%}", "status": "good"})
        else:
            factors.append({"name": "Corner fill ratio", "value": f"{corner_ratio:.1%}", "status": "neutral"})

    # Factor 4: Solidity
    if solidity > 0.92:
        correct_score += 1
        factors.append({"name": "Shape convexity", "value": f"{solidity:.0%}", "status": "good"})
    elif solidity < 0.82:
        inverted_score += 1
        factors.append({"name": "Shape convexity", "value": f"{solidity:.0%}", "status": "bad"})
    else:
        factors.append({"name": "Shape convexity", "value": f"{solidity:.0%}", "status": "neutral"})

    # Factor 5: Side-profile check
    if not is_side_profile:
        factors.append({"name": "View angle", "value": "Possibly top-down", "status": "bad"})
    else:
        factors.append({"name": "View angle", "value": "Side profile", "status": "good"})

    # Brightness factor
    factors.append({
        "name": "Background brightness",
        "value": quality["brightness"],
        "status": "good" if quality["brightness"] > 140 else ("neutral" if quality["brightness"] > 80 else "bad"),
    })

    # 8. CONFIDENCE
    score_diff = abs(inverted_score - correct_score)
    if score_diff >= 4:
        confidence = 92
    elif score_diff >= 3:
        confidence = 82
    elif score_diff >= 2:
        confidence = 70
    elif score_diff >= 1:
        confidence = 58
    else:
        confidence = 45

    if not is_side_profile:
        confidence = min(confidence, 55)
    if quality["brightness"] < 80:
        confidence -= 10
    if quality["low_contrast"]:
        confidence -= 8
    confidence = max(15, min(99, confidence))

    # 9. DECISION
    if inverted_score > correct_score:
        return {
            "status": "inverted",
            "message": "The edges appear to flare outward. The lens is likely INSIDE OUT. Gently flip it before inserting.",
            "confidence_pct": int(confidence),
            "tip": "Place the lens in your palm and gently press the center to invert it. Rinse with solution.",
            "factors": factors,
            "debug": {
                "inverted_score": inverted_score,
                "correct_score": correct_score,
                "solidity": round(solidity, 3),
                "aspect_ratio": round(aspect_ratio, 2),
                "rim": rim,
            },
        }
    elif correct_score > inverted_score:
        return {
            "status": "correct",
            "message": "The edges curve smoothly inward. The lens appears to be oriented CORRECTLY. Safe to insert!",
            "confidence_pct": int(confidence),
            "tip": "Looks good! If it feels uncomfortable after inserting, remove and flip it.",
            "factors": factors,
            "debug": {
                "inverted_score": inverted_score,
                "correct_score": correct_score,
                "solidity": round(solidity, 3),
                "aspect_ratio": round(aspect_ratio, 2),
                "rim": rim,
            },
        }
    else:
        return {
            "status": "uncertain",
            "message": "Unable to determine orientation with confidence. Try repositioning with better backlighting and a clearer side-profile view.",
            "confidence_pct": int(confidence),
            "tip": "Hold lens at eye level against a bright white background. The side profile (edge) must be clearly visible.",
            "factors": factors,
            "debug": {
                "inverted_score": inverted_score,
                "correct_score": correct_score,
                "solidity": round(solidity, 3),
                "aspect_ratio": round(aspect_ratio, 2),
                "rim": rim,
            },
        }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "error",
            "message": "Usage: python analyze_lens.py <image_path>",
        }))
        sys.exit(1)

    result = analyze_lens(sys.argv[1])
    print(json.dumps(result, indent=2))
