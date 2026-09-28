---
name: workflow-lifecycle
description: >
  Workflow 生命周期总纲(五段模型)+ 步骤表 SSOT 管理。任何新 workflow 立项、老 workflow
  迭代/翻车/加步骤时先读本 skill:确定当前在 S1探索/S2沉淀/S3固化/S4可靠/S5交付 哪一段、
  过关门槛是什么、Commander 该以救火还是审计身份在场。步骤表本地 JSON 为唯一真相源,
  改完跑 scripts/sync-to-notion.mjs 推送 Notion 仪表盘。
  触发:「workflow 到哪一段了」「更新步骤表」「这步该固化还是留AI」「新 workflow 立项」。
---

# workflow-lifecycle — 五段生命周期总纲

## 五段模型(出生一次性)

| 段 | 目标 | 过关门槛 | 谁干活 |
|---|---|---|---|
| S1 探索 | 端到端通1次 | 完整通1次(慢丑都行) | 纯AI |
| S2 沉淀 | 出步骤表 | 连续2-3遍序列一致+每步有验证信号 | AI跑+记录 |
| S3 固化 | 稳→写死,漂→留AI | 每步有标签+证据,整轮稳M次 | 代码+AI混合 |
| S4 可靠 | 加审计(证据/哈希) | 带审计仍整轮稳 | +Commander审计 |
| S5 交付 | Kotlin+skill | 有交付需求+表齐全 | Kotlin机械+AI判断 |

## Commander 两身份
- **救火(辅助)**:S2 起在场——卡一步能重做/换法子,不查证据。
- **审计**:S4 才上岗——救火形态整轮稳定后,一格一格加。
- 病征:审计压在救火没稳的链上 = 整轮跑不完(0912 获客线实证)。

## 迭代环(运营期,步骤级)
- 翻车步骤:自动降级留AI兜底(不停服)→重沉淀→重固化→版本+0.1
- 新增步骤:局部走 探索→沉淀→固化 →嫁接进步骤表
- 固化的每一步永远保留 AI 兜底路径。

## 步骤表 SSOT
- 本地真相源:`steps/<workflow>.json`(order/stage/name/impl_now/target/deterministic/signal/status/history[]/evidence)
- 颗粒度标准:每步可独立验证成败(能说清"成了没"就是一步)
- 沉淀触发:AI连对N次→固化候选;反复漂→标留AI;翻车修好→history 加一条
- 改本地 → `node scripts/sync-to-notion.mjs steps/<workflow>.json` 推 Notion
- Notion 仪表盘:总图页 3d9c40c2ba638171933af1746e19b60c / 步骤库 3d9c40c2ba638195a41bf529056a4aa8 / Workflows库 3d9c40c2-ba63-8145-bfa8-f4c0c006e0af

## 配套 skill 网
已有:rpa-audit(S3守门)/systematic-debugging/设备台账+TTL锁/memory
缺:步骤记录skill(S2)/标签判定skill(S3)/Commander减负/固化步AI兜底机制
