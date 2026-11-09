#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Layer cleanup, speck removal, and bounding box tightening."""

from typing import Any, Dict, List, Tuple
import numpy as np
from ..core.psd_io import clean_specks


def tighten_layer_bbox(layer: Dict[str, Any], min_alpha: int = 5) -> Dict[str, Any]:
    """Tightens the bounding box of a layer around its non-transparent pixels."""
    rgba = layer["rgba"]
    m = rgba[..., 3] >= min_alpha
    if not m.any():
        return layer

    ys, xs = np.where(m)
    y0, y1 = int(ys.min()), int(ys.max() + 1)
    x0, x1 = int(xs.min()), int(xs.max() + 1)

    crop = rgba[y0:y1, x0:x1].copy()
    new_layer = dict(layer)
    new_layer["left"] = layer["left"] + x0
    new_layer["top"] = layer["top"] + y0
    new_layer["rgba"] = crop
    return new_layer


def clean_layer(
    layer: Dict[str, Any],
    clean_speckles: bool = True,
    tighten_box: bool = True,
    min_alpha: int = 8,
) -> Dict[str, Any]:
    """Cleans specks, removes stray noise, and tightens bounding boxes for a single layer."""
    rgba = layer["rgba"].copy()
    # Zero out low alpha noise
    rgba[rgba[..., 3] < min_alpha] = 0

    if clean_speckles:
        # Don't clean specks on thin feature layers like eyelashes, lips, or nose
        name_lower = layer["name"].lower()
        if not any(k in name_lower for k in ["lip", "mouth", "nose", "lash", "brow"]):
            rgba = clean_specks(rgba, keep_ratio=0.08, min_abs=25)

    res = dict(layer)
    res["rgba"] = rgba
    if tighten_box:
        res = tighten_layer_bbox(res, min_alpha=min_alpha)
    return res


def clean_all_layers(layers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Runs cleaning across all layers."""
    return [clean_layer(l) for l in layers]
