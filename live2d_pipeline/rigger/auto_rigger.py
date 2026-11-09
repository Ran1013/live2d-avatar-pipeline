#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Automated Live2D rigger orchestrating PSD import, role classification, atlas packing, and export."""

from typing import Any, Dict, List, Optional
import os
import json
import time

from ..core.p2l_client import P2LClient
from ..repair.motion_sanitizer import MotionSanitizer
from ..repair.vts_config import VTSConfigurator


class AutoRigger:
    """Automates Live2D model generation from a layered PSD."""

    def __init__(self, client: Optional[P2LClient] = None, roles_config: Optional[Dict[str, Any]] = None):
        self.client = client or P2LClient()
        self.roles_config = roles_config or {}

    def rig_and_export(
        self,
        psd_path: str,
        output_dir: str,
        target: str = "vtube-studio",
        atlas_budget: int = 4096,
        mouth_open_boost: float = 1.35,
        sanitize_motions: bool = True,
    ) -> Dict[str, Any]:
        """Full pipeline: Imports PSD, configures rig, and exports sanitized Live2D model package."""
        if not self.client.connect():
            raise ConnectionError(
                "Unable to connect to PSD2Live service at "
                f"{self.client.url}. Ensure PSD2Live is running with MCP enabled."
            )

        psd_abs = os.path.abspath(psd_path)
        out_abs = os.path.abspath(output_dir)
        os.makedirs(out_abs, exist_ok=True)

        # 1. Inspect workspace
        st_info = self.client.inspect_workspace("project")
        if not st_info:
            raise RuntimeError("Failed to inspect PSD2Live workspace.")
        state = st_info["state"]

        # 2. Import PSD
        print(f"[AutoRigger] Importing PSD: {os.path.basename(psd_abs)}...")
        imp_res = self.client.import_psd(psd_abs, state)
        if not imp_res:
            raise RuntimeError("PSD import failed.")
        state = imp_res.get("result", {}).get("state", state)
        project_id = imp_res.get("result", {}).get("project_id", "")

        # 3. Classify layers if roles config is provided
        if self.roles_config:
            layer_info = self.client.inspect_workspace("layers")
            if layer_info and "items" in layer_info:
                print(f"[AutoRigger] Classifying {len(layer_info['items'])} layers...")
                state = layer_info.get("state", state)
                for item in layer_info["items"]:
                    name = item.get("name", "")
                    spec = self.roles_config.get(name)
                    if not spec:
                        continue
                    role, side, part = (list(spec) + ["none", "none"])[:3]
                    if (item.get("role"), item.get("side")) == (role, side):
                        continue
                    cls_res = self.client.call("workspace_call", {
                        "operation": "layer_classify",
                        "request": {
                            "state": state,
                            "layer_id": item["id"],
                            "role": role,
                            "side": side,
                            "part": part,
                            "project_id": project_id,
                            "request_id": f"cls-{int(time.time())}",
                        },
                    })
                    if cls_res and cls_res.get("ok"):
                        state = cls_res.get("data", {}).get("result", {}).get("state", state)

        # 4. Atlas budget & pack
        print(f"[AutoRigger] Setting atlas budget: {atlas_budget}x{atlas_budget}...")
        self.client.call("workspace_call", {
            "operation": "atlas_set_budget",
            "request": {
                "state": state,
                "project_id": project_id,
                "budget": atlas_budget,
                "request_id": f"atl-{int(time.time())}",
            },
        })

        # 5. Rebuild rig generation
        print("[AutoRigger] Generating rig & deformation hierarchy...")
        rig_res = self.client.update_rig(project_id, state)
        if rig_res:
            state = rig_res.get("result", {}).get("state", state)

        # 6. Export target
        print(f"[AutoRigger] Exporting to target '{target}' -> {out_abs}...")
        exp_res = self.client.export_vtube_studio(out_abs, state)
        if not exp_res:
            raise RuntimeError("Model export failed.")

        files = exp_res.get("result", {}).get("files", [])
        print(f"[AutoRigger] Exported {len(files)} files successfully.")

        # 7. Post-export sanitization (Motion curve validator + VTS profile setup)
        if sanitize_motions:
            print("[AutoRigger] Post-processing motion curves & sanitizing targets...")
            MotionSanitizer.sanitize_model_directory(out_abs)

        # Auto-configure vtube.json idle fallback
        vtube_files = [f for f in os.listdir(out_abs) if f.endswith(".vtube.json")]
        idle_files = [f for f in os.listdir(out_abs) if f.endswith(".idle.motion3.json")]
        if vtube_files and idle_files:
            VTSConfigurator.configure_vtube_profile(
                os.path.join(out_abs, vtube_files[0]),
                idle_motion_filename=idle_files[0],
            )

        return {
            "status": "success",
            "output_directory": out_abs,
            "files_count": len(files),
        }
