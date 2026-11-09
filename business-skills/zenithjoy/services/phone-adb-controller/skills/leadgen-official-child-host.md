# official-child-v1 内部正式宿主兼容合同

仅适用于显式声明本宿主的新版本101、102、103 Activity方法的正常 `mode=execute`，每次只执行一个Activity。旧run、旧Method、失败接手、104和 `raw-model-v1` 都保留各自原合同，不因本文改变。

准入由父进程执行，Agent不自行造证。原run必须同时冻结 `execution_mode=agent` 与 `primary_host=official-child-v1`；`execution_transport` 和 `max_turns` 缺省，不能临时设环境值、把raw回合冒充官方child，或从旧方法推定兼容。所选Method必须有 `metadata.primary_hosts` 对本宿主的显式声明，且真实Skill name/version/source/digest、支持文件、Activity合同和整个来源闭包均与本次冻结一致。

只有不可绕过的本宿主入口完成以下实际核验，才兼容中央 `actor=common-runner`、`source_kind=internal`。原 `actor=runtime:phone-adb-controller:agent-v1` 的旧入口不放宽，也不按actor字符串、Agent自报origin、序列化JSON或外部ACK授予内部执行权：

1. canonical run UUID、Task、唯一 `run_binding_id`、真实中央 `task_run_id` 和当前Activity/slot精确关联，中央不可变定义与本run来源一致；Task的实际CommonRunner投影和同run reconciliation读回一致，Task仍live且允许本活动。
2. 本进程liveMap拥有的真实identity/run_binding、中央定义 `runtime_snapshot_sha256` 及每run冻结 `local_snapshot_sha256` 全部核对；本轮 `request.public_domain` 四字段只由该父进程生成，不接受child构造或改写。固定源码校验、`readFrozen` 与 `validateAgentInput` 通过，Method/Activity身份及文件摘要一致；缺任一身份或活性证据均阻断。
3. 同tenant/company及其冻结政策、profile/serial/account（适用时）、当前资源租约和epoch、原Activity与Workflow绝对截止均有效。授权与工具执行前后继续由父进程核liveTask、liveMap和原授权；不凭一次旧快照延续过期执行权，不刷新TTL、预算或恢复次数。

正式官方child仍核其真实官方session/run/request及本次request/nonce绑定，只使用本request的受控 `inspect`、`phone`、`business` 模板；操作以本Activity实际暴露schema为准，不扩大白名单。Agent不直接调用内部RPC、裸队列、CLI/SSH、绑定创建或改actor。锁、公司账号、owner、资源、输入范围、额度与截止仍由Runner管理。

正常执行不能用 `resume`、原Activity handler或整工作流脚本代替本Activity。副作用仍用原持久operation/producer身份；结果未知只查原记录，不换ID重放。父owner已归还且官方child真实终态均有证据，且所有primitive和producer journal实际封闭，才可判执行停止；child文字、模型完成、CLI退出0均不代替。任一未知保留needs_review与原隔离，不清场释放未知资源。

业务结果仍由原合同独立verify、Step原件与PG持久读回裁判；宿主兼容不是业务PASS、公司资格或评分政策改变，也不解封104或赋予发送权限。本版本仍为awaiting-real-run。
