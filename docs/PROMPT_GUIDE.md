# 2D Character Generation & Prompt Engineering Guide for Live2D

> **Core Rule**: The objective is to produce an illustration that can be cleanly decomposed into Live2D layers, rather than a generic illustration.
> The single golden rule: **Arms, hair, and legs must be cleanly separable without occlusion gluing.**

---

## 1. Hard Constraints Checklist

Before passing any AI illustration into the layer decomposition pipeline, verify every single item below:

| # | Requirement | Reason |
|---|---|---|
| 1 | **Full body, top of head to boot soles fully in frame** with generous margins | Half-body crops cannot perform walk cycles or leg physics. |
| 2 | **A-Pose: Arms angled 30–40° away from torso** with visible background daylight | Arms touching the torso will blend into the clothes and cause tearing during decomposition. |
| 3 | **Hair positioned behind shoulders/back** | Hair overlapping the shoulder or arms is fatal for layer separation. |
| 4 | **Legs slightly parted with visible gap** | Parallel touching legs make clean left/right leg boundaries impossible. |
| 5 | **Skirt/hem does not cover knees** | Knees and thighs must be visible to allow inpainting underneath. |
| 6 | **Pure white or transparent background**, no props, no floor shadow | Shadows and background elements will bleed into layer textures. |
| 7 | **Height ≥ 2048px** | High resolution is essential for clear facial feature meshes. |
| 8 | **Crisp cel-shading + distinct lineart** | Heavy gradients and painterly blending turn into noisy artifacts when decomposed. |

---

## 2. Recommended Prompt Template (Chinese)

```text
二次元虚拟主播角色全身立绘，正面朝向观众，面部完全对称，全身完整入画，从头顶到靴底都要在画面内，四周留白。
姿势：A字站姿，双臂自然下垂同时向身体两侧张开约30度，手臂与躯干之间留出明显的透光空隙，双手自然张开，掌心朝前；双腿微微分开约15度，两腿之间留出缝隙，膝盖朝正前方。
角色：[发色发型描述，例如：银蓝色蓬松双马尾，所有长发一律披在身体后方两侧，绝对不遮挡肩膀、手臂和腰部]；整齐的齐刘海；大而圆的眼睛带星芒高光，温柔微笑。
服装：[服装描述，例如：白色露肩泡泡袖上衣，百褶短裙，大腿到膝盖完全露出，短靴]。
画风：干净清晰的粗线稿，平涂赛璐璐上色，柔和色调，纯白色背景，背景无任何元素无投影，柔和均匀光照，角色居中构图，高分辨率，虚拟主播皮套设计稿质量。
```

## 3. Recommended Prompt Template (English)

```text
full body anime VTuber character sheet, front view, perfectly symmetrical face, entire body from head to boots inside the frame with margin.
POSE: A-pose, arms hanging naturally but spread 30 degrees away from the torso, clear gap of empty space between each arm and the body, palms open facing forward; legs slightly apart with a visible gap between them, knees facing front.
CHARACTER: [hair style/color, e.g. silver-blue voluminous twin tails, ALL long locks draped behind the body, NEVER covering shoulders, arms or waist]; straight bangs; large round eyes with star highlights, gentle smile.
OUTFIT: [clothing details, e.g. off-shoulder top, pleated mini skirt, bare legs, ankle boots].
STYLE: clean bold lineart, flat cel shading, soft palette, minimal cel shadows, pure white background, no props, no floor, no cast shadow, even soft lighting, centered composition, high resolution, VTuber model sheet quality.
```

## 4. Negative Prompts

```text
手持道具, 翅膀, 披风, 复杂背景, 地板, 投影, 强烈渐变, 厚涂, 写实, 侧身, 背面, 手臂贴着身体, 头发遮住手臂, 长发盖住肩膀, 双腿并拢, 长裙, 过膝袜, 多人, 文字, 水印, props, wings, cape, complex background, floor, cast shadow, heavy gradient, painterly, photorealistic, side view, back view, arms glued to body, hair covering arms, hair over shoulders, legs together, long skirt, multiple characters, text, watermark
```
