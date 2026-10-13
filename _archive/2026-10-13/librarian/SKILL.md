---
name: librarian
version: 2.1.0
created: 2026-03-15
updated: 2026-03-15
description: |
  Cecelia 系统图书管理员。
  读取 BACKLOG.yaml，为每个知识单元生成一个
  可交互的深度 HTML 知识页（风格同 cecelia-dev-deep.html）。
  每次运行处理 3-5 个条目。多个 Codex 账号可并行运行互不干扰。

  触发词：librarian、/librarian、生成知识页、补充说明书
---

# librarian — 图书管理员

> 你是 Cecelia 系统的图书管理员。
> 你的工作是把源代码转化成人人都能读懂的深度交互式知识页。
> 每个知识页都是一个独立的 HTML 文件，风格和 cecelia-dev-deep.html 完全一致。
> **每个页面不少于 40KB**，内容深度必须达到 cecelia-dev-deep.html 的水准。

---

## 第一步：领取任务

```bash
cat /Users/administrator/perfect21/cecelia/docs/knowledge/BACKLOG.yaml
```

找出 `status: todo` 的条目，**立刻把它改成 `status: in_progress`**（防止其他 Codex 重复领取）。

优先级：P0 → P1 → P2，本次选 **3-5 个**。

---

## 第二步：深度读源代码

对每个条目，读取 `source_files` 里的所有文件：

```bash
cat /Users/administrator/perfect21/cecelia/{source_file}
```

读完后，必须提取以下信息（不提取不能写页面）：
- 所有关键常量和阈值（具体数值）
- 所有错误处理逻辑（错误类型、触发条件、处理方式）
- TODO、FIXME、⚠️ 注释
- 依赖关系（require/import 了什么）
- 对外暴露的 API 端点或函数

---

## 第三步：生成深度 HTML 知识页

### 视觉风格（必须严格遵守）

参考文件：`/Users/administrator/claude-output/cecelia-dev-deep.html`

```
背景色：#07070f
卡片背景：#0d0d1c，边框 #1a1a2e
标题渐变：linear-gradient(135deg,#fff,#a78bfa)
字体：-apple-system,'SF Pro Display',sans-serif
强调色：紫 #a78bfa，绿 #34d399，橙 #f59e0b，红 #ef4444
```

三栏布局：左侧导航(240px) + 中央内容(弹性) + 右侧信息栏(300px)

### 各章节内容要求（最低标准）

**做什么（最少 200 字）**
- 2-3 个日常类比（"它像值班保安"这样的比喻）
- 3-5 个具体场景举例
- 对用户的实际影响

**为什么需要它（最少 150 字）**
- 如果没有它，系统会出什么具体故障（真实场景）
- 解决了什么历史痛点

**怎么工作（最少 300 字）**
- 编号步骤，最少 4 步
- 每步用 step-block 格式
- 关键阈值必须用白话（"每5秒检查一次"，不是 TICK_INTERVAL=5000）
- 子机制分别说明

**正常状态（最少 100 字）**
- 3-5 个可观察现象（日志、API 返回、Dashboard 显示）

**常见失败和解决（表格，最少 3 行）**
- 从源代码错误处理逻辑中提取真实案例

**和其他模块的关系**
- CSS 绘制关系图（不用外部库）

**技术细节（默认折叠）**
- 真实常量值（从代码读取）
- 函数签名
- TODO/FIXME 列表

**右侧信息栏关键数字**：最少 5 个数字，从代码读取真实值

### 写作铁律

- ❌ `TICK_LOOP_INTERVAL_MS = 5000` → ✅ `每5秒检查一次`
- ❌ `ACTION_WHITELIST` → ✅ `允许执行的操作白名单`
- ❌ 粘贴代码块 → ✅ 解释代码在做什么
- ❌ "详见源码" → ✅ 直接说清楚
- ❌ 每章节2-3句话 → ✅ 每章节最少 150-300 字

---

## 第四步：保存文件

```
Brain 模块：  /Users/administrator/claude-output/knowledge/brain/{unit-id}.html
Engine 模块： /Users/administrator/claude-output/knowledge/engine/{unit-id}.html
Workflows：   /Users/administrator/claude-output/knowledge/workflows/{unit-id}.html
系统概念：    /Users/administrator/claude-output/knowledge/system/{unit-id}.html
```

---

## 第五步：更新 BACKLOG.yaml

每完成一个条目：
```yaml
status: done
output_url: knowledge/{module}/{unit-id}.html
completed: 2026-03-15
```

更新 `meta.done` 计数和 `meta.last_updated`。

---

## 第六步：更新总目录（index.html）

更新 `/Users/administrator/claude-output/knowledge/index.html`：
- 所有已完成页面的卡片网格（按模块分组）
- 进度条：X/86 已完成
- 未完成显示灰色占位卡片

---

## 第七步：输出本次进度

```
✅ 本次完成 N 个知识页（共 X/86）

  brain/xxx.html     — 说明
  engine/xxx.html    — 说明

访问：http://38.23.47.81:9998/knowledge/index.html
```

---

## 多账号并行规则

- 领任务时立刻改 `status: in_progress`
- 都往同一个 `claude-output/knowledge/` 目录写文件
- 都更新同一个 BACKLOG.yaml
