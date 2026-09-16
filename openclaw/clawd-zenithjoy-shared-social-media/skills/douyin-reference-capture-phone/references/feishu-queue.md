# 飞书队列约定

优先使用专用多维表格“抖音对标研究队列”。若尚不存在，创建一个 Base，并使用首张数据表。

字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| 标题 | 文本（主字段） | 视频标题或可见文案 |
| job_id | 文本 | 一次用户任务的唯一编号 |
| 状态 | 单选 | opening/acquiring/captured/transcribing/delivered/blocked/failed |
| 关键词 | 文本 | 发现该视频的搜索词 |
| 作者 | 文本 | 抖音账号名 |
| 来源链接 | URL | 分享链接；没有时保存分享文本到备注 |
| 发布时间 | 文本 | 以 App 可见值为准 |
| 时长秒 | 数字 | 视频时长 |
| 可见互动 | 文本 | 点赞、评论、收藏等可见值，不推测缺失数据 |
| 设备 | 文本 | ADB 序列号 |
| 截图证据 | 文本 | 工件路径或附件链接 |
| ASR模型 | 文本 | 实际使用模型或 fallback |
| 转写费用美元 | 数字 | 按 API usage/账单可得值填写；未知留空 |
| 交付文档 | URL | 飞书文档链接 |
| 覆盖状态 | 单选 | full/partial/unknown；只有 full 可交付为全文 |
| last_error | 文本 | 最后错误，成功时留空 |
| next_action | 文本 | 自动恢复或人工动作 |
| 更新时间 | 日期时间 | 最后一次状态变化 |

创建 Base 后，把 `app_token` 和 `table_id` 写入媒体 workspace 的 `config/douyin-reference-queue.json`。这些是资源标识，不是 API 密钥。每条视频一条记录；同一 `job_id + 来源链接` 不重复创建。
