#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Layer splitting interface (API and local assembly)."""

from typing import Any, Dict, List, Optional, Tuple
import os
import glob
import numpy as np
from PIL import Image

from ..core.psd_io import read_layers, write_layers
from .layer_sorter import sort_layers
from .cleaner import clean_all_layers


# Default 24-layer sequence used by anime layer decomposition models
DEFAULT_LAYER_NAMES = [
    "front hair", "irides-l", "irides-r", "eyelash-r", "eyewhite-l", "eyewhite-r",
    "eyelash-l", "mouth", "nose", "face", "ears-l", "ears-r",
    "eyebrow-l", "topwear", "eyebrow-r", "bottomwear", "neck", "footwear",
    "legwear", "headwear", "handwear-r", "handwear-l", "back hair", "tail"
]


class LayerSplitter:
    """Manages layer splitting and PSD assembly."""

    def __init__(self, hf_token: Optional[str] = None):
        self.hf_token = hf_token or os.environ.get("HF_TOKEN")

    def split_via_gradio(
        self,
        image_path: str,
        space_id: str = "fexas25/see-through",
        tblr_split: bool = True,
    ) -> Optional[str]:
        """Calls Hugging Face Space Gradio API to decompose a flat image into layers.
        
        Returns path to the downloaded PSD if successful.
        """
        try:
            from gradio_client import Client
        except ImportError:
            raise RuntimeError("gradio_client is required for online layer splitting. Run: pip install gradio_client")

        client = Client(space_id, hf_token=self.hf_token)
        result = client.predict(
            image=image_path,
            tblr_split=tblr_split,
            api_name="/predict",
        )
        return str(result)

    def assemble_from_directory(
        self,
        dir_path: str,
        out_psd: str,
        canvas_size: Optional[Tuple[int, int]] = None,
    ) -> str:
        """Assembles isolated PNG files in a folder into a standardized Live2D-ready PSD."""
        png_files = sorted(glob.glob(os.path.join(dir_path, "*.png")))
        if not png_files:
            raise FileNotFoundError(f"No PNG files found in {dir_path}")

        layers: List[Dict[str, Any]] = []
        max_w, max_h = 0, 0

        for idx, f in enumerate(png_files):
            fname = os.path.basename(f)
            base = os.path.splitext(fname)[0]
            # Match layer_00.png or use filename directly
            if base.startswith("layer_") and base.replace("layer_", "").isdigit():
                num = int(base.replace("layer_", ""))
                name = DEFAULT_LAYER_NAMES[num] if num < len(DEFAULT_LAYER_NAMES) else f"layer_{num}"
            else:
                name = base

            im = Image.open(f).convert("RGBA")
            max_w = max(max_w, im.width)
            max_h = max(max_h, im.height)
            rgba = np.array(im, dtype=np.uint8)

            layers.append({
                "name": name,
                "left": 0,
                "top": 0,
                "rgba": rgba,
            })

        size = canvas_size or (max_w, max_h)
        # Clean specks & tighten bounding boxes
        cleaned = clean_all_layers(layers)
        # Apply standard draw order
        sorted_layers = sort_layers(cleaned)
        # Write PSD
        return write_layers(sorted_layers, size, out_psd)

    def normalize_psd(self, input_psd: str, output_psd: str) -> str:
        """Normalizes an existing PSD: repairs layer order, cleans stray noise, and tightens boundaries."""
        layers, size, depth, cmode = read_layers(input_psd)
        cleaned = clean_all_layers(layers)
        sorted_layers = sort_layers(cleaned)
        return write_layers(sorted_layers, size, output_psd, depth=depth, cmode=cmode)
