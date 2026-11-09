#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VTube Studio configuration generator and optimizer."""

from typing import Any, Dict, List, Optional
import os
import glob
import json


class VTSConfigurator:
    """Configures VTube Studio model parameter mappings and hotkeys."""

    @staticmethod
    def configure_vtube_profile(
        vtube_json_path: str,
        idle_motion_filename: Optional[str] = None,
        mouth_open_output_max: float = 1.0,
        eye_open_output_max: float = 1.15,
        mouth_bias: Optional[float] = None,
    ) -> bool:
        """Updates and optimizes a *.vtube.json file."""
        if not os.path.exists(vtube_json_path):
            return False

        with open(vtube_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Fallback idle animation when face tracking is lost
        if idle_motion_filename:
            data["IdleAnimationWhenTrackingLost"] = idle_motion_filename

        # 2. Tune ParameterSettings
        for setting in data.get("ParameterSettings", []):
            out_param = setting.get("OutputLive2D", "")
            if out_param == "ParamMouthOpenY":
                setting["OutputRangeUpper"] = mouth_open_output_max
                if mouth_bias is not None:
                    setting["OutputRangeLower"] = mouth_bias
            elif out_param in ("ParamEyeLOpen", "ParamEyeROpen"):
                setting["OutputRangeUpper"] = eye_open_output_max

        with open(vtube_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True

    @staticmethod
    def sync_model_across_targets(
        source_model_dir: str,
        target_dirs: List[str],
        character_name: Optional[str] = None,
    ) -> List[str]:
        """Synchronizes model files to multiple destinations (e.g. VTS, showcase, archive)."""
        import shutil

        synced = []
        for t_dir in target_dirs:
            dest = os.path.join(t_dir, character_name) if character_name else t_dir
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(source_model_dir, dest)
            synced.append(dest)
        return synced
