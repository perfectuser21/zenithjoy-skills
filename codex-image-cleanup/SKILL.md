---
name: codex-image-cleanup
description: 用 Codex CLI 自带 image_gen 免费去图片水印/中文字（✅ 2026-09-11 实测，走 ChatGPT 订阅额度，零额外费用）。
  含"AI 会悄悄做不干净、必须逐张视觉复核"的翻车实证。
  触发场景：去水印 / 去图上文字 / 图片处理 / 1688图能不能直接用 / 商品图清理 / image edit / 抠图去字。
---

# Codex 免费去水印

## 为什么用这个，不用别的

调研过阿里云百炼万相（¥0.14/张）、GPT-Image-2.5（$0.006~0.211/张）、FLUX Kontext（$0.04/张）、
Nano Banana（$0.039/张）。**结论：都不用买。** Codex CLI 自带 `image_gen` 工具，走已有 ChatGPT/Codex
订阅额度，零额外费用，实测效果够用。

## 正确调用方式

```bash
codex exec --skip-git-repo-check \
  -i /abs/path/input.png \
  --output-last-message /tmp/codex_msg.txt \
  "Use your built-in image_gen tool to edit the attached image: remove all Chinese text overlays,
   banners, and any watermark. Keep the product itself completely unchanged (same color, shape,
   angle, background, lighting). Output a clean product photo with zero text, suitable for a US
   e-commerce listing. Save the edited output to /abs/path/output.png"
```

### ⚠️ 两个必须知道的坑

**1. 不要直接跑那个 python 脚本。**
`~/.codex-team1/skills/.system/imagegen/scripts/image_gen.py` 是 fallback CLI，**需要单独的
`OPENAI_API_KEY`**，直接跑必报错。要用免费订阅额度，**必须走 `codex exec`** 让 agent 自己调内置工具。

**2. `--input-fidelity high` 会报错。** gpt-image-2 的图片输入天然就是 high fidelity，传这个参数直接失败。

## 🔴 铁律：每张图必须视觉复核，不能只看"没报错"

**2026-09-11 实测翻车两次，都是我自己没看图直接上传才被用户抓出来的：**

| 翻车 | 现象 | 根因 |
|---|---|---|
| 图2 | 水印没除干净，左侧留隐约重影 | 提示词只说 "remove watermark"，没说明那是**重复图案**。重跑时明确要求 `repeating semi-transparent watermark pattern, erase every instance, do not leave any faint ghost text` 才彻底干净 |
| 图5 | 成品顶部多出诡异黑块 | **裁剪边界的锅，不是 AI 的锅**——截图时把手机相册缩略图条一角带进来了，AI editor 不认识那是"不该在的东西"就原样保留 |
| 图1 | 整张漏处理 | 我肉眼判断"只有两个小标签、问题不大"就跳过了，实际那是"轻松自洁/高效省力"六个大字 |

**结论**：
- `image_gen` **会不完整执行编辑指令**，且不会告诉你它没做好
- 加工的人 ≠ 验收的人。自己做的图自己不会怀疑，必须独立过一遍
- 复核三看：①文字/水印是否真的干净 ②产品本身有没有被改形/改色 ③有没有非产品杂物（UI残留/裁切artifact）

## 输入质量前置

去水印前先确保裁剪干净。截图源的常见污染：顶部状态栏、底部缩略图条。PIL 按比例裁：

```python
from PIL import Image
img = Image.open(src); w, h = img.size
img.crop((0, int(h*0.12), w, int(h*0.335))).save(dst)   # 比例按实际机型调，裁完必须看一眼
```

裁早了会带出手机 UI，AI 不会帮你修，只会原样保留。

## 生成场景图（未实测）

`image_gen` 也支持 generate 模式（拿产品图当参照生成"宠物正在被梳毛"这类生活场景图）。
**本 skill 只覆盖 edit 模式，generate 模式尚未实测**，用前自行验证。
