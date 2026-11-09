#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Headless Client for PSD2Live automation service via MCP/REST JSON-RPC."""

from typing import Any, Dict, List, Optional
import json
import os
import plistlib
import re
import sys
import time
import urllib.error
import urllib.request

DEFAULT_URL = "http://127.0.0.1:23871/mcp"
DEFAULT_PLIST = os.path.expanduser("~/Library/Preferences/io.github.psd2live.plist")
ALT_PLIST = os.path.expanduser("~/Library/Preferences/com.apple.java.util.prefs.plist")


def find_token() -> Optional[str]:
    """Retrieves the bearer token from environment or macOS preferences."""
    env_token = os.environ.get("PSD2LIVE_TOKEN")
    if env_token:
        return env_token

    for p in [DEFAULT_PLIST, ALT_PLIST]:
        if not os.path.exists(p):
            continue
        try:
            with open(p, "rb") as f:
                prefs = plistlib.load(f)

            def _search(node: Any) -> Optional[str]:
                if isinstance(node, dict):
                    for k, v in node.items():
                        if k.strip("/").endswith("agent_mcp_bearer_token") and isinstance(v, str):
                            return v
                        hit = _search(v)
                        if hit:
                            return hit
                return None

            raw = _search(prefs)
            if raw:
                # Java Preferences encodes uppercase as '/x'
                return re.sub(r"/(.)", lambda m: "/" if m.group(1) == "/" else m.group(1).upper(), raw)
        except Exception:
            pass
    return None


class P2LClient:
    """Automated client for PSD2Live MCP endpoints."""

    def __init__(self, url: str = DEFAULT_URL, token: Optional[str] = None):
        self.url = url
        self.token = token or find_token()
        self.headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

        self._seq = 1
        self._connected = False

    def connect(self) -> bool:
        """Initializes handshake with the PSD2Live MCP server."""
        try:
            res = self._post({
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "live2d-avatar-pipeline", "version": "1.0.0"},
                },
            }, raw=True)
            sid = res.headers.get("Mcp-Session-Id")
            if sid:
                self.headers["Mcp-Session-Id"] = sid
            self.headers["MCP-Protocol-Version"] = "2024-11-05"
            self._post({"jsonrpc": "2.0", "method": "notifications/initialized"}, raw=True)
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            return False

    def is_available(self) -> bool:
        """Checks if PSD2Live server is reachable."""
        try:
            req = urllib.request.Request(self.url, headers=self.headers, method="GET")
            with urllib.request.urlopen(req, timeout=3) as r:
                return r.status in (200, 401, 405)
        except urllib.error.HTTPError as e:
            return e.code in (401, 405)
        except Exception:
            return False

    def _post(self, body: Dict[str, Any], raw: bool = False, timeout: int = 300) -> Any:
        req = urllib.request.Request(
            self.url,
            json.dumps(body).encode("utf-8"),
            self.headers,
            method="POST",
        )
        r = urllib.request.urlopen(req, timeout=timeout)
        if raw:
            r.read()
            return r
        txt = r.read().decode("utf-8")
        if txt.startswith("event:") or txt.startswith("data:"):
            txt = "\n".join(l[5:].strip() for l in txt.splitlines() if l.startswith("data:"))
        return json.loads(txt)

    def rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._seq += 1
        payload = {"jsonrpc": "2.0", "id": self._seq, "method": method}
        if params is not None:
            payload["params"] = params
        return self._post(payload)

    def call(self, tool: str, args: Dict[str, Any], wait: bool = True, timeout: int = 240) -> Dict[str, Any]:
        """Calls a tool and waits for completion if an async job is returned."""
        res = self.rpc("tools/call", {"name": tool, "arguments": args})
        sc = res.get("result", {}).get("structuredContent", res)
        d = sc.get("data") if isinstance(sc, dict) else None
        t0 = time.time()
        while wait and isinstance(d, dict) and str(d.get("id", "")).startswith("job-") and not d.get("terminal"):
            if time.time() - t0 > timeout:
                break
            time.sleep(1)
            w = self.rpc("tools/call", {
                "name": "job",
                "arguments": {"op": "wait", "request": {"id": d["id"], "timeout_ms": 20000}},
            })
            sc = w.get("result", {}).get("structuredContent", w)
            d = sc.get("data") if isinstance(sc, dict) else None
        return sc

    def inspect_workspace(self, scope: str = "project") -> Optional[Dict[str, Any]]:
        """Inspects current project or layers."""
        r = self.call("workspace_inspect", {"request": {"scope": scope}})
        if isinstance(r, dict) and r.get("ok"):
            return r.get("data")
        return None

    def import_psd(self, psd_path: str, state: str) -> Optional[Dict[str, Any]]:
        """Imports PSD file into the workspace."""
        r = self.call("project", {
            "op": "import_psd",
            "request": {
                "path": os.path.abspath(psd_path),
                "discard_unsaved": True,
                "state": state,
                "request_id": f"imp-{int(time.time())}",
            },
        })
        if isinstance(r, dict) and r.get("ok"):
            return r.get("data")
        return None

    def update_rig(self, project_id: str, state: str) -> Optional[Dict[str, Any]]:
        """Rebuilds the rig generation."""
        r = self.call("workspace_call", {
            "operation": "rig_update_generation",
            "request": {
                "state": state,
                "project_id": project_id,
                "request_id": f"rig-{int(time.time())}",
            },
        })
        if isinstance(r, dict) and r.get("ok"):
            return r.get("data")
        return None

    def export_vtube_studio(self, output_dir: str, state: str) -> Optional[Dict[str, Any]]:
        """Exports the model to VTube Studio format."""
        os.makedirs(output_dir, exist_ok=True)
        r = self.call("project", {
            "op": "export_target",
            "request": {
                "target": "vtube-studio",
                "output_directory": os.path.abspath(output_dir),
                "state": state,
                "request_id": f"exp-{int(time.time())}",
            },
        })
        if isinstance(r, dict) and r.get("ok"):
            return r.get("data")
        return None
