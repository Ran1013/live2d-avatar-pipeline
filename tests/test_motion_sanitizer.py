#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for MotionSanitizer."""

import json
import os
import tempfile
import unittest

from live2d_pipeline.repair.motion_sanitizer import MotionSanitizer


class TestMotionSanitizer(unittest.TestCase):
    def test_sanitize_motion_target_and_form(self):
        dummy = {
            "Version": 3,
            "Meta": {"Duration": 3.6, "Fps": 30.0, "CurveCount": 2},
            "Curves": [
                {
                    "Target": "Model",
                    "Id": "ParamMouthOpenY",
                    "Segments": [0.0, 0.0, 0, 3.6, 0.5],
                },
                {
                    "Target": "Parameter",
                    "Id": "ParamMouthForm",
                    "Segments": [0.0, 0.8, 0, 3.6, 0.4],
                },
            ],
        }

        with tempfile.NamedTemporaryFile("w", suffix="talk.motion3.json", delete=False) as f:
            json.dump(dummy, f)
            path = f.name

        try:
            res = MotionSanitizer.sanitize_file(path, fix_target_model=True, lock_mouth_form_zero=True)
            self.assertTrue(res["modified"])
            self.assertEqual(res["target_fixes"], 1)

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertEqual(data["Curves"][0]["Target"], "Parameter")
            self.assertEqual(data["Curves"][1]["Segments"], [0.0, 0.0, 0, 3.6, 0.0])
            self.assertGreaterEqual(data["Meta"]["TotalSegmentCount"], 2)
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    unittest.main()
