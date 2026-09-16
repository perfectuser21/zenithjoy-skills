# 多租户设备恢复

恢复时始终使用任务上下文和租户配置中的 `tenant_id、profile、node、phone_serial、phone_model、adb_controller、screen_size`。任何一项缺失都不进入采集。

## 新租户登记

1. 为公司分配唯一 `tenant_id`，为每台手机分配唯一 profile；不要只写“工作机”。
2. 在目标 Node 实际连接手机，核对 serial、model、USB transport 和屏幕尺寸。
3. 把 profile 写入 Node 控制器的 allowlist/registry，并把控制器路径、Node、serial、model 和尺寸写入租户配置。
4. 在同一 Node 执行 `status、diagnose、screencap、pull`，确认不会命中其他租户设备。
5. 绑定该租户自己的飞书账号、关键词表、线索表、账号矩阵和业务 Agent；配置未完成前保持 disabled。

## 恢复顺序

每条命令都在当前租户 Node 上通过 `<adb_controller> --profile <profile> <command>` 执行。不要从 Gateway、其他服务器或 Agent 本机直接调用 adb。

1. 运行 `status`。成功输出中的 serial 和 model 必须与租户登记值完全一致。
2. 状态 offline 时运行 `diagnose`，只核对登记 serial。USB 可见但 ADB 为空时只执行一次 `refresh`，再重试 `status`。
3. 若出现额外 serial，只报告现场存在额外设备，不操作、不接管、不切换 profile。
4. 状态正常后运行 `telecom` 并截图；有通话或来电就停止。
5. 黑屏时运行 `wake`；只有系统确认无安全凭证时才运行 `unlock`。不输入密码、不绕过图案或指纹。
6. 再次截图确认页面，随后才允许 `open-search`。每次点击或滑动后重新截图。

## 退出条件

- 出现密码、图案、指纹或“允许 USB 调试”弹窗：停止并交给手机使用者。
- `status` 与 `diagnose` 连续两次失败：报告精确租户、profile、Node、serial 和状态。
- 任何时候只允许操作当前 profile；其他租户、旧手机或在线设备不得作为故障兜底。
