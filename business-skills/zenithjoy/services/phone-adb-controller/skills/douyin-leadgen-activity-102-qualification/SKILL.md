---
name: douyin-leadgen-activity-102-qualification
description: 交出有证据的视频资格结论。用于核对目标视频、录音转写并按公司政策判断资格或接手同一 Activity；不执行整个工作流。
metadata:
  change_summary: "对齐当前Activity合同、通用Checker与共享截止；不新增执行授权"
  version: 0.8.0
  primary_execution: agent-v1
  primary_hosts:
    - official-child-v1
  execution_transports:
    - raw-model-v1
  activity_ref: douyin_video_processing.qualification
  activity_version: 3.5.0
  validation: awaiting-real-run
  support_files:
    - services/phone-adb-controller/skills/douyin-leadgen-activity-102-qualification/references/sdk31-capture.md

  method_role: single-activity
  instruction_dependencies: self-contained

---

# 交出有证据的视频资格结论

仅执行 `douyin_video_processing.qualification`，使用业务合同版本 `3.5.0`。方法版本变化不修改Activity身份或公司业务政策。本版为说明重写，离线校验不等于实机验收。

## 合同、执行提案与独立验收

读取本run冻结的完整当前Activity Contract，核对来源、Activity身份、版本与摘要；输入输出、前后条件、DoD及已选公司政策以该合同为准，不从旧specific检查列表另立标准。执行者交付的是执行提案和原始证据，不是验收结论；独立通用Checker读取同一合同并用只读工具核实事实。模型自述、工具verified摘要或退出0不能代替原件，也不能替下一Activity判通过。

预算只引用冻结Activity Contract的 `budget` 与本run原绝对截止：业务受 `run.deadline_ms` 约束，收尾受 `run.cleanup_deadline_ms` 约束，实际可用时间取适用Activity预算和相应绝对截止的更早者。换Activity、恢复或新工具调用不重置剩余时间；不得挪用收尾窗口新增业务。

`agent_recovery` 仅声明方法可选能力，不是本次重试额度。只有本run实际冻结的 `runtime.checker_repair` 明确授权、剩余额度与原截止仍有效时，才按失败原因和证据进行允许的返工；没有该设置不自行增回合。保留原Task/run、动作身份和已成功成果；未知副作用先读回，未知不重做，不能换nonce或generation重放。返工不增加本次批次、评分、录制或发送授权，不重复已成功业务动作。Checker不执行业务写入，也不授予发送权。

## 执行上下文与工具边界

本文件就是本 Activity 的操作方法；不要求加载 Workflow 母 Skill 或旧业务 Skill。Workflow 决定活动顺序，本方法只完成当前输入指定的活动。

- 输入须明确真实 `task_id`、`run_id/run_tag`、`activity_ref`、公司/租户/业务线、公司配置与政策版本、处理范围、业务及收尾截止、实际工具与授权。已有 Task 只读回，不重复建单；缺身份或范围由调用方补齐，不从示例、最新目录或其他租户借值。
- 正式 Workflow 宿主给出的合同原件、方法/源码摘要、绑定、资源 owner 和工具 schema 都要核对；校验失败停止。普通 API 单 Activity 任务使用本任务明确授予、来源和作用域已核的工具，不伪造 Workflow ACK、actor、broker request 或冻结合同，也不因缺正式绑定而擅自切为手工模式。
- 下文是所需能力和已存在的操作名示例，不是新的工具注册或写入授权。用当前真实 schema/已部署签名确定调用；缺少合法单活动工具就报 `tool_unavailable`，不启动整条 Workflow、原 Activity handler 或任意裸 RPC/SQL顶替。保留原运行权限与公司校验。
- `execution_transport=raw-model-v1` 时不运行 shell、SSH、插件或子会话，只输出宿主 schema 的一个意图：`inspect`、`phone`、`business` 或 `finish`；`phone` 使用 `command,args`，`business` 使用 `operation,input`。不夹带最终 status/result。`finish` 只停止提意图，业务结果由独立通用Checker依据当前合同和宿主原始证据核验。
- 已绑定 child/失败接手只使用该次交接授予的工具和操作。旧 owner/child、连接或原生操作终态不明就保留隔离；不通过新 run、nonce 或 generation 重置次数。`resume` 仅在原宿主明确授予时按原共享额度执行，不能因为读了本 Skill 新增恢复权。返工必须另有本次冻结的 `runtime.checker_repair`，不能由方法声明推断额度。
- 原生调用采用本次工具已验证的执行超时并受当前合同剩余预算约束。工具返回running/session不是失败或已停止，沿同一session等真实返回，不并发重试或换EID；预算不足不启动新动作，未知终态由原owner收尾。
- 副作用保留同一持久动作身份；回执未知先读回，不换 ID 重交。数据与字段写入走已授权业务接口，凭据只经组织凭据工具/1Password取得，放入工具进程，不进正文、参数回显或日志。到业务截止停止新增业务，保留收尾预算。

## 输入与交付

输入本人已领取VID/规范链接、来源、公司冻结资格政策及版本、设备与实际账号上下文、录制/ASR/判断/保存工具、本次明确覆盖范围和截止。覆盖是全片还是获授权的前N秒，以本次合同为准；不从旧手册自动套“前5分钟=全文”或默认3倍速。

输出每VID `matched/rejected/unknown`、真实理由/政策、cached或fresh、原判断run、当前原生身份与音频/转写证据、持久判定读回。只有有效资格结果能交采集。

## 操作

1. 核当前本人视频租约、设备锁、真实公司和原生账号。按VID/deeplink进入详情并核当前页面/分享解析身份，不重走关键词搜索当成身份核验。存在他人、活跃或无法确定的受管录音时停止；不关应用干扰未知执行者。
2. 已授权、已确认无在途录制时，可按现有方法同owner关闭抖音再直接打开本VID，清理旧播放现场；之后重新核VID。只做此应用归位，不重启ADB、手机或网络，不为多音轨开例外。
3. 读取真实设备SDK及本次冻结能力配置，核实际获授权、已部署且成对验证的录制客户端/server与工具参数。SDK和版本用于选择已验证工具，不由方法另定业务资格标准；缺包、能力未经验证或摘要不符保unsupported/unknown，不跨模式回退或自行安装升级。
4. 保存开始/结束SDK原件、同包UID/前台、唯一started原生音轨、muted原因、client/server固定版本与SHA、本人录制PID和媒体原件。仅“started”、设置回显或UI看起来播放不够；外UID、共享UID、多音轨或解析不明停止。首错、退出码与阶段完整保留。
5. 播放控件只从当前完整树定位本包唯一“播放视频/暂停视频”且clickable/enabled、bounds有效节点，动作前后核原生音轨。只在原工具授权且同包唯一音轨、无活录制、明确仅stream/port音量静音时，执行其既有一次有界音量恢复；未知读回不循环按键。恢复失败保unknown，不以点击当作录制许可。
6. 从实际视频时长、已验证播放速度和本次覆盖范围算录制时长。不能只凭 `set-playback-speed` 回显把时长除3；未证实倍速按实际速度。分别核录制工具上限、ASR单请求上限及收尾预算；以当前批准ASR实际接口限制为准，不超限盲传。超长只用现有已授权分片方法覆盖本次范围；缺工具/预算记具体缺口，不截短后冒覆盖完成。
7. 复用原 `record-start/status/stop/extract-audio` 等实际工具，等待原生请求返回。校验容器、轨数/模式、真实媒体/音频时长、采样与声道、首末源身份和音量；恢复了容器也要核真实音轨。捕获近静音、全零PCM、App opt-out或多音轨仅说明捕获无效/未知，不把内容写成rejected。
8. ASR前核实际文件完整送达、摘要相符、ffprobe时长满足本次覆盖且每请求不超服务上限。分别保存provider/model/request或response ID、原错误码、文本/分片与实际调用；未暴露ID写unknown。`AUDIO_DURATION_TOO_LONG`、401/429、网络或格式错误是技术失败，不是空转写或内容不合格。只有当前工具能区分服务错误且不会误写内容结论时才调用其持久资格入口；已知旧入口混淆时报告 `qualification_tool_incompatible`，不重用其错误缓存。
9. 正常 `NO_WORDS/no_speech` 与捕获静音分开。缺有效转写时默认unknown，不用标题或旧ASR补成匹配；若当前冻结政策明示无语音分支，按该分支及真实证据执行。转写保留原文与保守校正依据，不凭模型补实词。
10. 只用公司冻结资格规则和实际授权判断工具，保存真实结论、原文依据及政策身份，再独立读取PG判定、转写、公司与VID。技术失败保持未决，不通过CLI退出0或“拒绝缓存命中”宣称内容已判。技术误写需当前明确授权的修复/重评入口；保留原失败与恢复结果，不直接SQL改分或改政策。
11. 缓存只复用同真实VID、公司/租户/政策版本匹配且原结论证据有效者。旧matched的原 `judgment_config.run_id`不重写；本轮资格回执另列cached/fresh、旧判断run、本轮原生身份摘要。正式采样交接仍须原run/binding/source SHA/VID的资格主span及原Step/Activity pass，失败或partial不放采集。

## 成功条件

本次所有目标VID都有可验证的真实资格结果；真实rejected可以是本活动完成结果，但不产生可采资格。存在捕获、ASR、身份或工具未知则相应VID为unknown并交partial/blocked。不打开评论采集、不评分、不替后续活动报完成。

## 副作用

获授权的详情导航、播放/有界音量恢复、本人的录制进程与音视频/转写工件，以及原资格判定持久化是本活动副作用。实际音频送当前批准ASR（现役为DashScope），视频原文/政策送当前批准判断服务（现役含OpenRouter）；记录实际服务/模型，不新增数据接收方。不采评论、发送、切号或改政策。

## 结果与验收

交付本次 Activity 的实际 `task_id/run_id/activity_ref`、`status`、`stop_reason`、输入对象身份、逐项结果、实际新增/历史/重复/未决计数、持久读回和证据位置、工具/模型实际调用与未知项、资源交接及副作用。工具或模型回执缺失写 unknown，不填 0；明确未调用才填 0。

执行提案中的 `success` 必须有本Activity合同要求的真实产物证据，仍须独立通用Checker验收；已提交部分成果但未达目标记 `partial`；缺授权、来源或工具记 `blocked`；实际调用失败记 `failed`；真实无输入记 `skipped/empty`。业务上的真实拒绝、无语音、捕获失败、空队列分别记录。Agent文字、脚本退出0、收尾成功都不能替代业务验收，不能据此替下一个 Activity 报成功。

## 宿主恢复能力声明

以下 `agent_recovery` 只描述可选能力，不能被解释为本次已选额度。实际是否允许返工及其次数只读本run冻结的 `runtime.checker_repair`；原授权、动作累计次数、未知不重做和绝对截止仍约束所有回合。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
