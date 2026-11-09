#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""High-fidelity anime eye reconstruction and close-eye swap layer generation."""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from ..core.psd_io import read_layers, write_layers, clean_specks, find_layer
from ..core.utils import bezier3, downsample_lanczos_premultiplied


def generate_close_eye_lashes(
    p0: Tuple[float, float],
    c1: Tuple[float, float],
    c2: Tuple[float, float],
    p1: Tuple[float, float],
    stroke_width: int = 14,
    color: Tuple[int, int, int] = (45, 24, 20),
    canvas_size: Tuple[int, int] = (320, 240),
    supersample: int = 8,
) -> np.ndarray:
    """Generates natural closed-eye curved eyelashes via cubic Bezier with 8x supersampling."""
    S = supersample
    W, H = canvas_size[0] * S, canvas_size[1] * S
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    p0_s = (p0[0] * S, p0[1] * S)
    c1_s = (c1[0] * S, c1[1] * S)
    c2_s = (c2[0] * S, c2[1] * S)
    p1_s = (p1[0] * S, p1[1] * S)

    pts = bezier3(p0_s, c1_s, c2_s, p1_s, n=120)
    d.line(pts, fill=color + (255,), width=stroke_width, joint="curve")

    # Gentle corner tapering
    d.ellipse([p0_s[0] - stroke_width // 2, p0_s[1] - stroke_width // 2,
               p0_s[0] + stroke_width // 2, p0_s[1] + stroke_width // 2], fill=color + (255,))
    d.ellipse([p1_s[0] - stroke_width // 2, p1_s[1] - stroke_width // 2,
               p1_s[0] + stroke_width // 2, p1_s[1] + stroke_width // 2], fill=color + (255,))

    down = downsample_lanczos_premultiplied(im, S)
    return np.asarray(down)


class EyeRepairEngine:
    """Engine for iris enhancement and closed-eye swap layer generation."""

    @staticmethod
    def add_close_eye_swap_layers(
        input_psd: str,
        output_psd: str,
        left_eye_coords: Optional[Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float], Tuple[float, float]]] = None,
        right_eye_coords: Optional[Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float], Tuple[float, float]]] = None,
        lash_color: Tuple[int, int, int] = (45, 24, 20),
    ) -> str:
        """Injects `eye_close-l` and `eye_close-r` layers into PSD to activate PSD2Live SWAP mode.
        
        When `eye_close` layers exist, PSD2Live automatically replaces the open eye mesh
        with the closed eyelash curve at eye openness <= 0.06 instead of squishing and
        distorting the open eyelash mesh.
        """
        layers, size, depth, cmode = read_layers(input_psd)
        lash_l = find_layer(layers, "eyelash-l")
        lash_r = find_layer(layers, "eyelash-r")

        out_layers: List[Dict[str, Any]] = []

        for l in layers:
            name = l["name"].strip()
            out_layers.append(l)

            # Insert eye_close-l right after eyelash-l if not already present
            if name == "eyelash-l" and not find_layer(layers, "eye_close-l"):
                box_w = l["rgba"].shape[1] + 8
                box_h = l["rgba"].shape[0] + 8
                pts = left_eye_coords or ((4, 6), (box_w * 0.35, box_h * 0.8), (box_w * 0.7, box_h * 0.8), (box_w - 4, 10))
                arr = generate_close_eye_lashes(pts[0], pts[1], pts[2], pts[3], canvas_size=(box_w, box_h), color=lash_color)
                out_layers.append({
                    "name": "eye_close-l",
                    "left": l["left"] - 4,
                    "top": l["top"] - 4,
                    "rgba": arr,
                })

            # Insert eye_close-r right after eyelash-r if not already present
            if name == "eyelash-r" and not find_layer(layers, "eye_close-r"):
                box_w = l["rgba"].shape[1] + 8
                box_h = l["rgba"].shape[0] + 8
                pts = right_eye_coords or ((4, 10), (box_w * 0.3, box_h * 0.8), (box_w * 0.65, box_h * 0.8), (box_w - 4, 6))
                arr = generate_close_eye_lashes(pts[0], pts[1], pts[2], pts[3], canvas_size=(box_w, box_h), color=lash_color)
                out_layers.append({
                    "name": "eye_close-r",
                    "left": l["left"] - 4,
                    "top": l["top"] - 4,
                    "rgba": arr,
                })

        return write_layers(out_layers, size, output_psd, depth=depth, cmode=cmode)
