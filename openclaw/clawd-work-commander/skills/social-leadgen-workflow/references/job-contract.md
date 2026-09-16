# Workflow 任务合同

## task_request.json

Intake 在启动 Commander 前必须把用户要求归一化为以下合同。用户显式值优先；只有未填字段才从租户默认策略取值，写入 `defaults_applied`，并在 Workflow 主卡中完整显示。机器合同见 [task-request.schema.json](task-request.schema.json)。

```json
{
  "task_name": "required",
  "tenant_id": "required",
  "audience": "required",
  "keywords": ["required"],
  "search_policy": {
    "sort": "most_commented",
    "time_layers": ["one_week", "six_months"],
    "duration": "unlimited",
    "scope": "unlimited",
    "location": "unlimited",
    "exhaust_visible_results": true
  },
  "qualification_policy": {
    "transcript_coverage": "full",
    "verdict_mode": "single_full_transcript",
    "low_confidence": "review"
  },
  "comment_policy": {
    "mode": "visible_window_exhaustive",
    "window": "follow_video_layer",
    "batch_size": 30,
    "scheduler": "round_robin",
    "per_video_limit": null
  },
  "scoring_policy": {
    "deliver_categories": ["strong_intent", "weak_intent"],
    "low_confidence": "review"
  },
  "delivery_policy": {
    "destination": "tenant_final_leads",
    "dedupe": ["video", "comment", "person", "prior_runs"],
    "external_outreach": false
  },
  "card_target": {
    "audience_key": "required",
    "chat_id": "required",
    "visibility": "internal"
  },
  "defaults_applied": []
}
```

可选值来自已实机核对的抖音筛选页：

- `sort`：`comprehensive | latest | most_liked | most_commented | most_favorited`；推荐默认 `most_commented`。
- `time_layers`：`one_day | one_week | six_months`；可单选或按数组顺序多选，推荐默认 `one_week → six_months`。
- `duration`：`unlimited | under_one_minute | one_to_five_minutes | over_five_minutes`。
- `scope`：`unlimited | following | recently_viewed | not_viewed`。
- `location`：`unlimited | same_city`。
- `comment_policy.mode`：`visible_window_exhaustive | top_n`；穷尽模式中 `batch_size` 只是每轮大小，不是总上限。

Intake 必须同时生成可读描述，例如：

```text
搜索：AI怎么学、零基础学AI｜排序：最多评论｜时间：先一周后半年
时长：不限｜范围：不限｜位置：不限
视频：可见结果穷尽并去重｜判定：全文ASR后单次判定
评论：跟随视频时间层穷尽，每视频30条/轮｜配送：强+弱意向，按人去重
```

合同缺少关键词、租户、目标人群、不合法选项或卡片目标时，Intake 不得启动 Workflow。执行前必须通过 `scripts/validate-task-request.mjs`，生成 `task_request_hash` 和中文可读描述。Commander 和各阶段 Agent 不得在执行中擅自改变筛选、窗口、批次或配送范围；阶段结果必须回传相同哈希。

## 状态

`discovery → qualification → collection → scoring → delivery`

每阶段状态：`pending | running | completed | blocked | failed`。

## tenant_context.json

```json
{
  "tenant_id": "required",
  "platform": "douyin",
  "platform_adapter": "douyin-phone-runtime",
  "destination_adapter": "lark-base-cli",
  "account_role": "search-primary",
  "audience": "required",
  "keyword_source": "tenant-configured",
  "task_request": "validated task_request.json",
  "qualification_policy": {
    "transcript_coverage": "full",
    "transcript_delivery": "one_feishu_doc_per_link",
    "verdicts": ["qualified", "rejected", "review"],
    "low_confidence": "review"
  },
  "comment_policy": {
    "mode": "visible_window_exhaustive",
    "window_follows_video_layer": true,
    "batch_size": 30,
    "scheduler": "round_robin",
    "per_video_limit": null
  },
  "resources": {
    "raw_comments": "tenant-visible staging resource",
    "leads": "tenant final lead resource"
  }
}
```

Skill 不得给上述占位符填入某个公司的真实值。真实值只来自当前租户注册表。

## 阶段工件

- `discovery.json`：关键词、合同指定时间层和排序证据、视频 ID、可重开链接、标题、作者、发布时间、可见互动、截图、去重状态和 `task_request_hash`。
- `transcript-package.json`：每个链接的视频身份、完整时长、ASR 覆盖、原始/合并稿、分片 manifest、飞书文档链接和回读状态。
- `qualification.json`：视频 ID、校正全文、唯一 `qualified/rejected/review` 结论、目标人群匹配、评论获客价值、置信度、理由和转写文档链接。
- `comment-batch.json` / `comment-leads.json`：视频 ID、批次、评论原文、评论/用户稳定 ID、证据、`next_cursor`、`exhausted`、原始池记录 ID 和回读状态。
- `scored-comments.json`：每条原始评论的类型、分数、置信度、理由、配送候选标记和原始池回写证据。
- `delivery.json`：视频/评论/人员/跨运行去重键、最终目标记录 ID、原始到最终关联、写入/回读状态、游标和错误。

所有工件必须包含 `job_id`、`tenant_id`、`observed_at` 和来源阶段。阶段重跑按稳定 ID 幂等更新，不追加重复对象。
