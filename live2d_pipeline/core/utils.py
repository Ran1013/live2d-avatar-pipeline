#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Geometry, color, and image resampling utilities."""

from typing import List, Tuple, Union
import numpy as np
from PIL import Image


def bezier2(p0: Tuple[float, float], c: Tuple[float, float], p1: Tuple[float, float], n: int = 72) -> List[Tuple[float, float]]:
    """Generates n points along a quadratic Bezier curve."""
    ts = np.linspace(0, 1, n)
    return [
        (
            float((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t ** 2 * p1[0]),
            float((1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t ** 2 * p1[1]),
        )
        for t in ts
    ]


def bezier3(
    p0: Tuple[float, float],
    c1: Tuple[float, float],
    c2: Tuple[float, float],
    p1: Tuple[float, float],
    n: int = 120,
) -> List[Tuple[float, float]]:
    """Generates n points along a cubic Bezier curve."""
    ts = np.linspace(0, 1, n)
    out = []
    for t in ts:
        mt = 1 - t
        x = mt ** 3 * p0[0] + 3 * mt * mt * t * c1[0] + 3 * mt * t * t * c2[0] + t ** 3 * p1[0]
        y = mt ** 3 * p0[1] + 3 * mt * mt * t * c1[1] + 3 * mt * t * t * c2[1] + t ** 3 * p1[1]
        out.append((float(x), float(y)))
    return out


def downsample_lanczos_premultiplied(im: Image.Image, scale_factor: int = 8) -> Image.Image:
    """Downsamples an image using premultiplied alpha with LANCZOS filter.
    
    Prevents dark fringing or halo artifacts on translucent edges.
    """
    if scale_factor <= 1:
        return im

    arr = np.array(im, dtype=np.float32)
    if arr.ndim == 2:
        return im.resize((im.width // scale_factor, im.height // scale_factor), Image.LANCZOS)

    if arr.shape[2] == 3:
        return im.resize((im.width // scale_factor, im.height // scale_factor), Image.LANCZOS)

    alpha = arr[..., 3:4] / 255.0
    premult = np.concatenate([arr[..., :3] * alpha, arr[..., 3:4]], axis=2).astype(np.uint8)
    sim = Image.fromarray(premult, "RGBA").resize(
        (im.width // scale_factor, im.height // scale_factor),
        Image.LANCZOS,
    )
    p = np.asarray(sim).astype(np.float32)
    al = p[..., 3:4] / 255.0
    rgb = np.where(al > 1e-4, p[..., :3] / np.maximum(al, 1e-4), 0)
    final = np.concatenate([rgb, p[..., 3:4]], axis=2).clip(0, 255).astype(np.uint8)
    return Image.fromarray(final, "RGBA")


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Converts a hex color string ('#RRGGBB' or 'RRGGBB') to an (R, G, B) tuple."""
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join(c * 2 for c in hex_str)
    return int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """Converts an (R, G, B) tuple to a '#RRGGBB' string."""
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
