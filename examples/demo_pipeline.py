#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example script demonstrating Python API usage of live2d-avatar-pipeline."""

import os
import sys

from live2d_pipeline.splitter.cleaner import clean_all_layers
from live2d_pipeline.splitter.layer_sorter import sort_layers
from live2d_pipeline.repair.mouth_engine import MouthRepairEngine
from live2d_pipeline.repair.eye_engine import EyeRepairEngine
from live2d_pipeline.repair.motion_sanitizer import MotionSanitizer
from live2d_pipeline.qa.model_checker import ModelChecker
from live2d_pipeline.qa.pca_tilt import calculate_tilt_angle_pca


def main():
    print("=== Live2D Avatar Pipeline Demo ===")

    # 1. Demonstrate PCA Mouth Tilt Calculation
    import numpy as np
    # Perfectly level mouth points
    level_points = np.array([[620, 230], [630, 230], [640, 230], [650, 230]])
    angle = calculate_tilt_angle_pca(level_points)
    print(f"[*] PCA Tilt Angle on Level Lip Line: {angle:.2f}° (Expected ~0.00°)")

    # 2. Demonstrate Motion Curve Sanitizer logic
    dummy_motion = {
        "Version": 3,
        "Meta": {"Duration": 3.6, "Fps": 30.0, "CurveCount": 2},
        "Curves": [
            {
                "Target": "Model",  # Invalid target that causes Unity/VTS crash
                "Id": "ParamMouthOpenY",
                "Segments": [0.0, 0.0, 0, 3.6, 0.5],
            },
            {
                "Target": "Parameter",
                "Id": "ParamMouthForm",
                "Segments": [0.0, 0.8, 0, 3.6, 0.4],  # Non-zero causing sharp lip
            },
        ],
    }
    
    tmp_motion_path = "/tmp/demo_motion.motion3.json"
    import json
    with open(tmp_motion_path, "w", encoding="utf-8") as f:
        json.dump(dummy_motion, f)

    print(f"[*] Created demo motion with Target='Model' and non-zero MouthForm at {tmp_motion_path}")
    res = MotionSanitizer.sanitize_file(tmp_motion_path, mouth_open_boost=1.4)
    print(f"[+] Sanitization result: {res}")

    with open(tmp_motion_path, "r", encoding="utf-8") as f:
        sanitized = json.load(f)

    print(f"[+] Sanitized Target: {sanitized['Curves'][0]['Target']} (Target='Model' successfully resolved!)")
    print(f"[+] Sanitized MouthForm Segments: {sanitized['Curves'][1]['Segments']} (Locked to 0.0)")

    print("\n[✓] Demo completed successfully!")


if __name__ == "__main__":
    main()
