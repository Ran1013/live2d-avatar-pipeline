#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Live2D Avatar Pipeline CLI."""

import argparse
import sys
import os
import json

try:
    from .core.p2l_client import P2LClient
    from .splitter.layer_splitter import LayerSplitter
    from .repair.mouth_engine import MouthRepairEngine
    from .repair.eye_engine import EyeRepairEngine
    from .repair.motion_sanitizer import MotionSanitizer
    from .rigger.auto_rigger import AutoRigger
    from .qa.model_checker import ModelChecker
except ImportError:
    # Support direct execution
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if pkg_root not in sys.path:
        sys.path.insert(0, pkg_root)
    from live2d_pipeline.core.p2l_client import P2LClient
    from live2d_pipeline.splitter.layer_splitter import LayerSplitter
    from live2d_pipeline.repair.mouth_engine import MouthRepairEngine
    from live2d_pipeline.repair.eye_engine import EyeRepairEngine
    from live2d_pipeline.repair.motion_sanitizer import MotionSanitizer
    from live2d_pipeline.rigger.auto_rigger import AutoRigger
    from live2d_pipeline.qa.model_checker import ModelChecker


def cmd_split(args: argparse.Namespace) -> int:
    splitter = LayerSplitter()
    if os.path.isdir(args.input):
        print(f"[*] Assembling PNG layers from folder: {args.input}")
        out = splitter.assemble_from_directory(args.input, args.output)
        print(f"[+] Output PSD created: {out}")
    elif args.input.endswith(".psd"):
        print(f"[*] Normalizing layer order & cleaning specks in PSD: {args.input}")
        out = splitter.normalize_psd(args.input, args.output)
        print(f"[+] Normalized PSD saved: {out}")
    else:
        print(f"[*] Splitting image via See-through API: {args.input}")
        out = splitter.split_via_gradio(args.input)
        if out:
            print(f"[+] Split PSD received: {out}")
        else:
            print("[-] API splitting returned no result.")
            return 1
    return 0


def cmd_repair_mouth(args: argparse.Namespace) -> int:
    box = (args.x0, args.y0, args.x1, args.y1)
    print(f"[*] Generating procedural dual mouth for {args.input} within box {box}...")
    out = MouthRepairEngine.apply_dual_mouth(
        input_psd=args.input,
        output_psd=args.output,
        box=box,
        rx=args.rx,
        depth=args.depth,
        preview_png=args.preview,
    )
    print(f"[+] Repaired PSD written: {out}")
    if args.preview:
        print(f"[+] Preview image saved: {args.preview}")
    return 0


def cmd_repair_eyes(args: argparse.Namespace) -> int:
    print(f"[*] Adding close-eye swap layers into {args.input}...")
    out = EyeRepairEngine.add_close_eye_swap_layers(
        input_psd=args.input,
        output_psd=args.output,
    )
    print(f"[+] Repaired PSD written: {out}")
    return 0


def cmd_sanitize_motion(args: argparse.Namespace) -> int:
    if os.path.isdir(args.path):
        print(f"[*] Sanitizing all motions in directory: {args.path}")
        results = MotionSanitizer.sanitize_model_directory(args.path)
        print(f"[+] Processed {len(results)} motion files.")
    else:
        print(f"[*] Sanitizing motion file: {args.path}")
        res = MotionSanitizer.sanitize_file(args.path, mouth_open_boost=args.boost)
        print(f"[+] Sanitized: {res}")
    return 0


def cmd_rig(args: argparse.Namespace) -> int:
    roles = {}
    if args.roles and os.path.exists(args.roles):
        with open(args.roles, "r", encoding="utf-8") as f:
            roles = json.load(f)

    rigger = AutoRigger(roles_config=roles)
    print(f"[*] Rigging model from {args.psd} -> {args.out_dir}...")
    res = rigger.rig_and_export(
        psd_path=args.psd,
        output_dir=args.out_dir,
        atlas_budget=args.atlas,
        mouth_open_boost=args.boost,
    )
    print(f"[+] Rigging completed: {res}")
    return 0


def cmd_qa(args: argparse.Namespace) -> int:
    print(f"[*] Checking model integrity for: {args.model_dir}")
    report = ModelChecker.inspect_model_directory(args.model_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("valid") else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="avatar-pipeline",
        description="Live2D Avatar Pipeline: Layer Splitting, Auto-Rigging & Repair Toolkit",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Split
    p_split = subparsers.add_parser("split", help="Split image or assemble layers into PSD")
    p_split.add_argument("input", help="Path to input image, folder of layer PNGs, or PSD to normalize")
    p_split.add_argument("-o", "--output", required=True, help="Path to output PSD")
    p_split.set_defaults(func=cmd_split)

    # Repair Mouth
    p_mouth = subparsers.add_parser("repair-mouth", help="Inject procedural dual-layer mouth")
    p_mouth.add_argument("input", help="Source PSD")
    p_mouth.add_argument("-o", "--output", required=True, help="Output PSD")
    p_mouth.add_argument("--x0", type=int, required=True, help="Patch left coordinate")
    p_mouth.add_argument("--y0", type=int, required=True, help="Patch top coordinate")
    p_mouth.add_argument("--x1", type=int, required=True, help="Patch right coordinate")
    p_mouth.add_argument("--y1", type=int, required=True, help="Patch bottom coordinate")
    p_mouth.add_argument("--rx", type=float, default=16.0, help="Mouth half-width (default: 16.0)")
    p_mouth.add_argument("--depth", type=float, default=12.0, help="Mouth open depth (default: 12.0)")
    p_mouth.add_argument("--preview", help="Optional path to output preview PNG")
    p_mouth.set_defaults(func=cmd_repair_mouth)

    # Repair Eyes
    p_eyes = subparsers.add_parser("repair-eyes", help="Add close-eye swap layers")
    p_eyes.add_argument("input", help="Source PSD")
    p_eyes.add_argument("-o", "--output", required=True, help="Output PSD")
    p_eyes.set_defaults(func=cmd_repair_eyes)

    # Sanitize Motion
    p_motion = subparsers.add_parser("sanitize-motion", help="Sanitize motion3 curves")
    p_motion.add_argument("path", help="Motion file or directory of motion files")
    p_motion.add_argument("--boost", type=float, default=1.35, help="Speech mouth opening multiplier")
    p_motion.set_defaults(func=cmd_sanitize_motion)

    # Rig
    p_rig = subparsers.add_parser("rig", help="Automated rigging via PSD2Live")
    p_rig.add_argument("psd", help="Input PSD file")
    p_rig.add_argument("-o", "--out-dir", required=True, help="Output model directory")
    p_rig.add_argument("--roles", help="JSON file with layer role specifications")
    p_rig.add_argument("--atlas", type=int, default=4096, help="Texture atlas budget (default: 4096)")
    p_rig.add_argument("--boost", type=float, default=1.35, help="Mouth open multiplier")
    p_rig.set_defaults(func=cmd_rig)

    # QA
    p_qa = subparsers.add_parser("qa", help="Check model package integrity")
    p_qa.add_argument("model_dir", help="Model directory")
    p_qa.set_defaults(func=cmd_qa)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
