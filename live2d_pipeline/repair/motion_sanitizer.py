#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Motion curve sanitizer, Target validator, and speech amplitude optimizer."""

from typing import Any, Dict, List, Optional
import os
import glob
import json


class MotionSanitizer:
    """Sanitizes motion3.json files to prevent engine crashes and fix mouth/body distortions."""

    @staticmethod
    def sanitize_file(
        motion_path: str,
        fix_target_model: bool = True,
        lock_mouth_form_zero: bool = True,
        mouth_open_boost: float = 1.35,
        zero_nod_leg_distortion: bool = True,
    ) -> Dict[str, Any]:
        """Sanitizes a single motion3.json file.
        
        Returns summary of modifications.
        """
        with open(motion_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        is_talk = "talk" in os.path.basename(motion_path).lower()
        is_nod = "nod" in os.path.basename(motion_path).lower()

        modified = False
        target_fixes = 0
        total_segments = 0
        total_points = 0

        curves = data.get("Curves", [])
        for c in curves:
            # 1. Target check (Unity Cubism SDK crashes on Target: Model)
            if fix_target_model and c.get("Target") == "Model":
                c["Target"] = "Parameter"
                target_fixes += 1
                modified = True

            curve_id = c.get("Id", "")
            segments = c.get("Segments", [])

            # 2. Talk motion optimizations
            if is_talk:
                # Lock MouthForm to 0 to prevent sharp lower lip deformation
                if lock_mouth_form_zero and curve_id == "ParamMouthForm":
                    # Simple linear or flat curve at 0.0
                    c["Segments"] = [0.0, 0.0, 0, 3.6, 0.0]
                    modified = True

                # Boost MouthOpenY amplitude
                elif mouth_open_boost > 1.0 and curve_id == "ParamMouthOpenY":
                    new_segs = []
                    idx = 0
                    while idx < len(segments):
                        if idx in (0, 1):
                            new_segs.append(segments[idx] if idx == 0 else min(1.0, segments[idx] * mouth_open_boost))
                            idx += 1
                        else:
                            seg_type = int(segments[idx])
                            new_segs.append(seg_type)
                            idx += 1
                            if seg_type == 0:  # Linear: [time, val]
                                new_segs.append(segments[idx])
                                new_segs.append(min(1.0, segments[idx + 1] * mouth_open_boost))
                                idx += 2
                            elif seg_type == 1:  # Bezier: [t1, v1, t2, v2, t3, v3]
                                for k in range(3):
                                    new_segs.append(segments[idx])
                                    new_segs.append(min(1.0, segments[idx + 1] * mouth_open_boost))
                                    idx += 2
                            elif seg_type == 2:  # Stepped: [time, val]
                                new_segs.append(segments[idx])
                                new_segs.append(min(1.0, segments[idx + 1] * mouth_open_boost))
                                idx += 2
                            elif seg_type == 3:  # InverseStepped: [time, val]
                                new_segs.append(segments[idx])
                                new_segs.append(min(1.0, segments[idx + 1] * mouth_open_boost))
                                idx += 2
                    c["Segments"] = new_segs
                    modified = True

            # 3. Nod motion distortion dampening
            if is_nod and zero_nod_leg_distortion:
                if curve_id in ("ParamBodyAngleY", "ParamBodyAngleZ"):
                    # Zero out body rotation during nod so character legs don't pinch/shrink
                    c["Segments"] = [0.0, 0.0, 0, 1.0, 0.0]
                    modified = True

            # Count segments & points for Meta block
            segs = c.get("Segments", [])
            if len(segs) >= 2:
                idx = 2
                pts = 1
                seg_cnt = 0
                while idx < len(segs):
                    st = int(segs[idx])
                    idx += 1
                    seg_cnt += 1
                    if st == 1:
                        idx += 6
                        pts += 3
                    else:
                        idx += 2
                        pts += 1
                total_segments += seg_cnt
                total_points += pts

        # Update metadata counts
        if "Meta" in data:
            if total_segments > 0:
                data["Meta"]["TotalSegmentCount"] = total_segments
            if total_points > 0:
                data["Meta"]["TotalPointCount"] = total_points
            data["Meta"]["CurveCount"] = len(curves)

        with open(motion_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return {
            "path": motion_path,
            "modified": modified,
            "target_fixes": target_fixes,
        }

    @classmethod
    def sanitize_model_directory(cls, model_dir: str) -> List[Dict[str, Any]]:
        """Sanitizes all motion3.json files in a model directory."""
        results = []
        for p in glob.glob(os.path.join(model_dir, "**/*.motion3.json"), recursive=True):
            res = cls.sanitize_file(p)
            results.append(res)
        return results
