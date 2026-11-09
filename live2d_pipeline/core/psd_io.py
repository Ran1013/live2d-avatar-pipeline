#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PSD I/O engine with fixes for NumPy 2.x and pytoshop 1.2.1 packbits decompression."""

from typing import Any, Dict, List, Optional, Tuple
import types
import numpy as np

# Apply monkey-patches to pytoshop before importing its codecs
def _unpackbits_row(src: bytes, expected: int) -> bytes:
    dst = bytearray()
    i = 0
    while i < len(src) and len(dst) < expected:
        n = src[i]
        i += 1
        if n < 128:
            dst += src[i : i + n + 1]
            i += n + 1
        elif n > 128:
            dst += bytes([src[i]]) * (257 - n)
            i += 1
    return bytes(dst)


def _decode(data: bytes, height: int, width: int, depth_size: int, version: int = 1) -> bytes:
    out = bytearray()
    pos = 0
    step = 4 if version == 2 else 2
    sizes = [
        int.from_bytes(data[pos + i * step : pos + (i + 1) * step], "big")
        for i in range(height)
    ]
    pos += step * height
    for n in sizes:
        out += _unpackbits_row(data[pos : pos + n], width)
        pos += n
    return bytes(out)


try:
    import pytoshop
    import pytoshop.codecs as _codecs
    _codecs.packbits = types.SimpleNamespace(decode=_decode)
    from pytoshop.enums import ColorChannel, ColorMode, Compression
    from pytoshop.user import nested_layers as nl
    nl._fix_user_layer_mask_size = lambda *a, **k: None
except ImportError:
    pytoshop = None  # Handled gracefully if pytoshop is missing

CHANNELS = (
    getattr(pytoshop.enums.ColorChannel, "red", None) if pytoshop else None,
    getattr(pytoshop.enums.ColorChannel, "green", None) if pytoshop else None,
    getattr(pytoshop.enums.ColorChannel, "blue", None) if pytoshop else None,
    getattr(pytoshop.enums.ColorChannel, "transparency", None) if pytoshop else None,
)


def _chan(layer: Any, idx: int) -> np.ndarray:
    ch = layer.get_channel(CHANNELS[idx])
    arr = np.asarray(getattr(ch, "image", ch))
    if arr.ndim == 3:
        arr = arr[..., 0]
    return arr.astype(np.uint8)


def read_layers(path: str) -> Tuple[List[Dict[str, Any]], Tuple[int, int], int, Any]:
    """Reads a PSD file and returns its layers ordered top to bottom.
    
    Returns:
        (layers, size, depth, color_mode)
        where each layer is a dict: {'name': str, 'left': int, 'top': int, 'rgba': np.ndarray}
    """
    if pytoshop is None:
        raise RuntimeError("pytoshop is required to read PSD files. Install via pip install pytoshop.")

    with open(path, "rb") as f:
        psd = pytoshop.read(f)
        raw_layers = nl.psd_to_nested_layers(psd)
        layers = []
        for l in raw_layers:
            name = l.name.decode("utf-8", "replace") if isinstance(l.name, bytes) else str(l.name)
            name = name.replace("\x00", "").strip()
            h = int(l.bottom) - int(l.top)
            w = int(l.right) - int(l.left)
            if h <= 0 or w <= 0:
                continue
            rgba = np.zeros((h, w, 4), dtype=np.uint8)
            for i in range(4):
                try:
                    rgba[..., i] = _chan(l, i)
                except Exception:
                    rgba[..., i] = 255 if i == 3 else 0
            layers.append({
                "name": name,
                "left": int(l.left),
                "top": int(l.top),
                "rgba": rgba,
            })
        size = (psd.width, psd.height)
        depth = psd.depth
        cmode = psd.color_mode
    return layers, size, depth, cmode


def _make_layer(name: str, left: int, top: int, rgba: np.ndarray) -> Any:
    h, w = rgba.shape[:2]
    layer = nl.Image(
        name=name,
        left=int(left),
        top=int(top),
        right=int(left) + w,
        bottom=int(top) + h,
        color_mode=ColorMode.rgb,
    )
    for i in range(4):
        layer.set_channel(CHANNELS[i], np.ascontiguousarray(rgba[..., i]))
    return layer


def write_layers(
    layers: List[Dict[str, Any]],
    size: Tuple[int, int],
    out_path: str,
    depth: int = 8,
    cmode: Any = None,
    compress: bool = False,
) -> str:
    """Writes a list of layer dicts to a PSD file.
    
    Empty (all-transparent) layers are automatically skipped.
    """
    if pytoshop is None:
        raise RuntimeError("pytoshop is required to write PSD files. Install via pip install pytoshop.")

    if cmode is None:
        cmode = ColorMode.rgb

    objs = []
    for l in layers:
        rgba = l["rgba"]
        m = rgba[..., 3] > 0
        if not m.any():
            continue  # Discard fully transparent layers
        ys, xs = np.where(m)
        y0, y1 = ys.min(), ys.max() + 1
        x0, x1 = xs.min(), xs.max() + 1
        crop = np.ascontiguousarray(rgba[y0:y1, x0:x1])
        name = l["name"].decode("utf-8", "replace") if isinstance(l["name"], bytes) else str(l["name"])
        objs.append(_make_layer(name, l["left"] + x0, l["top"] + y0, crop))

    compression_mode = Compression.rle if compress else Compression.raw
    psd = nl.nested_layers_to_psd(
        objs,
        color_mode=cmode,
        compression=compression_mode,
        depth=depth,
        size=size,
    )
    with open(out_path, "wb") as g:
        psd.write(g)
    return out_path


def clean_specks(rgba: np.ndarray, keep_ratio: float = 0.10, min_abs: int = 30) -> np.ndarray:
    """Removes stray disconnected noise pixels and cleans transparent RGB."""
    try:
        from scipy import ndimage
    except ImportError:
        return rgba

    a = rgba[..., 3]
    mask = a > 8
    if not mask.any():
        return rgba
    lab, n = ndimage.label(mask, structure=np.ones((3, 3)))
    if n > 1:
        sizes = ndimage.sum(mask, lab, range(1, n + 1))
        thr = max(min_abs, sizes.max() * keep_ratio)
        keep = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s >= thr])
        rgba = rgba.copy()
        rgba[..., 3] = np.where(keep, a, 0)
    rgba = rgba.copy()
    rgba[rgba[..., 3] == 0] = 0
    return rgba


def to_canvas(layers: List[Dict[str, Any]], size: Tuple[int, int]) -> np.ndarray:
    """Composites layers top-to-bottom onto a single canvas RGBA array."""
    W, H = size
    out = np.zeros((H, W, 4), dtype=np.uint8)
    for l in reversed(layers):
        rgba = l["rgba"]
        h, w = rgba.shape[:2]
        x0, y0 = l["left"], l["top"]
        x1, y1 = x0 + w, y0 + h
        sx0, sy0 = max(0, -x0), max(0, -y0)
        x0c, y0c = max(0, x0), max(0, y0)
        x1c, y1c = min(W, x1), min(H, y1)
        if x1c <= x0c or y1c <= y0c:
            continue
        src = rgba[sy0 : sy0 + (y1c - y0c), sx0 : sx0 + (x1c - x0c)]
        sub = out[y0c:y1c, x0c:x1c].astype(np.float32)
        sa = src[..., 3:4].astype(np.float32) / 255.0
        da = sub[..., 3:4] / 255.0
        oa = sa + da * (1 - sa)
        rgb = np.where(
            oa > 0,
            (src[..., :3] * sa + sub[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-6),
            sub[..., :3],
        )
        out[y0c:y1c, x0c:x1c] = np.dstack([rgb, oa[..., 0] * 255]).astype(np.uint8)
    return out


def find_layer(layers: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    """Finds a layer by name (case-insensitive, whitespace-trimmed)."""
    norm = name.strip().lower()
    for l in layers:
        if l["name"].strip().lower() == norm:
            return l
    return None
