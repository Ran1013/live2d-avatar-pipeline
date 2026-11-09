#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PCA tilt and symmetry analyzer for mouth and facial features."""

from typing import List, Tuple
import numpy as np


def calculate_tilt_angle_pca(points: np.ndarray) -> float:
    """Calculates the tilt angle (in degrees) of a set of 2D coordinates using PCA.
    
    A perfectly horizontal feature (like a level mouth line) returns 0.0 degrees.
    Positive indicates counter-clockwise tilt, negative indicates clockwise tilt.
    """
    if len(points) < 2:
        return 0.0

    pts = np.asarray(points, dtype=np.float64)
    # Center points
    centered = pts - pts.mean(axis=0)

    # Covariance matrix
    cov = np.cov(centered, rowvar=False)
    evals, evecs = np.linalg.eigh(cov)

    # Principal component direction
    principal = evecs[:, np.argmax(evals)]

    # Calculate angle with horizontal x-axis
    angle_rad = np.arctan2(principal[1], principal[0])
    angle_deg = np.degrees(angle_rad)

    # Normalize angle to range [-90, 90]
    if angle_deg > 90:
        angle_deg -= 180
    elif angle_deg < -90:
        angle_deg += 180

    return float(angle_deg)


def evaluate_mouth_symmetry(
    left_points: np.ndarray,
    right_points: np.ndarray,
    center_x: float,
) -> float:
    """Calculates symmetry error between left and right mouth contours mirrored across center_x."""
    mirrored_left = left_points.copy()
    mirrored_left[:, 0] = 2 * center_x - mirrored_left[:, 0]
    min_len = min(len(mirrored_left), len(right_points))
    diff = np.abs(mirrored_left[:min_len] - right_points[:min_len])
    return float(np.mean(diff))
