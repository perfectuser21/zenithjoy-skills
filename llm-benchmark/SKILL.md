---
name: llm-benchmark
description: |
  AI 模型横评工具。运行标准化 LLM 横评，输出各模型在"一人公司内容运营"场景下的得分排名，基于商业洞察深度、内容创意、文案感染力等开放式质量维度。
  当用户想比较不同 AI 模型的能力、跑 benchmark、评测哪家模型最好用时触发。
  触发词：/llm-benchmark、跑一下模型测评、测评一下各家模型、跑 benchmark、对比一下各家 AI、哪个模型最好用。
---

# /llm-benchmark — AI 模型横评工具

## 触发词

用户说以下任意内容时触发本 skill：
- `/llm-benchmark`
- "跑一下模型测评"
- "测评一下各家模型"
- "跑 benchmark"
- "对比一下各家 AI"
- "哪个模型最好用"

---

## 你的职责

运行标准化 LLM 横评，输出各模型在「一人公司内容运营」场景下的得分排名。

---

## 核心方法论（v6）

### 设计哲学

**"做得有多好"而非"对不对"**

评分维度必须是开放式质量评估，不能是二元正确性检验。原因：
- 现代前沿 LLM 在结构化任务（代码实现/计算/格式校验）上几乎全部满分，无法拉开差距
- 质量型任务（商业洞察深度、内容创意、文案感染力）天然有 30~40 分差距

### 4 个测评维度（各 25 分 = 共 100 分）

| 维度 | 分数 | 评分方式 | 核心考察 |
|------|------|---------|---------|
| T1 商业诊断分析 | 25 | 全 LLM judge | 多跳推理（收藏↓评论↑ = 内容质量问题 = 品牌合作受损）|
| T2 三件套内容创作 | 25 | 全 LLM judge | 平台原生感（小红书标题能否引发点击、私信是否自然）|
| T3 数据推理+判断 | 25 | 15分自动 + 10分 judge | 发现反直觉洞察（粉丝增长≠收入增长）|
| T4 精确指令执行 | 25 | 15分自动 + 10分 judge | 约束遵守 × 文案质量 |

### LLM Judge 规则

- 使用 claude-sonnet-4-6，temperature=0.1
- 每次评分提供完整 rubric（不是"打个分"）
- 输出格式：SCORE: XX/25 + RATIONALE

---

## 模型列表（当前 12 个）

```python
MODELS = [
    {"name":"GPT-5.4",       "via":"codex",      "model":"gpt-5.4",              "codex_home":"~/.codex-team3"},
    {"name":"GPT-5.4-mini",  "via":"codex",      "model":"gpt-5.4-mini",         "codex_home":"~/.codex-team4"},
    {"name":"Sonnet 4.6",    "via":"anthropic",  "model":"claude-sonnet-4-6"},
    {"name":"Haiku 4.5",     "via":"anthropic",  "model":"claude-haiku-4-5-20251001"},
    {"name":"DeepSeek V3.2", "via":"openrouter", "model":"deepseek/deepseek-v3.2"},
    {"name":"DeepSeek R1",   "via":"openrouter", "model":"deepseek/deepseek-r1"},
    {"name":"Qwen3-235B",    "via":"openrouter", "model":"qwen/qwen3-235b-a22b"},
    {"name":"Qwen3-Coder",   "via":"openrouter", "model":"qwen/qwen3-coder"},
    {"name":"GLM-4.5",       "via":"openrouter", "model":"z-ai/glm-4.5"},
    {"name":"GLM-4.5-Air",   "via":"openrouter", "model":"z-ai/glm-4.5-air"},
    {"name":"MiniMax M2.7",  "via":"openrouter", "model":"minimax/minimax-m2.7"},
    {"name":"Kimi K2.5",     "via":"openrouter", "model":"moonshotai/kimi-k2.5"},
]
```

### API 路由方式

**codex**（GPT-5.4 系列）：
```python
result = subprocess.run(
    ["codex", "exec", prompt, "--model", model_id, "--approval-policy", "auto"],
    env={**os.environ, "CODEX_HOME": os.path.expanduser(codex_home)},
    capture_output=True, text=True, timeout=300
)
```

**anthropic**（Claude 系列）：
```python
# key from: ~/.credentials/anthropic.json → api_key 字段
client = anthropic.Anthropic(api_key=key)
msg = client.messages.create(model=model_id, max_tokens=2000, messages=[...])
```

**openrouter**（国内模型）：
```python
# key from 1Password: op item get u6odjvscjwyvhavlqaxutwaypq --vault CS --fields api_key --reveal
client = openai.OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
```

---

## 执行流程

### Step 1 — 标定（先跑 2 个模型）

目标：验证题目能拉开差距（>=30分）再跑全量，节省时间和 quota。

用最强（GPT-5.4）和最弱（MiniMax M2.7）先跑：
```bash
python3 ~/claude-output/benchmark/run_v6.py
```

判断标准：
- 差距 >= 30分 → 题目有效，进入 Step 2
- 差距 < 20分 → 题目太简单，必须重新设计

### Step 2 — 全量跑 12 模型

```bash
python3 ~/claude-output/benchmark/run_v6_full.py
```

耗时约 30~60 分钟（GPT-5.4 最慢，每题约 2min）

### Step 3 — 生成 HTML 报告

脚本内置生成逻辑，输出：
```
~/claude-output/benchmark/report_v6.html
```

公网：http://38.23.47.81:9998/benchmark/report_v6.html

报告包含：柱状图（总分排名）+ 雷达图（4维度对比）+ 详细表格

---

## 更新题目（设计规则）

### 好题 vs 坏题

| 好题（有分化） | 坏题（无分化）|
|------|------|
| 诊断一个内容账号的增长停滞原因 | 写一段 Python 代码 |
| 给一个美容服务写小红书标题 | 判断以下5条中哪条是事实 |
| 分析数据找出反直觉的商业洞察 | 计算 ROI |
| 在15个约束下写出高质量文案 | 验证以下代码是否有 bug |

好题必须满足：
1. 开放式质量：输出好坏由质量决定，不是"对不对"
2. 需要领域经验：内容运营的真实判断，不是通用推理
3. 弱模型会露出破绽：浅层分析/通用建议/缺乏平台感

### 换题步骤

1. 修改 run_v6_full.py 中的 TASKS 列表
2. 先跑标定（2模型），确认差距 >= 30 分
3. 如差距不够，加大题目难度或增加质量维度权重

---

## 参考结果（2026-03-25 v6）

| 排名 | 模型 | 总分 | T1商业 | T2内容 | T3数据 | T4执行 |
|------|------|------|--------|--------|--------|--------|
| 1 | GPT-5.4 | 78 | 22 | 21 | 20 | 15 |
| 2 | GPT-5.4-mini | 74 | 19 | 22 | 20 | 13 |
| 3 | Sonnet 4.6 | 74 | 20 | 22 | 19 | 13 |
| 4 | DeepSeek R1 | 73 | 20 | 21 | 19 | 13 |
| 5 | Qwen3-235B | 67 | 18 | 18 | 18 | 13 |
| 6 | Haiku 4.5 | 66 | 17 | 18 | 18 | 13 |
| 7 | DeepSeek V3.2 | 66 | 17 | 18 | 18 | 13 |
| 8 | Qwen3-Coder | 58 | 15 | 16 | 15 | 12 |
| 9 | GLM-4.5-Air | 54 | 13 | 15 | 15 | 11 |
| 10 | MiniMax M2.7 | 54 | 14 | 16 | 12 | 12 |
| 11 | GLM-4.5 | 53 | 13 | 14 | 15 | 11 |
| 12 | Kimi K2.5 | 42 | 11 | 12 | 13 | 6 |

最高-最低差距：36分（目标 >= 30分）

---

## 文件清单

```
~/claude-output/benchmark/
├── run_v6.py              # 标定版（2模型：GPT-5.4 vs MiniMax）
├── run_v6_full.py         # 全量版（12模型）
├── v6_calibration.json    # 标定结果
├── v6_full_results.json   # 全量结果（最近一次）
└── report_v6.html         # HTML 报告
```
