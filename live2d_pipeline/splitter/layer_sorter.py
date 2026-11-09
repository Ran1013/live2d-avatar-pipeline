#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Live2D layer sorting and hierarchy enforcement."""

from typing import Any, Dict, List, Optional
import re

# Standard layer hierarchy from front (0) to back (N)
STANDARD_ORDER_PRIORITY = [
    # Forefront accessories & hair
    "front hair",
    "bangs",
    "刘海",
    "前发",
    "headwear",
    "hairpin",
    "发饰",
    "头饰",
    # Eye close replacement layers (for SWAP mechanism)
    "eye_close-l",
    "eye_close-r",
    # Eyebrows & eyelashes
    "eyebrow-l",
    "eyebrow-r",
    "眉毛-左",
    "眉毛-右",
    "eyelash-l",
    "eyelash-r",
    "睫毛-左",
    "睫毛-右",
    # Irises & eye highlights
    "irides-l",
    "irides-r",
    "眼珠-左",
    "眼珠-右",
    "虹膜-左",
    "虹膜-右",
    # Eye whites
    "eyewhite-l",
    "eyewhite-r",
    "眼白-左",
    "眼白-右",
    # Nose & mouth stack
    "nose",
    "鼻子",
    "上唇线",
    "下唇线",
    "上牙",
    "下牙",
    "舌头",
    "口腔",
    "oral",
    "lips",
    "mouth",
    "嘴巴",
    # Face & ears
    "face",
    "脸",
    "头部",
    "ears-l",
    "ears-r",
    "耳朵-左",
    "耳朵-右",
    # Neck & hands (hands MUST be placed above topwear)
    "handwear-l",
    "handwear-r",
    "手套-左",
    "手套-右",
    "手臂-左",
    "手臂-右",
    "neck",
    "脖子",
    "颈部",
    # Body garments
    "topwear",
    "上衣",
    "外套",
    "衣服",
    "bottomwear",
    "裙子",
    "短裙",
    "裤子",
    "下装",
    "legwear",
    "腿部",
    "大腿",
    "袜子",
    "footwear",
    "鞋子",
    "靴子",
    # Background hair & back elements
    "back hair",
    "后发",
    "后头发",
    "马尾",
]


def get_layer_priority(name: str) -> int:
    """Returns the priority score for a layer (lower score = drawn further in front)."""
    clean_name = name.lower().strip()
    for idx, key in enumerate(STANDARD_ORDER_PRIORITY):
        if key in clean_name or clean_name == key:
            return idx
    # Default priority for unrecognized layers (placed in middle-rear)
    return len(STANDARD_ORDER_PRIORITY) + 10


def sort_layers(layers: List[Dict[str, Any]], remove_ghost_layers: bool = True) -> List[Dict[str, Any]]:
    """Sorts layers into valid Live2D draw order.
    
    Ensures:
      1. Eyes: eyelash -> irides -> eyewhite
      2. Hands: handwear is above topwear (never clipped underneath jacket)
      3. Hair: front hair is in front of face, back hair is at the bottom
      4. Junk layers (e.g. ghost 'tail' layers with grey halos) are eliminated
    """
    cleaned: List[Dict[str, Any]] = []
    for l in layers:
        name = l["name"].strip()
        # Filter ghost or corrupt artifact layers
        if remove_ghost_layers and name.lower() in ("tail", "尾巴", "ghost", "artifact"):
            continue
        cleaned.append(l)

    # Sort stably based on priority
    return sorted(cleaned, key=lambda x: get_layer_priority(x["name"]))
