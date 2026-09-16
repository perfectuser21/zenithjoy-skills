---
name: wechat-moments-publisher-android
description: Publish an approved YueShengYun WeChat Moments task through its tenant-bound OpenClaw Node and Android WeChat controller, then write verifiable results back to Feishu Base. Use only for explicit publish/preflight requests or approved queue execution; never use a Douyin controller or an unbound phone.
metadata:
  version: "0.2.0"
---

# 悦升云端安卓微信朋友圈发布器

## 当前边界

本 Skill 是受控执行合同，不自行扩大授权。部署本 Skill 不等于允许发布。只有飞书系统配置中的“微信发布器状态”为“启用”、账号与设备已现场核验、专用控制器存在，且目标发布任务已经批准时，才能操作手机。

当前任何缺少项都返回 `blocked`，不得调用抖音控制器、裸 `adb`、其他租户设备或其他微信账号求成功。

执行前读取 [悦升云端绑定与发布合同](references/yueshengyun-binding.md)。

## 输入

- 飞书发布任务ID；或明确的只读 `preflight` 请求。
- 当次运行ID与幂等键。
- 用户明确发布授权，或可信调度信封中的已批准发布权限。

不得仅凭一段文案直接操作手机。正文、附件、账号和计划时间必须来自飞书发布任务的冻结快照。

## 执行流程

1. 从 `06-发布任务` 精确读取任务，并读取关联的 `05-朋友圈内容` 与 `08-朋友圈系统配置`。
2. 核验 tenant、审核状态、发布状态、正文附件快照、计划时间和是否已有成功回执。
3. 核验 OpenClaw Node 在线、微信专用控制器存在、phone profile 与设备身份匹配。
4. 取得独占设备锁，打开微信并在个人页核验账号 marker。登录、验证码、实名、人脸、设备确认或风控立即停止。
5. 只在最终预览页再次比对正文摘要、附件数量和账号；未获得本次发布授权不得点击最终发布。
6. 成功后取得可核验证据，回写实际发布时间、证明、尝试次数和“已发布”；结果不确定时写“发布失败/结果不确定”，不得再次点击最终发布。
7. 退出敏感页面并释放设备锁。

## 输出

返回结构化结果：`task_id`、`status`、`tenant_id`、`account_verified`、`device_verified`、`published_at`、`proof`、`failure_reason`、`external_interactions` 和 `business_writes`。

没有证明证据时不得返回 `published`。一次任务最多自动重试一次，而且必须能证明第一次未完成发布。
