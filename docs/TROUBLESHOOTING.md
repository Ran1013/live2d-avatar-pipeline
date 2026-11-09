# Troubleshooting & FAQ

### 1. VTube Studio: "Animation not found" or "ThrowArgumentNullException"
- **Cause**: The `*.motion3.json` file contains curves where `"Target": "Model"` instead of `"Target": "Parameter"`. Unity's Cubism SDK cannot resolve model root curves and crashes.
- **Fix**: Run `avatar-pipeline sanitize-motion <model_dir>` to automatically rewrite all curve targets to `"Parameter"` and recalculate curve metadata.

---

### 2. Character Model Squints or Freezes When Webcam Tracking is Off
- **Cause**: `IdleAnimationWhenTrackingLost` is not configured in `*.vtube.json`, causing the model to stick to default un-animated rest poses.
- **Fix**: Run the pipeline with VTS configuration enabled, or manually set `"IdleAnimationWhenTrackingLost": "<character>.idle.motion3.json"` in the `.vtube.json` file.

---

### 3. Mouth Tilts or Sags When Speaking
- **Cause**: Single-layer mouth mesh deformation inherits non-uniform weights from the surrounding face mesh.
- **Fix**: Use `avatar-pipeline repair-mouth <input.psd> -o <repaired.psd> --x0 ... --y0 ... --x1 ... --y1 ...` to inject independent `lips` and `oral` layers with keyform opacity switching.

---

### 4. Ghost Lines or Double Mouth
- **Cause**: The original closed lip line was drawn onto the `face` layer. When the mouth opens, the static line underneath remains visible.
- **Fix**: `MouthRepairEngine` automatically performs bidirectional linear skin interpolation across the mouth bounding box on the `face` layer, erasing the static line seamlessly.

---

### 5. Jagged Eyelashes When Blinking
- **Cause**: Live2D engine squishing open eyelashes into a flat line causes polygon overlap and jagged aliasing.
- **Fix**: Inject `eye_close-l` and `eye_close-r` layers via `avatar-pipeline repair-eyes`. PSD2Live automatically detects these layers and enables `SWAP=0.06f` replacement mode.

---

### 6. Texture Atlas Appears Blurry or Pixelated
- **Cause**: Texture atlas budget defaults to 2048px or facial features receive insufficient UV space.
- **Fix**: Increase the atlas budget to 4096px (`--atlas 4096`) and ensure supersampled mouth/eye textures are generated at 8x with premultiplied alpha.
