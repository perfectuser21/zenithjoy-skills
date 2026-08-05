# Janitor etime 八进制换算 bug 修复设计

日期：2026-08-05
Brain task：ecbd6c8b-4c96-4825-bfbd-db2fda2117ca
决策：616183dc（bug-fix）
来源：memory handoff_0805_janitor_octal_bug_load_root（本设计已修正其两处归因）

## 问题（已实测复现）

`janitor/janitor.sh` 的 `etime_to_secs()` 处理 `ps -o etime` 的 `DD-HH:MM:SS` 形态时，
第 105 行 `secs=$((days * 86400))` 对 `days=08`（运行满 8~9 天的进程）按八进制解析，
触发 bash 致命算术错误 `value too great for base`：

- `$()` 子 shell 直接退出 → 函数返回**空串**（不是 0）
- 调用点（271-272 / 328-329 行）`[ "" -lt $threshold ]` 报 `integer expression expected`，
  返回码 2 → `&& return` 不执行 → 控制流**穿透阈值保护**直落 `is_orphan` 判定（fail-open）
- 每轮 frequent 对每个 8+ 天进程刷 2 行错；kill 日志秒数为空

时分秒片段（111-113 行）有 `${parts[0]#0}` 去一个前导零护着，etime 字段恒 2 位，实测不炸；
但写法脆弱，本次一并统一。

现场触发源：pid 64880（node，etime `08-16:10:29`）等 8 天+ 进程。

## 修法

### 1. `etime_to_secs()` 加固（janitor/janitor.sh 98-116 行）

- 入参格式校验：不匹配 `^([0-9]+-)?[0-9]{1,2}(:[0-9]{2}){0,2}$` 或为空 → `echo 0` 返回（杜绝空串出口）
- 全部算术改 `10#` 强制十进制：
  - `secs=$((10#$days * 86400))`
  - `secs=$((secs + 10#${parts[0]}*3600 + 10#${parts[1]}*60 + 10#${parts[2]}))`（2/1 段同理）
- 保持函数签名、缩进、注释风格不变

### 2. 调用点空值兜底（271-272 / 328-329 行两处）

```bash
secs=$(etime_to_secs "$elapsed")
[ -z "$secs" ] && { echo "$(date '+%Y-%m-%d %H:%M:%S') [frequent] etime_to_secs 解析失败 elapsed=$elapsed pid=$pid，保守跳过"; secs=0; }
```

空/0 → 走既有 `[ "$secs" -lt "$threshold" ] && return` 按"未达阈值"保守跳过（fail-safe：
宁可不杀，不可带着坏数据进 kill 路径）。兜底带日志（fail-loud），不静默。

### 3. 守卫测试（proven-to-fire）

新文件 `janitor/__tests__/janitor_etime_octal.test.sh`：

- **从 janitor.sh 实文件用 sed 提取 `etime_to_secs` 函数体并 eval**（不复制粘贴实现，
  防测试与实现漂移；改回旧写法必然报红）
- 样本与断言（stderr 重定向捕获，同时断言无 `value too great` 错误输出）：

| 样本 | 期望秒数 | 覆盖点 |
|---|---|---|
| `08-16:10:29` | 749429 | 真实触发形态，days=08 八进制炸点 |
| `09-00:00:01` | 777601 | days=09 炸点 |
| `3-08:00:00` | 288000 | 单位数 days + HH=08 |
| `1-02:03:04` | 93784 | 正常 days 回归 |
| `00:08:30` | 510 | HH=00 + MM=08 |
| `08:09` | 489 | MM:SS 两段形态 08/09 |
| `45` | 45 | 单段形态 |
| 空串 | 0 | 兜底出口 |
| `garbage` | 0 | 非法输入出口 |

### 4. CI 机器闸门

`.github/workflows/lint-skills.yml` 的 lint-skills job 加一步（与既有
`Regression — post-pr-create rewrite/* 豁免` 同格式）：

```yaml
- name: Regression — janitor etime 八进制换算
  run: bash janitor/__tests__/janitor_etime_octal.test.sh
```

该仓 CI 不自动发现测试文件，不点名 = 假守卫。

## 守卫种类判定

接缝是纯 bash 字符串/算术逻辑（逻辑接缝），CI test 即为正确守卫形态，
无需运行时自检（janitor 本身就在本机 cron 跑，修完可直接用真实 `ps -o etime` 回放验证）。

## 测试策略

- **unit**：上表 9 样本断言（本次核心，proven-to-fire：commit-1 对旧实现必须红）
- **integration**：本地 `bash janitor/janitor.sh --mode=frequent` 干跑一轮，
  确认 stderr 无 `value too great` / `integer expression expected`（当前机器实存 8 天+ 进程，
  天然具备触发条件）——作为 PR 前人工验证，不进 CI（CI 无 8 天进程）
- **E2E**：不适用（无 UI/服务）

## 不做

- 不改 audiomxd 兜底逻辑（根治需主理人决策：关蓝牙/重启/迁移 Brain）
- 不动 is_orphan 判定逻辑
- 不迁移现有 grep 式旧测试

## commit 顺序（TDD 铁律）

1. commit-1 `fix(janitor): 增加 etime 八进制换算守卫测试（红）`——测试 + CI 接线，对旧实现红
2. commit-2 `fix(janitor): etime_to_secs 强制十进制 + 调用点空值兜底（绿）`
