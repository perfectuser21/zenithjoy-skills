---
name: android-bilibili-verify-existing
description: 通过轻盈底座只读核验小白上已存在的一条 B 站私密视频，读回本人 UID、BVID、可见范围和播放完成证据。
metadata:
  version: "1.0.0"
---

# 核验小白上的既有 B 站私密作品

使用已登记的 `android_bilibili_verify_existing` 工作流。唯一 Activity 是 `verify_existing`，宿主只接受空参数 `{}`。执行前由工作流核对固定版本、当前安装观测和任务；中央租约与本机锁都由宿主管理。

本版只核验 `xian-m4` 的小白（`yueshengyun-work`，序列号 `e6c7ef34`），账号 UID `3546824935738234`，既有视频 `BV1cLpG6cEHH`，片长 10 秒。设备、本人、作者、视频或可见范围有一项不符即结束，记录缺失的原证。只能查看稿件、可见设置及播放器。禁止输入文案，禁止发稿、分享、改保存设置或切换账号。

验收需同一次运行的账户、作者、作品详情、编辑器、可见设置与播放器原件，确认本人 UID 与作者 UID 一致、该 BVID 仅自己可见且播放到 `00:10`。Brain 读回对应的证据摘要，宿主回到默认桌面并确认双锁释放后，才能记为完成。若原件或宿主收尾状态未知，保留 `needs_review`，不得重开或改用其他稿件。
