# 工具合同

路径、源码摘要、公司/设备绑定由本任务提供，不能从别的租户补齐。凭据走credentials/1Password；缓存权限600，不进正文或日志。

## 冻结和绑定

runtime-receipts.mjs的prepare只冻结发布、合同、工具闭包；bind-run通过Brain定义接口取得真实ACK；两者均不启动业务或模型会话。计划参数取已核plan，不能手造定义/摘要/ACK。导出的freezeDefinition等构建函数不等于已注册的独立公开API，调用它们也不把新Skill变成旧release已发布的主方法；正式方法版本需有自己的注册、发布与观测。

先选真实设备实例再冻结。ZJ_ADB_HOST_CONFIG只影响控制器，不改变已冻结scope。schema2实例由已部署defaultDiscoveryPhoneScope/defaultCollectionPhoneScope与freezeDefinition组合，使用登记实例和合同要求的真实epoch，保留原发布、源码、任务和实例守卫。缺合法组装入口则runtime_binding_missing；不改ACK，不把5042动作冒充5041合同完成。独立Codex需有其真实owner的准入验证；不能把claimed_by或result伪填为common-runner。ADB_INSTANCE_EPOCH_RUN_DIR说明缺运行上下文，不足以证明手机离线。

## 手机

复用已部署控制器的预检、精确owner锁、截图/树、证据点击、输入、取链、安全桌面。先核runtime-contract和真实命令定义、控制器及锁助手摘要。中央租约owner为本任务ID，本地锁owner为本轮唯一身份；可用central-device-lease.mjs调用原Brain接口。取得后读回owner和期限，动作前保持有效。未知原生进程未停止时保留隔离，不释放别人锁。

定位取新鲜树，每次页面变化留截图、关键页留XML。只用安全取链动作获取平台链接。工具拒绝某owner/动作组合时报告缺口，不删owner参数绕检查；不裸启动或重启共享ADB。

## 数据

已核部署的leadgen-client.mjs提供createRpc({frozen,local:true,environment,runContext})。frozen/binding来自本轮真实文件；environment.WF_HOME为冻结runtime；runContext含run、binding.run_id、profile、line。来源和执行身份仍由RPC校验。不能import裸队列、构造pool或写SQL。

| 用途 | kind / 操作 |
|---|---|
| 公司 | queue / company_config，带阶段及手机设备绑定 |
| 关键词 | keywords，取本公司已启用词 |
| 短链 | resolve_share_link，输入实际复制链接 |
| 101 | queue / discover、discover_readback |
| 102 | queue / claim_videos、comment_history、collect_partial、collect、sample_readback |
| 103 | queue / score_scope、score、policy_review、mark_leads、bridge_outreach、bridge_readback |
| 104 | 原outreach领取、prepared、写回及读回协议 |

精确字段读本轮固定实现，不能凭表猜参数。旧discover无metrics，新版要求canonical URL及同视频真实指标，不能混用。新版指标用discovery-metrics从原件生成并读回。

public-domain当前拒绝outreach。101/102/103接口可用不代表104发送接口已就绪；104使用独立批准域，没有原订单prepared接口就停止。

## 运行回执

执行入口通过Brain execution-callback记录开始和终态，使用同一task/run。回执被拒时独立读回任务与task_runs，区分运行事实、任务状态和自动重排；HTTP200或duplicate不等于终态落库。沿真实状态机归位，保留actor/事实/证据。

## 独立工具接口

候选运行通过本轮私有工具连接提供 inspect、phone、business。`phone/open-search-card` 只接卡片索引与证据ID，由工具即时重读卡片并完成定位取链；不开放任意坐标。每个证据ID只允许一次实际尝试。宿主首次启动留O_EXCL记录，不能崩溃后重建实例清空数量或未知提交账。

模型外发与控制器视觉降级见主Skill「数据外发」。`external-interactions.jsonl` 按唯一request_id/intent计数，returned不能替代请求计数；没有该账本或未核实际模型调用时回执为unknown。API模型tool/view_image用量另从实际事件与usage取，不与OpenRouter重复计数。
