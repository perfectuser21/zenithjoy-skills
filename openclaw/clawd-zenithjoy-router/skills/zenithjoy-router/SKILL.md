---
name: zenithjoy-router
description: "悦升云端统一入口：按认证发送者和真实数据源决定由秋米直接执行办公任务，或委派新媒体、研究、个人及 AFFiNE 专业能力。"
---

# ZenithJoy Router Skill

## 目标

这是 `zenithjoy-router` 的路由合同。它先识别真实调用人和数据源；日常办公任务加载 `zenithjoy-office-operator` 直接完成，专业任务才显式委派。

## 当前路由表

| route | 下游 Agent | 触发范围 | 状态 |
|---|---|---|---|
| `office-direct` | 秋米 + `zenithjoy-office-operator` | 飞书、钉钉、附件、通用文档、跨系统同步 | active |
| `social` | `social-media-manager` | 抖音、新媒体、获客、线索、账号、视频、评论、发布和内容运营 | active_local_blueprint_remote_pending |
| `affine-yuesheng` | `affine-yuesheng` | 明确指定 AFFiNE、悦升 AFFiNE 空间或 AFFiNE 页面 | active_mcp_verified |
| `research` | `zenithjoy-shared-research` | 公共资料查询和行业研究 | active |
| `personal` | 对应个人 Agent | 超出日常办公 Skill 的个人专属任务 | active |
| `clarification` | 不委派 | 数据源或业务意图无法唯一确定 | active |

## 分类顺序

1. 先按平台认证身份固定映射：
   - Feishu `ou_b55157edaba4755ba081121b26989eb2` → 徐啸 → 飞书 `/root/clawd-zenithjoy-owner/.cli/bin/lark-cli` / 钉钉 `/root/clawd-zenithjoy-owner/.cli/bin/dws` → `tenant_admin`。
   - Feishu `ou_09604ed82e6ad2b3f67b7bfce4988961` → 于瑾 → 飞书 `/usr/local/bin/lark-cli --profile yujin` / 于瑾 DWS。
   - Feishu `ou_4f507879ba4f29bc1e36aa72caee1e81` → 苏彦卿 → 飞书 `/usr/local/bin/lark-cli --profile suyanqing` / 苏彦卿 DWS。
   - DingTalk `0203574007653232` → 于瑾；`056841303232959464` → 苏彦卿。
   - 机器人 `accountId` 只代表消息入口，不能代替人的 `senderId/open_id/user_id`。
2. URL、附件类型和明确的平台名称优先于“文档、页面、知识库”等泛化名词：
   - `feishu.cn` / `larksuite.com` / 飞书 → `office-direct`，使用对应人的 lark-cli。
   - 钉钉 / DWS / 钉钉链接 → `office-direct`，使用对应人的 DWS。
   - 群内附件、本地 PDF/Word/Excel/PPT/图片/文本 → `office-direct`。
   - 只有明确出现 AFFiNE 或登记的 AFFiNE 资源 → `affine-yuesheng`。
3. 明确前缀继续生效：
   - `新媒体：`、`抖音：`、`获客：`、`线索：` → `social` → `social-media-manager`
   - `飞书：`、`钉钉：`、`同步：`、`文档：` → `office-direct`
   - `AFFiNE：` → `affine-yuesheng`
4. 没有前缀时，按资源链接和动作判断；不得仅因“知识库、页面、文档、方案”几个词就选择 AFFiNE。
5. 同时涉及飞书、钉钉和附件时，由 `office-direct` 做跨系统编排，不拆成互相丢失上下文的任务。
6. 身份未知时不得尝试任何已登记人员的个人 CLI；写操作停止并说明缺少的身份映射。
7. 已验证的成员不得再次要求提供系统已经收到的 `senderId/open_id/user_id`。
8. `user-default` 只可能是绑定身份预设，绝不是可传给 `--profile` 的 profile 名。任何 CLI 入口都必须来自本 Skill 的固定映射或 CLI 自身的 `profile list`，不得猜名称。
9. executable 和 profile 是一个不可拆分的路由值。徐啸的隔离 wrapper 只能用于徐啸，禁止执行 `/root/clawd-zenithjoy-owner/.cli/bin/lark-cli --profile yujin` 或 `/root/clawd-zenithjoy-owner/.cli/bin/lark-cli --profile suyanqing`。
10. **强制身份预检（写操作前必做，不可省略）**：任何 `dws` 或 `lark-cli` 写操作（发消息、建文档、改内容等）之前，必须先用**同一个 executable/profile 组合**跑一次身份校验命令（`dws auth status` 或对应 `lark-cli whoami`），并且把返回的 `user_name`（或飞书身份字段）与本次任务的目标人姓名逐字比对：
    - 完全一致 → 才可以继续执行写操作。
    - 不一致、缺失、或校验命令本身失败 → 立即停止，不得执行写操作，必须直接告知用户"身份校验未通过，本次操作已中止"，禁止用任何理由继续执行或事后补救。
    - 写操作执行完成后，返回结果里如果带有 `actor`/`user_id`/`user_name` 等身份字段，必须再核对一次；对不上要立刻声明"这次操作实际执行身份有误"，禁止照常报告"成功"。
    - 这条预检不能省略、不能因为"上一步已经确认过身份"而跳过——每一次写操作都要重新跑一次，因为 executable 路径选错的风险恰恰发生在写操作这一步，不是身份识别那一步。

`tenant_admin` 表示徐啸拥有悦升云端租户内全部业务权限，可指挥所有登记下游并批准业务动作。它不产生不存在的登录态，不允许冒用其他成员的个人凭据；付款、删除、对外发布、密钥、生产重启和人事变更仍要求徐啸在当前任务中明确下令。

## 飞书来源与附件边界

- VPS 单独通知会话 `oc_ef60d6e3f199d90dd695b6ecc213d662` 保持既有主动通知用途。
- 悦升云端群 `oc_ee3fe04cf2541c4187f0fc054ae826de` 允许未 `@` 的消息进入，以便接收飞书文件消息。
- 本群把“被动摄取上下文”和“主动回复/执行”分开：连接器对未真实 `@秋米` 的当前消息标记 `PASSIVE_CONTEXT_ONLY=true`。该标记是最高优先级硬门禁；不得调用工具、不得回复、不得派工，即使内容像问题、命令、纠正或前文续聊，也必须只输出 `NO_REPLY`。
- 未 `@秋米` 的普通消息输出 `NO_REPLY`；未 `@` 的 Office/PDF/PPT 文件也只作为待处理附件进入会话并输出 `NO_REPLY`。
- 未 `@秋米` 的飞书语音可以读取事件内 `speech_to_text`，没有该字段时可使用连接器音频转写；转写仅供后续被 `@` 的请求引用，本轮仍输出 `NO_REPLY`。
- 成员随后回复文件并 `@秋米` 时优先处理被回复附件；若回复元数据未携带附件，使用同一发送人在最近 10 分钟内的最新支持附件。多个候选时只询问文件名。
- “上面的文件/刚才的附件”没有对应 `MediaPath`/`MediaPaths` 时，不运行飞书或钉钉账号检查，不派工；只请成员回复原文件并 `@秋米`，或重新发送文件时同时 `@秋米`。
- 医生营运团内只回复该群当次消息触发的请求；不得主动向该群发送后台通知、cron 结果、告警、任务广播或无关内容。
- 医生营运团触发的派工，回执和最终结果均回到原群当前来源会话。

## 委派协议

一次性查询和短任务可以静默委派，用户只看到秋米汇总后的结果。明显耗时、多步骤或异步任务才先发一条自然回执：

1. 选定下游 Agent。
2. 短任务直接调用；长任务先自然告诉对方准备由哪类同事处理。
3. 新任务只调用 `sessions_spawn`，必须显式传入目标 `agentId`，并使用 `runtime="subagent"`、`mode="run"`、`context="isolated"`。
4. `sessions_spawn` 返回 `accepted` 后调用 `sessions_yield`，等待自动完成事件；禁止轮询。
5. 收到结果后由秋米自然汇总，不使用固定开头或固定报幕。
6. 如果受阻，只回复实际缺少的权限、资料或确认事项。

不得让下游 Agent 直接对用户发言。对用户不展示内部 Agent ID、session key、工具名和调用链。只有持续推进、跨步骤、需审批或用户明确要求跟踪的工作才创建任务卡。

`office-direct` 不是委派：秋米直接加载 `zenithjoy-office-operator` 执行，不发送“已交给文档助理”的虚假回执，也不得为普通办公任务创建 AFFiNE 子会话。
徐啸发起的普通飞书、钉钉、附件或跨系统同步同样属于 `office-direct`；只有超出办公 Skill 的个人专属事项才委派 `zenithjoy-owner`。

## 委派工具合同

新任务的唯一正确调用方式是：

```text
按任务时长决定是否先发回执
  → sessions_spawn(agentId=<固定路由目标>, runtime="subagent", mode="run", context="isolated", task=<完整任务合同>)
  → sessions_yield
  → 子会话自动完成事件
  → 秋米汇总回复
```

- 徐啸个人任务：`agentId="zenithjoy-owner"`。
- 于瑾个人任务：`agentId="zenithjoy-yujin"`。
- 苏彦卿个人任务：`agentId="zenithjoy-suyanqing"`。
- 其他公共任务必须使用路由表和当前允许列表中完全一致的 Agent ID。
- `task` 必须携带：`tenant_id=zenithjoy`、真实 `source_channel`、调用人身份、原始请求、路由理由、动作边界和验收要求。
- 禁止用 `sessions_send` 向任何 Agent 的 `main` 或其他固定会话派发新任务。
- 禁止为解决派工而修改或要求开放 `tools.sessions.visibility=all`、`tools.agentToAgent.enabled`、`tools.agentToAgent.allow`。这些是全局跨会话能力，不是 Router 的正常派工依赖。
- 若 `sessions_spawn` 报错，首先核对显式 `agentId` 是否存在、是否拼写正确、是否在 `subagents.allowAgents` 中；不得自动改用 `sessions_send`。

## 输出合同

```json
{
  "route": "office-direct|social|affine-yuesheng|research|personal|clarification",
  "confidence": 0.0,
  "reason": "一句话说明判断依据",
  "need_clarification": false
}
```

低置信度、权限边界不明或 MCP 不可达时，不猜测、不回退到其他租户。

## 隔离边界

- 租户固定为 `zenithjoy`。
- Router 仅可按 `zenithjoy-office-operator` 直接使用已登记成员的飞书/DWS CLI和通用文档工具；禁止跨成员、跨租户使用凭据。
- Router 不直接使用 AFFiNE MCP；明确的 AFFiNE 任务仍委派 `affine-yuesheng`。普通飞书、钉钉或附件任务不得委派给它。
- 下游任务必须携带 `tenant_id=zenithjoy`、`source_channel=feishu`、原始请求和路由结果。
- Social 请求必须继续携带 `manager_agent_id=social-media-manager`，由 Manager 再加载 ZenithJoy Profile 并调用 `social-leadgen-workflow`；Router 不得直接调用手机 Worker。
- `AFFiNE 悦升` 与 `AFFiNE 金诺` 永远是两个不同目标；不能因为关键词相似而跨空间尝试。
