#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for QA and PCA tilt calculation."""

import unittest
import numpy as np

from live2d_pipeline.qa.pca_tilt import calculate_tilt_angle_pca


class TestQA(unittest.TestCase):
    def test_pca_tilt_horizontal(self):
        pts = np.array([[10, 50], [20, 50], [30, 50], [40, 50]], dtype=float)
        angle = calculate_tilt_angle_pca(pts)
        self.assertLess(abs(angle), 0.01)

    def test_pca_tilt_slanted(self):
        pts = np.array([[10, 10], [20, 20], [30, 30], [40, 40]], dtype=float)
        angle = calculate_tilt_angle_pca(pts)
        self.assertLess(abs(angle - 45.0), 0.1)


if __name__ == "__main__":
    unittest.main()
