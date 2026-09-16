---
name: douyin-leadgen-phone
description: "Compatibility entry for existing Douyin phone lead-generation tasks. Route full lead-generation requests to social-leadgen-workflow and route low-level device actions to douyin-phone-runtime. Use when an older task, automation, or Agent still invokes douyin-leadgen-phone; do not implement the entire business workflow in this Skill."
---

# 抖音手机获客兼容入口

这是旧任务名称的兼容路由，不再承担搜索、判定、评论采集、线索分类和写表的全部职责。


## 交结果之前先落盘（尽力而为，绝不因它阻塞）

输出最后一行 `WORKER_RESULT {json}` 之前，先用**网关侧文件写工具**（不是 `exec`）把**完全相同**的 JSON
写到这个确定路径：

```
/root/clawd-work-commander/state/workflow-runs/<run_id>__<attempt_id>.<stage_id>.<stage_attempt>.worker-result.json
```

这条路径是可写的（0913 实证：preflight 第 3 次正是靠它写成、Commander 读到、阶段才通过）。
偶尔 `file_write` 会失败——那时记一条 warning 就好，见下。

**这份落盘是尽力而为的备份，不是验收条件。**写失败就在 `warnings` 里记一句然后照常返回你真实的
`status` 与 `recommended_next_action`。**任何情况下都不得因为"回执没写成"而把 `status` 改成 `blocked`**——
那会把一次成功的阶段变成失败。它不需要 write-guard、不计入 `business_writes` / `artifact_writes` / 外部交互计数。

## 路由

- 完整获客任务：调用 `social-leadgen-workflow`。
- 日期窗口视频发现：调用 `social-video-discovery`。
- 文案与前 15 秒二段判定：调用 `social-video-qualifier`。
- 评论证据采集：调用 `social-comment-lead-collector`。
- 线索判定、去重和交付：调用 `social-lead-delivery`。
- 抖音手机、Node、profile、截图和清理：调用 `douyin-phone-runtime`。
- 高价值视频整条转写和内容研究：调用 `douyin-reference-capture-phone`，不得作为每条获客视频的默认步骤。

## 兼容边界

旧自动化可以继续用本名称触发，但必须先读取租户注册表并构造 `tenant_context`，随后交给 Workflow。不得在本 Skill 中增加公司、账号、设备 serial、Node、飞书表或关键词默认值。

手机控制器源码暂保留在 `scripts/douyin-phone-adb.zsh` 以兼容已部署路径。控制器只负责 profile 隔离、动作与截图复合命令、设备恢复和 `close-app`；业务判断由新阶段 Skills 完成。

默认只读采集和内部写入。禁止点赞、关注、评论、私信、发布、切换未授权账号或绕过风控。任何打开抖音的任务最终都必须通过 `douyin-phone-runtime` 清理并验证回到桌面。
