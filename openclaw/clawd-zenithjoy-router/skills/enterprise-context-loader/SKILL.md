---
name: enterprise-context-loader
description: "在热点、关键词、内容、获客、FDE方案或经营分析前，按 tenant_id 读取同一份企业、产品和目标客户主数据，并返回带版本和完整度的最小业务上下文。"
---

# 企业上下文加载器

从 `/Users/administrator/openclaw-root/workspaces-root/clawd/company-data/<tenant_id>/current/` 读取企业运行副本。`enterprise-master.md` 是企业叙事主文档，YAML 是结构化索引。这个 Skill 只读；飞书同步、修改企业资料和外部动作不属于本 Skill。

读取前先核对 `/Users/administrator/openclaw-root/workspaces-root/clawd/config/enterprise-context/tenant-registry.json`。租户必须存在，且注册表必须明确设置 `cross_tenant_fallback=false`；不得因为多个企业处于同一飞书组织就借用其他企业的 App、Agent、文档或 Base。

## 输入

- `tenant_id`：必填。不得根据群名以外的模糊线索跨企业猜测。
- `task_type`：`hot_news`、`keyword_radar`、`content`、`leadgen`、`fde` 或 `general`。
- 可选 `query`：本次任务主题。

## 执行

1. 运行：

   ```bash
   node /Users/administrator/openclaw-root/workspaces-root/clawd/skills/enterprise-context-loader/scripts/load-context.mjs \
     --tenant <tenant_id> --task <task_type>
   ```

2. 检查输出中的 `status`、`version`、`completeness`、`master_document` 和 `missing_required`。
3. `status=ready` 时，只使用返回的数据作为企业事实；外部检索结果必须另外标注来源。
4. `status=incomplete` 时仍可完成公开信息采集，但企业相关性评级不得高于 A，并明确列出缺失项。
5. `status=invalid` 或目录不存在时停止企业定制分析，报告缺口；不得借用其他 tenant 的资料。

## 任务裁剪

- `hot_news`：企业、产品、客户画像、战略重点、关注词和排除词。
- `keyword_radar`：产品、客户痛点、购买触发、品牌词、产品词、需求词、竞品词和排除词。
- `content`：企业定位、产品价值、客户画像、品牌语气和禁用表述。
- `leadgen`：客户画像、地域、决策角色、痛点、购买触发和线索判定规则。
- `fde`：企业能力、产品、客户画像、已验证案例和交付边界。
- `general`：返回完整的精简上下文。

## 边界

- 不读取或输出应用密钥、个人登录态、Cookie 和无关客户隐私。
- 输出中的 `tenant_route` 是当前租户唯一允许的 App/Agent 路由；后续动作必须沿用，不得自动回退。
- 线索不是客户；`lead`、`prospect`、`customer` 必须分开。
- 不把飞书同步失败解释成资料被删除；继续使用最后一个校验通过的运行副本。
- 主文档与结构化表冲突时停止自动升级事实，并输出冲突项；不自动修改企业主数据。

## 验收

运行以下命令，必须退出码为 0，且输出 `tenant_id`、`version`、`task_type`、`completeness`：

```bash
node /Users/administrator/openclaw-root/workspaces-root/clawd/skills/enterprise-context-loader/scripts/load-context.mjs \
  --root /Users/administrator/openclaw-root/workspaces-root/clawd/company-data \
  --registry /Users/administrator/openclaw-root/workspaces-root/clawd/config/enterprise-context/tenant-registry.json \
  --tenant yueshengyun --task hot_news
```
