#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for procedural mouth generation and skin inpainting."""

import unittest
import numpy as np

from live2d_pipeline.repair.mouth_engine import generate_dual_mouth_art, erase_face_lip_line


class TestMouthEngine(unittest.TestCase):
    def test_generate_dual_mouth_shapes(self):
        patch = np.full((30, 40, 4), 255, dtype=np.uint8)
        patch[..., 0] = 245
        patch[..., 1] = 220
        patch[..., 2] = 215

        closed_rgba, open_rgba = generate_dual_mouth_art(
            patch,
            lip_y_ratio=0.5,
            rx_px=14.0,
            depth_px=10.0,
            lift_px=2.0,
        )

        self.assertEqual(closed_rgba.shape, (30, 40, 4))
        self.assertEqual(open_rgba.shape, (30, 40, 4))
        self.assertEqual(closed_rgba[..., 3].min(), 255)
        self.assertEqual(open_rgba[..., 3].min(), 255)

    def test_erase_face_lip_line(self):
        face_rgba = np.full((100, 100, 4), 240, dtype=np.uint8)
        face_rgba[50, 40:60, :3] = 50

        face_layer = {
            "name": "face",
            "left": 0,
            "top": 0,
            "rgba": face_rgba,
        }

        repaired = erase_face_lip_line(face_layer, mouth_box=(35, 45, 65, 55))
        rep_rgba = repaired["rgba"]

        self.assertGreater(rep_rgba[50, 50, 0], 200)


if __name__ == "__main__":
    unittest.main()
