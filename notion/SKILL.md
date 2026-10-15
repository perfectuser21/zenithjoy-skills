---
name: notion
description: "查询 Notion 页面与数据库，写入获授权的知识或内容真身；Brain 六层目录及任务、决策、Ops 等投影只读，结构和事件写回走 Brain。"
version: 2.0.0
updated: 2026-10-15
---

# Notion 读写

## 先确定真身与工作面

按用户当前六去向规则操作：知识与对外内容的真身在 Notion；任务、事件、决定、设备、Ops、
六层业务树的真身在 Brain，Notion 是投影。不能通过直写投影修正源数据或掩盖同步错误。

- 六层业务树的层级与判据只认 `../tree/SKILL.md`、`../tree/references/doctrine.md`。
- Brain 写入规范读 `../db-update/SKILL.md`，先核实目标环境、实体表与现行写入API。
- 旧 Journey / Ability / Feature / golden_path 五层模板及旧工作区ID不再作为现行结构依据。
- 人工可写列保留用户修改；设备状态、电量、心跳和机器关系等按用户列级分权规则执行。

## 凭据

按 `../credentials/SKILL.md` 从 1Password CS Vault 的 `Notion` 条目读取。
本次已核实 `credential` 字段有集成凭据；字段和值仍需按凭据技能验证，不在输出中显示。
凭据缓存只写 `~/.credentials`，权限600，不进入仓库、聊天或Notion正文。

## 当前六层目录

实际结构是 Department → Value Stream → Capability → Workflow → Activity → Step。
对应实体表及父子关系读 tree；`journeys` 是兼容视图，不代表仍使用旧表模型。

读取正式配置：`GET /api/brain/projections/notion/directory/status`（需内部API鉴权）。
以响应的 `config.dbs` 获取 areas/value_streams/capabilities/workflows/activities/steps 的库ID，
不要凭旧静态库名、同名页或历史ID猜测。先核实Brain运行环境及数据库身份。

需要同步时调用正式目录入口：`POST /api/brain/projections/notion/directory/run`，请求体为空对象。
程序负责写投影，禁止另写脚本直接改目录页的名称或关系。目录按批次与游标运行；调度唤醒不等于
全目录已同步，接口返回、`last_success_at` 也不能单独证明目标页正确。

验收目标页时核对：所属数据库、Brain ID、真实标题、直接父级关系、状态及同步收据。
不要把分页不全、同名旧页、旧工作区无权限或局部map投影误报为生产结构不存在。

## 知识与内容写入

用户指定库或页面时先读取其实际属性与父级身份，再按现有字段写入；不假设属性名称或枚举。
知识使用用户当前指定的 Reference / Operational / Insights 真库；对外内容按 Ideas → Seed →
Core → 发布编排链处理。库ID优先取本次用户提供的现行清单或正式注册表，不沿用旧AI Hub的模板ID。

普通查询只读；写入范围遵循用户授权。任务、Issue、决策、Ops和运行记录通过Brain正式入口登记，
不把AI Notes或旧Notion模板当作这些对象的新真身。

## 结果

给出实际页面链接，并区分「源数据已更新」「投影已写入」「已读回验证」三个事实。
同步失败时保留错误与目标身份，修正源或同步程序；不直改投影补一个表面成功。
