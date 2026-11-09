#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Live2D model integrity checker and QA validator."""

from typing import Any, Dict, List, Tuple
import os
import glob
import json


class ModelChecker:
    """Validates structure, file references, and parameters of an exported Live2D model."""

    @staticmethod
    def inspect_model_directory(model_dir: str) -> Dict[str, Any]:
        """Comprehensive verification of an exported model folder."""
        issues: List[str] = []
        warnings: List[str] = []

        # 1. Check model3.json
        model3_files = glob.glob(os.path.join(model_dir, "*.model3.json"))
        if not model3_files:
            return {"valid": False, "errors": ["No .model3.json file found."]}

        model3_path = model3_files[0]
        try:
            with open(model3_path, "r", encoding="utf-8") as f:
                model3_data = json.load(f)
        except Exception as e:
            return {"valid": False, "errors": [f"Failed to parse {model3_path}: {e}"]}

        file_refs = model3_data.get("FileReferences", {})

        # Check Moc
        moc_rel = file_refs.get("Moc", "")
        moc_path = os.path.join(model_dir, moc_rel)
        if not moc_rel or not os.path.exists(moc_path):
            issues.append(f"Moc file missing: {moc_rel}")
        elif os.path.getsize(moc_path) < 100:
            issues.append(f"Moc file appears empty or corrupt: {moc_rel}")

        # Check Textures
        textures = file_refs.get("Textures", [])
        if not textures:
            issues.append("No textures defined in model3.json")
        for tex in textures:
            tex_p = os.path.join(model_dir, tex)
            if not os.path.exists(tex_p):
                issues.append(f"Texture missing: {tex}")
            elif os.path.getsize(tex_p) == 0:
                issues.append(f"Texture file empty: {tex}")

        # Check Motions
        motions = file_refs.get("Motions", {})
        motion_count = 0
        for group, items in motions.items():
            for it in items:
                m_file = it.get("File", "")
                m_path = os.path.join(model_dir, m_file)
                if not os.path.exists(m_path):
                    issues.append(f"Motion file referenced in '{group}' missing: {m_file}")
                else:
                    motion_count += 1
                    # Inspect curves for invalid target
                    try:
                        with open(m_path, "r", encoding="utf-8") as mf:
                            m_data = json.load(mf)
                        for c in m_data.get("Curves", []):
                            if c.get("Target") == "Model":
                                issues.append(f"{m_file}: Curve '{c.get('Id')}' has invalid Target='Model'")
                    except Exception as e:
                        issues.append(f"Error parsing motion file {m_file}: {e}")

        # Check VTube profile
        vtube_files = glob.glob(os.path.join(model_dir, "*.vtube.json"))
        if not vtube_files:
            warnings.append("No .vtube.json profile found (recommended for VTube Studio).")

        return {
            "valid": len(issues) == 0,
            "errors": issues,
            "warnings": warnings,
            "model_file": os.path.basename(model3_path),
            "textures_count": len(textures),
            "motions_count": motion_count,
        }
