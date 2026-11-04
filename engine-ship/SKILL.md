---
name: engine-ship
version: 17.0.0
updated: 2026-11-04
description: /dev 创建PR后的候选交付接力。核对实际PR与完整HEAD，将事实、证据、actor写入Brain Task并读回，然后立即交engine-pr-watchdog监控CI和真实合并终态。
trigger: Superpowers finishing-a-development-branch 创建PR后，按 /dev 接力进入
---

所有输出使用简体中文。Task 是事件真身；知识按 Notion 知识库归位，PR 不是已合并交付。

## 1. 确认候选与有效门禁

在对应仓库的独立 worktree 中完成实际验收，提交全部候选改动并创建 PR。记录真实
Task UUID、owner/repo、PR 号、完整 40 位 Git HEAD、执行者与可读回证据。

保留目标仓库当前有效 DevGate；Cecelia 的事实、版本、DoD 门使用当前
`scripts/facts-check.mjs`、`scripts/check-version-sync.sh`、
`scripts/devgate/check-dod-mapping.cjs`。没有当前测试证据不写“通过”。
不要调用旧 Engine 目录下的清理、回调或 finalize 脚本来代替这些门。

不创建 Learning Markdown、handoff 镜像或 CURRENT_STATE 快照来满足交付仪式。
不运行旧快照生成器，不发送自动 Learning/fire-event 通知。历史文档与冻结证据保留原位。
需要记录本次经验时，把具体事实与证据写入本 Task；可复用知识另按用户授权写 Notion 真身。

## 2. 写入候选事实并读回

先在仓库外准备 JSON 文件，必须含非空 `facts` 字符串数组和非空 `evidence` 对象数组。
每个证据对象必须有 `path`、`sha256`、`command`、`result` 四个非空字符串字段。
`path` 为存在的绝对文件路径或 HTTPS URL；`sha256` 为 64 位十六进制。helper 对本地文件
计算真实 SHA256 并比对。HTTPS 引用仅验证结构，不下载、不代表远端产物或业务效果已验证。
`command` / `result` 填真实执行命令及结果，helper 不会执行所填命令；不要放凭据或原始日志。
未知项明确写未证，不能把模型/设备/生产效果填成已经验证。

从**本次实际加载**的 Skill 上下文填写 `LOADED_SKILL_MD`；不猜 Claude/Codex 专属变量，
不从旧 main、CWD 或其它安装位置回落加载 helper。下面整块在目标候选 worktree 执行。

```bash
# engine-ship candidate receipt
LOADED_SKILL_MD='<本次实际加载的SKILL.md绝对路径>'
if ! SHIP_HELPER=$(python3 - "$LOADED_SKILL_MD" <<'PYTHON'
from pathlib import Path
import re
import sys
try:
    loaded = Path(sys.argv[1])
    if not loaded.is_absolute():
        raise ValueError('必须给实际加载Skill绝对路径')
    skill = loaded.resolve(strict=True)
    parts = skill.read_text(encoding='utf-8').split('---', 2)
    if (skill.name != 'SKILL.md' or skill.parent.name != 'engine-ship'
            or len(parts) != 3 or parts[0].strip()
            or re.findall(r'^name:\s*(.+?)\s*$', parts[1], re.M) != ['engine-ship']
            or re.findall(r'^version:\s*(.+?)\s*$', parts[1], re.M) != ['17.0.0']):
        raise ValueError('Skill身份或版本不符')
    helper = skill.parent / 'scripts/record-candidate.py'
    if not helper.is_file() or helper.resolve(strict=True) != helper:
        raise ValueError('同release helper缺失或物理路径越界')
    print(helper)
except (OSError, ValueError):
    sys.exit(12)
PYTHON
); then
  echo 'SHIP_UNKNOWN: 无法确认实际加载Skill的同release helper' >&2
  exit 12
fi
python3 "$SHIP_HELPER" \
  --loaded-skill "$LOADED_SKILL_MD" \
  --task-id '<Task UUID>' --repo '<owner/repo>' --pr '<PR号>' \
  --head '<当前候选完整HEAD>' --actor '<执行者>' \
  --facts-file '<事实证据JSON绝对路径>' --dev-mode '<本仓.dev-mode绝对路径>' \
  --brain-url '<Brain API根地址>'
```

正常 Brain 根地址为 `http://localhost:5221`；该端口是生产 Brain 账本代理，仅交付本 Task
候选事件，不当测试服务。回归只使用本人隔离的 loopback HTTP 端口，不调用真实业务或通知。

helper 验真实 Git HEAD/干净树、GitHub PR 的仓库/URL/head/OPEN 状态、进行中的 Task 身份，
只 PATCH `result.ship_candidate`，随后 GET 精确读回。不会发送 Task status、generator_done、
终态 verdict 或 merged=true；因此不会把 PR 尚未合并写成 completed/PASS。

任何 API 失败、坏 JSON、身份未知、写失败或读回不一致均返回 12。保留工作树；已发生但未确认
的写入先读回核对，不重复伪报成功。若 PR 已 MERGED/CLOSED，直接交 watchdog 验真终态，
不要在这里猜测或覆盖终态。候选回执成功只代表候选事实已入账，不代表 GitHub CI/部署通过。

## 3. 接力到真实终态

候选回执读回后立即调用 `engine-pr-watchdog`。它负责当前 PR 的 CI 轮询、失败修复、合并状态
确认与 Task 终态 handoff；未知不能当绿，CLOSED 未合并不能写 PASS。

helper 在 Task 候选回执精确读回后，才把当前工作树中同 Task 的 `step_4_ship` 标为 done。
这个本地阶段仅表示“候选已交付”，Task 仍为 in_progress；写入或读回失败保持 pending。
不创建 Learning 文件来绕开旧门。只有当前执行现场真实加载的门才按当前合同验收；
磁盘上的旧 hook 不作为恢复旧流程的理由。

handoff 的 `next_steps` 每条保留明确 kind：`resume_headed` / `dispatch_headless` /
`decision` / `note`。无下一步用 note 明确“完成，无下一步”。不主动创建仓库 Markdown 镜像。

**完成后下一 tool call 必须加载并执行 `engine-pr-watchdog`，使用本次真实 PR、repo 与 Task。**
