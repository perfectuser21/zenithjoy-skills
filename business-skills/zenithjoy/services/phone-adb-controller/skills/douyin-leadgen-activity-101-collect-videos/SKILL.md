---
name: douyin-leadgen-activity-101-collect-videos
description: 按关键词交出筛选后的视频链接。用于采集关键词搜索结果或接手同一视频发现 Activity；不执行整个工作流。
metadata:
  change_summary: "0.8.0: 在Activity内整合有效业务步骤，去除母Skill和旧Skill执行依赖，保留原合同与授权边界"
  version: 0.8.0
  primary_execution: agent-v1
  primary_hosts:
    - official-child-v1
  execution_transports:
    - raw-model-v1
  activity_ref: douyin_video_discovery.collect_videos
  activity_version: 5.1.1
  validation: awaiting-real-run
  support_files: []

  method_role: single-activity
  instruction_dependencies: self-contained

---

# 按关键词交出筛选后的视频链接

仅执行 `douyin_video_discovery.collect_videos`，保留业务合同版本 `5.1.1`。方法版本变化不修改Activity身份或公司业务政策。本版为说明重写，离线校验不等于实机验收。

## 执行上下文与工具边界

本文件就是本 Activity 的操作方法；不要求加载 Workflow 母 Skill 或旧业务 Skill。Workflow 决定活动顺序，本方法只完成当前输入指定的活动。

- 输入须明确真实 `task_id`、`run_id/run_tag`、`activity_ref`、公司/租户/业务线、公司配置与政策版本、处理范围、业务及收尾截止、实际工具与授权。已有 Task 只读回，不重复建单；缺身份或范围由调用方补齐，不从示例、最新目录或其他租户借值。
- 正式 Workflow 宿主给出的合同原件、方法/源码摘要、绑定、资源 owner 和工具 schema 都要核对；校验失败停止。普通 API 单 Activity 任务使用本任务明确授予、来源和作用域已核的工具，不伪造 Workflow ACK、actor、broker request 或冻结合同，也不因缺正式绑定而擅自切为手工模式。
- 下文是所需能力和已存在的操作名示例，不是新的工具注册或写入授权。用当前真实 schema/已部署签名确定调用；缺少合法单活动工具就报 `tool_unavailable`，不启动整条 Workflow、原 Activity handler 或任意裸 RPC/SQL顶替。保留原运行权限与公司校验。
- `execution_transport=raw-model-v1` 时不运行 shell、SSH、插件或子会话，只输出宿主 schema 的一个意图：`inspect`、`phone`、`business` 或 `finish`；`phone` 使用 `command,args`，`business` 使用 `operation,input`。不夹带最终 status/result。`finish` 只停止提意图，业务结果由宿主工具记录与独立读回确定。
- 已绑定 child/失败接手只使用该次交接授予的工具和操作。旧 owner/child、连接或原生操作终态不明就保留隔离；不通过新 run、nonce 或 generation 重置次数。`resume` 仅在原宿主明确授予时按原共享额度执行，不能因为读了本 Skill 新增恢复权。显式额外回合策略仍只接受原合同唯一键 `max_additional_turns=1`；默认无额外回合，raw 回合原冻结上限仍为 1～64，不增加原预算。
- 原生调用采用已验证的执行超时并受当前剩余预算约束；旧controller可能需要300000ms。工具返回running/session不是失败或已停止，沿同一session等真实返回，不并发重试或换EID；预算不足不启动新动作，未知终态由原owner收尾。
- 副作用保留同一持久动作身份；回执未知先读回，不换 ID 重交。数据与字段写入走已授权业务接口，凭据只经组织凭据工具/1Password取得，放入工具进程，不进正文、参数回显或日志。到业务截止停止新增业务，保留收尾预算。

## 输入与交付

输入已通过的设备/账号上下文、公司与 line、关键词及其任务/公司启用配置来源、排序/时间/地区/时长/范围筛选、唯一成功视频上限、尝试/屏数上限和截止。数量缺失先从当前任务或运营配置取，仍缺则由调用方补齐；不把某次1条冒烟当默认产能。

输出逐视频真实 `video_id/video_url/title/author/keyword/harvest_batch` 与 `discovery_metrics`：同视频原始点赞/页面评论显示值、解析值或 null、分档、观测时间、身份与证据摘要。业务字段 `comment_count` 保留102“已采评论数量”语义，不存页面评论总数。另报实际成功唯一VID数、尝试数、重复观测、停止原因和 `all_results_scanned`。

## 操作

1. 每批手机动作前核当前资源 owner、目标设备与账号上下文。若原生请求仍在途，等待真实返回，不并起第二条操作。controller支持命令和owner参数的范围要逐项核；不为绕过不支持的owner参数而去掉权限检查。
2. 按当前工具支持的搜索能力打开 URL 编码关键词，进入“视频”页。已有操作示例为 `open-search ENCODED_KEYWORD`、`search-video-tab EID`；不发明 `search` 或 `open-app douyin` 等参数。新鲜树确认关键词、页签及前台。
3. 在结果页直接调用现有筛选操作，不先手点一次再让复合动作点第二次。已部署形式示例：`search-time-layer TIME EID SORT DURATION SCOPE LOCATION`；六项均来自本次输入。保存面板、选中项、结果三份原件，核各实际选项；参数合法不等于原生UI已支持。
4. 用 `search-video-cards EID` 等能力读当前卡片，排除相关搜索词、广告入口、占位。保留卡片原槽位、标题、时长与新鲜坐标；确认页面仍新鲜后按工具返回坐标打开（如 `tap-evidence X Y EID`）。不按标题做公司业务资格判断，也不用标题相同代替同VID。
5. 对每个实际详情调用一次当前取链能力（如 `current-video-link EID [RETURN_KEYWORD]`），保留共享URL、解析URL、规范链接、真实平台ID和当前详情证据。`content_type=note`、`note_id` 只记排除项，绝不改名为video_id。复制失败或结果未知不把上一条剪贴板链接填进本候选。
6. 离开详情前，将同次详情XML/截图与本次解析VID对应。点赞数、页面评论总量保留原文与时间；解析万/亿等单位。缺数字、带+、不精确或越界显示记 `value=null` 并说明原因，不填0；评论分档为 `zero/1_100/101_500/over_500/unknown`。真实0评论可以留发现观察，但不得伪装为有评论的待采输入；持久化工具不能区分观察与待采状态时保留原件并报接口缺口。
7. 经公司/来源校验的正式写入能力提交，再按同一VID/链接独立读回公司、来源和本轮观测。当前合同要求 `discovery_metrics_verified=1`；仅旧 discover ACK、数据库默认0或旧观测不足以通过。新字段未发布时保存带VID的持久指标工件及 `metrics_persistence_missing`，结果为partial/failed，不宣称专用指标已入库。
8. 同VID重复观测幂等，只有本次同等或更新观测按接口规则接受；保持原资格、transcript、102进度、comment_count、已采视频原batch。新增/重复/历史分别计数；旧行不能冒本轮新增。
9. 取链返回note或临时搜索框后，用已有归位能力返回相同关键词与筛选，重新核页面，不把临时搜索框当新的任务。按授权继续当前屏/翻屏；达到数量、尝试或截止分别记 `limit_reached/attempt_limit_reached/deadline`，重复屏或加载停滞记 `stalled`。只有明确且范围匹配的页尾原件才能记 `exhausted`。

## 有界首屏输入

保留当前正式 `Run.discovery_input`：schema1 的 `max_candidates` 限首屏卡片数，超额零候选动作；schema2 的 `max_attempts` 限实际尝试，只试前N个原槽位。两模式互斥、唯一关键词、单首屏，不翻屏、不恢复视口、不用重入重置额度。重复、缺身份、失败均耗尝试；失败或未知按原安全规则停止，不为凑N补槽。`target_count` 是独立成功唯一VID上限。schema2已知无失败且达到尝试N时，可完成有界采样，但必须 `all_results_scanned=false`，不能声称新增N条或搜尽。

## 成功条件

本轮真实视频身份、原生筛选、指标与来源均有原件，实际持久行和专用指标独立读回通过，计数/停止原因可回算。只交发现结果；不录音、不判断视频业务资格、不采评论、不调用103，也不释放共享设备资源。

## 副作用

实际副作用包括搜索/筛选/详情导航、工具取链带来的剪贴板变化、截图/XML工件，以及经授权的视频/指标持久化。关键词、卡片/链接可交本次批准的解析/定位工具；不发送评论、点赞、关注、私信或作品，不调ASR/评分。

## 结果与验收

交付本次 Activity 的实际 `task_id/run_id/activity_ref`、`status`、`stop_reason`、输入对象身份、逐项结果、实际新增/历史/重复/未决计数、持久读回和证据位置、工具/模型实际调用与未知项、资源交接及副作用。工具或模型回执缺失写 unknown，不填 0；明确未调用才填 0。

`success` 必须满足本活动下文的可观察成功条件；已提交部分成果但未达目标记 `partial`；缺授权、来源或工具记 `blocked`；实际调用失败记 `failed`；真实无输入记 `skipped/empty`。业务上的真实拒绝、无语音、捕获失败、空队列分别记录。Agent文字、脚本退出0、收尾成功都不能替代业务验收，不能据此替下一个 Activity 报成功。

## 宿主恢复声明

以下仅保留原方法的可选恢复能力声明，不授予本次执行额度；只有原run合同明确且合法选定时生效，仍受上文原owner终态、nonce/generation、共享操作次数和原绝对截止约束。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
