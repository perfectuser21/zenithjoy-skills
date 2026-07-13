# Harness 七 skill EVA 评分标准（RUBRIC）

> 首份 07-05 RUBRIC 文档随 worktree 蒸发（只剩 memory 摘要），本文件为重建版并自 v2 起入库为 SSOT。

## 总框架（100 分制）

- **静态契约审计 /40**：只读当前 SKILL.md 全文，四个子维度各 /10。子维度按 skill 角色定制（见各 skill 的 BASELINE 分项表），共性口径：
  1. 指令确定性：硬检查是否机械可执行（grep/bash 闸 vs 自觉 checklist）、有无软词漏洞、有无引用未定义变量/不存在文件
  2. 接口协议一致性：与上下游 skill 的交接字段、文件路径、格式约定逐条比对（不是看声称，是逐字核对两侧文本）
  3. 失败路径与容错：断供/恢复/异常场景是否有交代与出口
  4. 角色核心纪律硬度（TDD/反作弊/APPROVED 判据/完成判据等，按棒次定制）
- **实战行为审计 /60**：只认真实运行证据，禁止用"文本写了"顶替"实际发生了"。证据源：
  - worktree 台账 `.harness/progress.md` + verdicts/ 附件
  - sprint 产物（sprint-prd.md / contract-draft.md / contract-dod.md / tests/ / e2e-verify.sh）
  - GitHub PR（commits 顺序、files、merge 状态）
  - Brain DB（relay-runs、initiative_run_events、decisions、learnings、tasks.result）
  - 证据不足的维度**保守记分并显式标注**，禁止脑补
  - 新修复无实战 run 证据 → 该维度按"待取证"保守给分，显式标注解锁条件

## 评分纪律

- 每个分项必须给一句证据（文件:行号 / 台账行 / API 行 / SQL 结果）
- 正反例都计：全通 run 是正分证据，失败 run 的归因决定扣谁的分（编排层失败不扣 generator）
- "系统级归因"要写明（如 task.result 为 null 是 Brain PATCH 不写列，不全算 report 的锅），但事实照记
- 版本间对比必须标注证据面差异（v2 证据面比 v1 深，分数下降可能是审得深而非退步）
