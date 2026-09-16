# 候选情报契约

返回 JSON 数组，每项使用以下字段：

```json
{
  "title": "中文标题",
  "original_title": "原文标题",
  "region": "国内",
  "type": "技术",
  "summary_zh": "两到三句中文事实摘要",
  "source_name": "来源名称",
  "source_url": "https://example.com/original",
  "published_at": "2026-09-03",
  "captured_at": "2026-09-03T08:00:00+08:00",
  "relevance_score": 86,
  "heat_score": 72,
  "confidence": "高",
  "direction": "产品与服务",
  "applicable_product": "企业FDE部署与落地",
  "action": "由FDE评估是否加入客户诊断清单",
  "receiver_agent": "fde",
  "login_requirement": "免登录",
  "status": "候选"
}
```

约束：

- `region` 只能为 `国内`、`国际`。
- `type` 只能为 `新闻热点`、`政策`、`技术`、`竞品`、`关键词`、`客户需求`、`战略机会`。
- `confidence` 只能为 `高`、`中`、`低`。
- `direction` 只能为 `企业与商业模式`、`产品与服务`、`目标客户与成交逻辑`、`创始人IP与内容定位`、`市场竞品与关键词`、`阶段目标与行动计划`。
- `receiver_agent` 只能为 `zenithjoy-router`、`social-media-manager`、`fde`、`dev`。
- `login_requirement` 固定为 `免登录`；遇到登录墙的来源不进入数组。
- 分数必须是 0–100 的整数。
- `source_url` 必须为已打开核验的原文链接。
