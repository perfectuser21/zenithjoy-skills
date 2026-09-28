# 考题 01 材料（考生只能看这一份）

被核验代码范围：`services/phone-adb-controller/workflow-result.sh`，提交 `0cd271e`（zenithjoy-workspace PR#1937 合并后）。
本次只核验**本文件**：判据要求的检查如果不在本文件里，按「缺失」记，并在 `note` 写明"不在本次范围"。
下面摘的是 `init` 与 `finalize` 两段，行号是该文件原始行号。

## 判据清单（来自 skill douyin-phone-runtime / 阶段契约，`level` 全为 must）

| id | 阶段 | 判据 |
|---|---|---|
| J1 | preflight | 设备身份已核对：serial、model 与租户登记一致 |
| J2 | preflight | 通话状态为空闲，否则立即停止 |
| J3 | preflight | 账号已核对：「我」页身份与目标账号一致，才算通过 |
| J4 | preflight | 已拿到设备锁，并保留 owner 证据 |
| J5 | cleanup | 关闭 App 之后，前台不再是抖音 |
| J6 | cleanup | 放锁之后，回读锁状态为 free |
| J7 | cleanup | 手机回到了安全桌面 |
| J8 | qualification | 判定阶段的 candidates_judged 等于输入的候选视频数 |
| J9 | cleanup | 收工时本次运行的阶段工件必须齐全（工件文件数不少于账本记录的阶段项数），否则本次运行判失败 |

## 代码（`workflow-result.sh`，节选）

```
76|     WFR_RUN_ID="social-keyword-leadgen-crontab-$TAG"
77|     WFR_HASH="$(calc_hash "$P" "$WF" "$PUSH")"
78|     WFR_RUN_DIR="$WFR_HOME/ledger/$WFR_RUN_ID"; WFR_ART_DIR="$WFR_HOME/workflow-runs"
79|     mkdir -p "$WFR_RUN_DIR" "$WFR_ART_DIR" 2>/dev/null || warn "mkdir failed errno: $(mkdir -p "$WFR_RUN_DIR" "$WFR_ART_DIR" 2>&1)"
80|     led1 init --run-id "$WFR_RUN_ID" --hash "$WFR_HASH" --profile "$P" --serial "$SERIAL" --hostkey "$HOSTKEY" >/dev/null
81|     export WFR_RUN_ID WFR_HASH WFR_RUN_DIR WFR_ART_DIR
82|     write_stage preflight completed 1 "device+account preflight by harvest-cron" \
83|       "[{\"type\":\"preflight\",\"serial\":\"$SERIAL\",\"hostkey\":\"$HOSTKEY\"}]" \
84|       '{"device_verified":1,"account_verified":0,"call_state_idle":1,"lock_acquired":0}'
85|     write_stage qualification blocked 1 "not_in_profile" '[]' '{"candidates_judged":0,"qualified":0}'
86|     write_stage scoring blocked 1 "not_in_profile" '[]' '{"comments_scored":0,"strong_intent":0,"weak_intent":0,"peer":0,"irrelevant":0,"spam":0}'
87|     echo "WFR_RUN_ID=$WFR_RUN_ID"; echo "WFR_HASH=$WFR_HASH"; echo "WFR_RUN_DIR=$WFR_RUN_DIR"; echo "WFR_ART_DIR=$WFR_ART_DIR";;
...
 99|   finalize)
100|     if not_initialized; then
101|       warn "called before init"
102|       echo "WFR_FINALIZE_OK=0"; echo "WFR_FINALIZE_MSG=not_initialized"
103|     else
104|       write_stage cleanup completed 1 "finalize by harvest-cron trap" '[{"type":"log","ref":"harvest-cron.log"}]' '{"close_app_attempts":0,"lock_released":1,"safe_desktop_visible":0}'
105|       n_files=$(ls "${WFR_ART_DIR:-}"/"${WFR_RUN_ID:-}"__*.worker-result.json 2>/dev/null | wc -l | tr -d ' ' || true)
106|       book="$(led show)"
107|       n_stages=$(printf '%s' "$book" | "$WFR_JQ" '[.stages[] | select(.status!="pending")] | length' 2>/dev/null || echo 0)
108|       n_items=$(printf '%s' "$book" | "$WFR_JQ" '[.stages[].items[]?] | length' 2>/dev/null || echo 0)
109|       if [[ -n "${WFR_SCP_TARGET:-}" ]]; then
110|         scp -q -o ConnectTimeout=20 "${WFR_ART_DIR:-}"/"${WFR_RUN_ID:-}"__*.worker-result.json "$WFR_SCP_TARGET" 2>/dev/null || warn "scp to MMV failed; artifacts kept locally"
111|       fi
112|       # 判据用产物(判定点 544cd6a3): 每条成功 write_stage 同时产 1 文件 + 1 账本 items 条目，
113|       # 故正常应有 n_files >= n_items。终审 C2 实证: 工件目录若从起跑前就不可写，write_stage
114|       # 全程写不进文件、也就全程没调 led1 set，n_files 与 n_stages 会一起停在 0，旧判据
115|       # n_files>=n_stages 在 0>=0 时假绿 OK=1；改用 n_items(而非 n_stages) 且要求其 >0 堵死这条假绿。
116|       if (( n_items > 0 && n_files >= n_items )); then echo "WFR_FINALIZE_OK=1"; echo "WFR_FINALIZE_MSG=artifacts=$n_files stages=$n_stages items=$n_items"
117|       else echo "WFR_FINALIZE_OK=0"; echo "WFR_FINALIZE_MSG=artifact_count_mismatch files=$n_files items=$n_items stages=$n_stages"; fi
118|     fi;;
119|   *) warn "unknown subcommand: $cmd";;
120| esac
```

（第 88～98 行是 `enter` 与 `stage` 子命令，与判据无关，已省略。）

## 交付

按 code-verify 的交付物格式输出一个 JSON。`subject` 写 `services/phone-adb-controller/workflow-result.sh@0cd271e`，`code_ref` 用上面的原始行号。
