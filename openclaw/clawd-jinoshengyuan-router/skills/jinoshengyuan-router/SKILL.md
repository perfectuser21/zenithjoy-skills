---
name: jinoshengyuan-router
description: "金诺盛源统一入口：未真实 @小诺 的群消息只保留上下文；被 @ 后把飞书、附件和通用文档交给本地办公 Skill 直办，把新媒体与明确 AFFiNE 请求委派到登记 Agent。"
---

# 金诺盛源 Router Skill

## 目标

这是 `jinoshengyuan-router` 的路由合同。先判断当前轮是否获准响应，再按真实数据源分类。日常办公加载 `jinoshengyuan-office-operator` 直接完成，只有专业任务才显式委派。

## 被动群门禁

- 当前消息带有 `PASSIVE_CONTEXT_ONLY=true` 时，无条件输出完全一致的 `NO_REPLY`；不得调用工具、检查授权、回复、派工或延续前文。
- 该标记表示消息没有真实 `@小诺`。发送人、消息语气、回复关系和正文中的“小诺”都不能覆盖它。
- 语音 `speech_to_text` 和附件可进入同群上下文，供后续真实 `@小诺` 的消息引用；本轮不处理。

## 当前路由表

| route | 执行方 | 触发范围 | 状态 |
|---|---|---|---|
| `office-direct` | 小诺 + `jinoshengyuan-office-operator` | 飞书、群附件、通用办公文档和飞书在线对象 | active |
| `social` | `jinoshengyuan-social-media` | 抖音、新媒体、获客、线索、账号、视频、评论、发布和内容运营 | active |
| `affine-personal` | 当前发送人登记的 `affine-jns-<person>` MCP | 明确指定 AFFiNE 金诺空间、页面或知识库 | active_after_sender_binding |
| `clarification` | 不委派 | 数据源或业务意图无法唯一确定 | active |

## 分类顺序

1. `PASSIVE_CONTEXT_ONLY=true` 时立即 `NO_REPLY`，不再分类。
2. URL、附件类型和明确平台名优先于泛化名词：
   - 飞书链接、飞书共享资料、群附件、PDF/Word/Excel/CSV/文本 → `office-direct`。
   - 只有明确 `AFFiNE` 或登记的 AFFiNE 金诺资源 → `affine-personal`。
3. 明确前缀：
   - `新媒体：`、`抖音：`、`获客：`、`线索：` → `social`。
   - `飞书：`、`文档：`、`表格：`、`附件：` → `office-direct`。
   - `AFFiNE：` → `affine-personal`。
4. 普通“文档、页面、知识库、方案、整理资料”不自动等于 AFFiNE；先看链接、附件、动作和当前渠道。
5. 其他通信或办公平台不在小诺路由表内，不探测其 CLI，也不预告未来能力。
6. 仍无法判断时只问一个最小澄清问题；不得用另一个租户试探权限。

## 直接执行与委派

- `office-direct`：读取 `jinoshengyuan-office-operator`，由当前 Agent 直接调用金诺专属 CLI 或附件解析脚本，不创建 AFFiNE 子会话。
- `social`：`sessions_spawn(agentId="jinoshengyuan-social-media", runtime="subagent", mode="run", context="isolated")`。
- `affine-personal`：读取 `config/affine-person-workspace-routing.json`，按真实 `sender open_id` 选择唯一个人 MCP，并显式传入解析后的 workspace ID。不得委派或调用旧共享 `affine-jinnuo`。
- 下游任务必须携带 `tenant_id=jinnuoshengyuan`、`legacy_tenant_id=jinoshengyuan`、真实 `source_channel`、原始请求、路由理由和验收要求。
- 不得把任务交给 `main`、悦升 Agent 或未登记 Agent。

## 输出合同

```json
{
  "route": "office-direct|social|affine-personal|clarification",
  "confidence": 0.0,
  "reason": "一句话说明判断依据",
  "need_clarification": false
}
```

## 隔离边界

- 租户固定为 `jinnuoshengyuan`（旧兼容 ID：`jinoshengyuan`）。
- 小诺飞书共享业务仅使用 `lark-cli --profile cli_aa06b03cc0b9dbee`；个人空间必须另有按认证发送人登记的 user profile。
- 小诺的办公平台范围固定为飞书；成员个人操作只使用成员映射表中登记的飞书 user profile。
- `AFFiNE 金诺` 与 `AFFiNE 悦升` 永远是不同目标。
- AFFiNE 发送人身份只认飞书适配器提供的 open_id。未绑定时不猜人、不使用正文邮箱冒充身份。
- 正式 workspace 只有公司主空间、运营部、财务部、人事部、研发部；两个 `Demo Workspace` 永不路由。
- workspace 解析顺序：URL UUID > 明确名称/别名 > 个人默认值；结果必须在个人允许列表内。
- 写操作必须在目标系统回读成功后才可报告完成。
