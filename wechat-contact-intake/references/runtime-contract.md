# 微信联系人登记 runtime 合同

本技能的业务执行体为 `perfectuser21/zenithjoy-workspace/services/wechat-contact-inventory/cli.py`。本文件描述候选 `schema_version=1.0.0` 的接口；执行前以固定运行包的 `--help`、schema 与真实返回核对。运行包 revision 从部署绑定读取，不能用 `main`／`latest` 代替。SDK、控制器与状态目录不假设跨节点共享。

## 身份命名空间

`tenant_id + wechat_account_id` 隔离账号；渠道类型为 `person` 或 `group`。`account_key`、`record_id`、`snapshot_id` 和 revision 均从机器回执／导出文件传递，不由模型转抄、拼接或从昵称计算。`account_key` 由 runtime 对规范账号对象计算，调用方只读取回执。

已核验稳定 ID 只在相同租户、微信账号和渠道类型中归并。同一客户跨账号关联客户主档时保留原渠道，不修改渠道身份。未核验 ID 的对象是本 run 观察项；同名个人／群可以有多条，不能跨 run 自动合并，也不能启用采集。

## 盘点清单输入

- `schema_version`：`1.0.0`。
- `run_id`：本次盘点和全部采用证据共同的唯一标识。
- `observed_at`：带时区时间，不用采集时间冒充历史消息时间。
- `account`：`tenant_id`、`wechat_account_id`、`device_serial`，来自私有绑定及现场核验。
- `preflight`：`status=ready`、`login_status=verified`、`call_state=idle`。登录页、未知通话状态或账号未确认不能入账。
- `account_verified=true`、`account_evidence_ids`：证明当次账号身份，缺证不入账。
- `coverage`：`scope`、`complete`、`pages_observed`、`not_covered`；可见片段用 `scope=visible_excerpt`、`complete=false`。未知范围不得写成全量。
- `evidence`：每项含 `evidence_id`、`run_id`、`kind=screenshot|ui_tree`、本执行机可读取的私有 `path`、原始文件 `sha256`。
- `observations`：每项含 `observation_id`、`kind=person|group`、实际 `display_name`、可选 `stable_id`、`identity_verified`、`identity_evidence_ids`、`evidence_ids`。身份未证实填 false，不虚构 ID。

跨节点证据先经现有传输能力取回并核对摘要，再引用本执行机可读取的原件。原图、XML 与数据引用属于同 run；不要拿历史截图证明当前账号或身份。

## 命令

以下 `RUNTIME_ROOT` 和所有文件路径均由当次绑定提供；参数用 argv 传递，不把群名、姓名、正文拼入 shell。

```text
python3 RUNTIME_ROOT/services/wechat-contact-inventory/cli.py ingest --db PRIVATE_DB --input SCAN_JSON --out INGEST_RECEIPT_JSON
python3 RUNTIME_ROOT/services/wechat-contact-inventory/cli.py export-review --db PRIVATE_DB --account-key ACCOUNT_KEY --out REVIEW_JSON_OR_CSV
python3 RUNTIME_ROOT/services/wechat-contact-inventory/cli.py apply-review --db PRIVATE_DB --input CONFIRMED_REVIEW --actor ACTUAL_OPERATOR --out CLASSIFICATION_RECEIPT_JSON
python3 RUNTIME_ROOT/services/wechat-contact-inventory/cli.py eligible --db PRIVATE_DB --account-key ACCOUNT_KEY --out COLLECTION_PLAN_JSON
```

导出后的 JSON／CSV 是当前私有人工审阅入口；它不是已上线的 Notion 双向同步。让用户保留导出中的快照、账号、record 与 revision 标识，只修改允许的人管字段。

Review JSON 顶层为 `schema_version=1.0.0`、`kind=contact_inventory_review`、`snapshot_id`、`account_key`、`batch_run_id`、`account`、`coverage`、`records`。每条记录带 `record_id`、`revision`、`kind`、`display_name`、`stable_id`、`identity_verified`、`requires_identity_confirmation`、`classification`、`customer_refs`、`project_refs`、`collect_enabled`、`auto_reply_enabled`、`evidence_ids`。确切 CSV 列名从该固定运行包实际导出，不手工造一个相似结构绕过校验；引用数组使用 JSON 数组格式。

人管字段仅为 `classification`（`pending/customer/internal/private/excluded`）、`customer_refs`、`project_refs`、`collect_enabled`。用户确认的操作者由 `--actor` 留痕。群的客户／项目引用均可多值。分类为 `customer` 时 `customer_refs` 必须非空，即使暂不开启采集；尚无核验稳定身份可保持 `customer` 与 `collect_enabled=false`，等待身份确认。`auto_reply_enabled` 在本流程内始终为 false。

`apply-review` 校验完整批次后事务提交：精确记录集合、账号、快照、batch、record、revision、身份与采集门槛任一不符则整批拒绝；未知字段、身份改写、回复开关 true 也拒绝。读回确认新的 revision 与审计记录；结果未知时先查询，不重复写一个新批次规避幂等。

失败返回已脱敏 JSON、exit 2，且不写成功回执；调用方须同时核对退出码和回执，禁止把旧 out 文件当本次结果。`login_required` 在创建数据库前拒绝，不生成空盘点替代。

`eligible` 输出是计划而非采集结果：对象须人工确认客户分类、稳定身份已核验、客户归属非空、`collect_enabled=true`；待分类／私人／内部／排除和身份不明对象不合格。它不执行消息读取、草稿、发送或客服监听。

## 部署与质量分开登记

本地解析测试、候选端到端测试、真实云手机盘点、人工分类读回、日常消息采集是不同证据。记录每一项实际是否通过；任一缺失保留为 pending／blocked。只有真实部署后调用到固定 runtime、收到新 run 回执并独立读回结果，才能说该部署可运行。人工分类未完成时可以交付待分类列表，但不能声称已有生产采集名单。
