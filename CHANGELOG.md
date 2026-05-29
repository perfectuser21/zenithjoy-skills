## [2026-05-29] harness-generator — updated
Step 7.5：PR 创建后轮询 CI 直到合并，不再立刻退出。

## [2026-05-29] engine-pr-watchdog — updated v3.0.0
修复 WTBASE 路径错、scope 太窄、trigger 受限三个问题，改为查所有 repo 的 open PR。

## [2026-05-29] engine-pr-watchdog — updated
超时立刻重新 Bash 调用，不得输出文字或结束 turn，PR 不合并就不停。

# ZenithJoy Skills Changelog

每次通过 skill-creator 创建或更新 skill 后，在此文件顶部追加一条记录。

格式：`## [YYYY-MM-DD] <skill-name> — <created|updated>`

---

## [2026-05-29] skill-creator — updated
加入 ZenithJoy 强制规则（所有 skill 改动必须经过 skill-creator）；Post-Creation 步骤新增 zenithjoy-skills 同步 + CHANGELOG 更新；明确两个 repo 的架构和职责。
