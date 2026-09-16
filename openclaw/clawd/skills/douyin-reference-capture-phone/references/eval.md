# 版本 Eval

Eval 是发布前或变更后的专项验收，不是生产任务阶段。日常任务不得自动调用 Eval 模型。

重新 Eval 的触发条件：新增输入模式、修改手机操作或降级路径、更换模型/API、修改长视频或转录策略、设备链路变化、连续异常。

每个入口至少保留一个端到端样本：

- 主题入口：主题 → 手机搜索 → 候选 → 共用流水线 → 飞书。
- 直链入口：真实抖音长链或短链 → 手机打开并核对 → 共用流水线 → 飞书。

先用脚本核对状态、媒体、ASR 分片和飞书回读；再启动一个独立 Luna 会话（`model: openai/gpt-5.6-luna`、`thinking: low`）只读取原始工件评分。Luna 低置信度或发现异常时才用 Terra 复核；Sol 默认禁用。Eval 结果存为 `eval-report.json`，至少包含 `skill_version`、`entry_mode`、`result`、`confidence`、`media_complete`、`transcript_complete`、`delivery_verified`、`issues`。
