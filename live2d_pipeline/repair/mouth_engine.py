#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Procedural mouth generation and Live2D rig repair engine.

Solves the classic single-layer mouth rigging flaws:
1. Mouth tilt and sagging during speech interpolation.
2. Mesh tearing and aliasing at small sizes.
3. Double-lip ghosting by cleanly inpainting face skin behind the mouth.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from ..core.psd_io import read_layers, write_layers, clean_specks, find_layer
from ..core.utils import bezier2, bezier3, downsample_lanczos_premultiplied, hex_to_rgb


class MouthConfig:
    """Configurable visual parameters for procedural anime mouth."""

    def __init__(
        self,
        center_x: float,
        corner_y: float,
        width: float = 28.0,
        depth: float = 14.0,
        lift: float = 2.0,
        col_line: Tuple[int, int, int] = (142, 90, 93),
        col_int_top: Tuple[int, int, int] = (158, 94, 100),
        col_int_mid: Tuple[int, int, int] = (188, 116, 120),
        col_int_bot: Tuple[int, int, int] = (206, 136, 138),
        col_tooth: Tuple[int, int, int] = (244, 236, 234),
        col_tongue: Tuple[int, int, int] = (226, 146, 148),
        has_fang: bool = False,
        fang_side: str = "right",  # "left" or "right"
    ):
        self.cx = center_x
        self.corner_y = corner_y
        self.width = width
        self.depth = depth
        self.lift = lift
        self.col_line = col_line
        self.col_int_top = col_int_top
        self.col_int_mid = col_int_mid
        self.col_int_bot = col_int_bot
        self.col_tooth = col_tooth
        self.col_tongue = col_tongue
        self.has_fang = has_fang
        self.fang_side = fang_side


def generate_dual_mouth_art(
    face_patch_rgba: np.ndarray,
    lip_y_ratio: float = 0.50,
    rx_px: float = 16.0,
    depth_px: float = 11.0,
    lift_px: float = 2.0,
    lip_color: Tuple[int, int, int] = (158, 104, 102),
    inner_color: Tuple[int, int, int] = (184, 114, 118),
    dark_color: Tuple[int, int, int] = (140, 74, 82),
    tongue_color: Tuple[int, int, int] = (216, 144, 142),
    slit_color: Tuple[int, int, int] = (146, 92, 96),
    supersample: int = 8,
) -> Tuple[np.ndarray, np.ndarray]:
    """Generates (closed_lips_rgba, open_oral_rgba) on the skin patch canvas."""
    h, w = face_patch_rgba.shape[:2]
    SS = supersample
    W, H = w * SS, h * SS

    # 1. Closed lips art
    base_cl = Image.fromarray(face_patch_rgba[..., :3], "RGB").resize((W, H), Image.LANCZOS)
    d_cl = ImageDraw.Draw(base_cl)
    cx = W * 0.50
    y0 = H * lip_y_ratio
    rx = rx_px * SS
    lift = lift_px * SS
    N = 72

    lip_curve = [
        (cx - rx + 2 * rx * t / N, y0 - lift + lift * np.sin(np.pi * t / N))
        for t in range(N + 1)
    ]

    # Subtle dark slit right underneath the closed lip
    band = 0.85 * SS
    top_slit = [(x, y + 0.35 * SS) for x, y in lip_curve]
    bot_slit = [
        (x, y + 0.35 * SS + band * (0.3 + 0.7 * np.sin(np.pi * i / N)))
        for i, (x, y) in enumerate(lip_curve)
    ]
    d_cl.polygon(top_slit + bot_slit[::-1], fill=slit_color)
    d_cl.line(lip_curve, fill=lip_color, width=max(1, int(1.7 * SS)), joint="curve")
    for pt in (lip_curve[0], lip_curve[-1]):
        d_cl.ellipse([pt[0] - 0.85 * SS, pt[1] - 0.85 * SS, pt[0] + 0.85 * SS, pt[1] + 0.85 * SS], fill=lip_color)

    arr_cl = np.asarray(base_cl.resize((w, h), Image.BOX))
    closed_rgba = np.dstack([arr_cl, np.full((h, w), 255, dtype=np.uint8)])

    # 2. Open oral art
    base_op = Image.fromarray(face_patch_rgba[..., :3], "RGB").resize((W, H), Image.LANCZOS)
    d_op = ImageDraw.Draw(base_op)
    depth = depth_px * SS

    top_curve = lip_curve
    bot_curve = [
        (cx - rx + 2 * rx * t / N, y0 - lift + depth * (np.sin(np.pi * t / N) ** 0.62))
        for t in range(N + 1)
    ]

    # Fill cavity
    d_op.polygon(top_curve + bot_curve[::-1], fill=inner_color)
    # Upper rim inner dark band (soft gradient shadow)
    d_op.polygon(
        [(x, y + 0.25 * SS) for x, y in top_curve] + [(x, y + 1.1 * SS) for x, y in top_curve[::-1]],
        fill=dark_color,
    )
    # Tongue: flat, soft pink, hugging the bottom of the mouth
    d_op.ellipse(
        [cx - rx * 0.52, y0 - lift + depth * 0.40, cx + rx * 0.52, y0 - lift + depth * 0.92],
        fill=tongue_color,
    )
    # Upper lip line and lower lip boundary line
    d_op.line(top_curve, fill=lip_color, width=max(1, int(1.6 * SS)), joint="curve")
    d_op.line(
        bot_curve,
        fill=(int(lip_color[0] * 0.94), int(lip_color[1] * 0.94), int(lip_color[2] * 0.94)),
        width=max(1, int(1.0 * SS)),
        joint="curve",
    )

    arr_op = np.asarray(base_op.resize((w, h), Image.BOX))
    open_rgba = np.dstack([arr_op, np.full((h, w), 255, dtype=np.uint8)])

    return closed_rgba, open_rgba


def erase_face_lip_line(face_layer: Dict[str, Any], mouth_box: Tuple[int, int, int, int]) -> Dict[str, Any]:
    """Inpaints and cleans residual closed lip line on the face layer to avoid double lips."""
    x0, y0, x1, y1 = mouth_box
    fx, fy = face_layer["left"], face_layer["top"]
    rgba = face_layer["rgba"].copy()
    fh, fw = rgba.shape[:2]

    lx0 = max(0, x0 - fx)
    ly0 = max(0, y0 - fy)
    lx1 = min(fw, x1 - fx)
    ly1 = min(fh, y1 - fy)

    if lx1 <= lx0 or ly1 <= ly0:
        return face_layer

    # Take skin colors from surrounding margin
    top_row = rgba[max(0, ly0 - 2) : ly0, lx0:lx1, :3]
    bot_row = rgba[ly1 : min(fh, ly1 + 2), lx0:lx1, :3]
    if top_row.size > 0 and bot_row.size > 0:
        c_top = top_row.mean(axis=(0, 1))
        c_bot = bot_row.mean(axis=(0, 1))
        for row_i, y in enumerate(range(ly0, ly1)):
            factor = row_i / max(1, (ly1 - ly0 - 1))
            color = (1 - factor) * c_top + factor * c_bot
            rgba[y, lx0:lx1, :3] = color.astype(np.uint8)

    new_face = dict(face_layer)
    new_face["rgba"] = rgba
    return new_face


class MouthRepairEngine:
    """High-level interface for mouth reconstruction on PSDs."""

    @staticmethod
    def apply_dual_mouth(
        input_psd: str,
        output_psd: str,
        box: Tuple[int, int, int, int],
        lip_y: float = 0.50,
        rx: float = 16.0,
        depth: float = 11.0,
        lift: float = 2.0,
        preview_png: Optional[str] = None,
    ) -> str:
        """Injects dual-layer mouth (closed lips + open oral) into PSD."""
        layers, size, depth_b, cmode = read_layers(input_psd)
        face = find_layer(layers, "face")
        if not face:
            raise ValueError("No 'face' layer found in PSD.")

        x0, y0, x1, y1 = box
        fx, fy = face["left"], face["top"]
        lx0, ly0 = x0 - fx, y0 - fy
        lx1, ly1 = x1 - fx, y1 - fy

        face_rgba = face["rgba"]
        patch = face_rgba[ly0:ly1, lx0:lx1].copy()

        cl_rgba, op_rgba = generate_dual_mouth_art(
            patch,
            lip_y_ratio=lip_y,
            rx_px=rx,
            depth_px=depth,
            lift_px=lift,
        )

        # Inpaint face to remove old mouth line
        new_face = erase_face_lip_line(face, box)

        out_layers: List[Dict[str, Any]] = []
        mouth_inserted = False

        for l in layers:
            nm = l["name"].strip().lower()
            if nm == "face":
                out_layers.append(new_face)
                continue
            if nm in ("mouth", "lips", "oral", "上唇线", "下唇线", "口腔"):
                if not mouth_inserted:
                    out_layers.append({"name": "lips", "left": x0, "top": y0, "rgba": cl_rgba})
                    out_layers.append({"name": "oral", "left": x0, "top": y0, "rgba": op_rgba})
                    mouth_inserted = True
                continue
            out_layers.append(l)

        if not mouth_inserted:
            out_layers.insert(0, {"name": "lips", "left": x0, "top": y0, "rgba": cl_rgba})
            out_layers.insert(1, {"name": "oral", "left": x0, "top": y0, "rgba": op_rgba})

        if preview_png:
            w_px = (x1 - x0) * 4
            h_px = (y1 - y0) * 4
            canvas = Image.new("RGB", (w_px * 2 + 10, h_px), (255, 255, 255))
            canvas.paste(Image.fromarray(cl_rgba[..., :3]).resize((w_px, h_px), Image.LANCZOS), (0, 0))
            canvas.paste(Image.fromarray(op_rgba[..., :3]).resize((w_px, h_px), Image.LANCZOS), (w_px + 10, 0))
            canvas.save(preview_png)

        return write_layers(out_layers, size, output_psd, depth=depth_b, cmode=cmode)
