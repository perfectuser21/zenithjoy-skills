# 考题 02 材料（考生只能看这一份）

被核验代码范围：zenithjoy-workspace `services/phone-adb-controller/`，提交 `e6fd729d`，下面节选的四个文件片段。
本次只核验**下面给出的代码**：判据要求的检查如果不在这些片段里，按「缺失」记，`code_ref` 填 null，并在 `note` 写明"不在本次范围"或"片段内没有对应检查"。
行号是各文件的原始行号，`code_ref` 用 `文件名:行号` 写。

## 判据清单（来自获客 skill 的落池、触达阶段契约，`level` 全为 must）

| id | 阶段 | 判据 |
|---|---|---|
| X1 | delivery | 评论写入飞书评论池后，必须回查确认这条记录真的存在，才算落池成功 |
| X2 | delivery | 本批一条线索都没落池（0 条）时，阶段不得记为 completed |
| X3 | outreach | 选单预写「触达中」之后，必须回读确认写入成功（状态、分发号、话术 ID 与预期一致），才可以动手机 |
| X4 | outreach | 私信发出后，回写线索表（状态、发送状态、触达时间等）必须确认写入成功，失败要有处理 |
| X5 | outreach | 点发送之前，输入框里的文字必须与审批过的话术逐字一致，否则停止 |
| X6 | outreach | 点发送之后，必须在界面上读到刚发出的那条气泡，才能判为已发送 |
| X7 | outreach | 发送前必须确认手机不在通话中，否则立即停止 |

## 代码节选

### 文件 A：`push-raw-comments.js`（评论写入飞书评论池）
```
50|       "评论原文": comment || "", "评论者昵称": nick || "",
51|       // 0915 主理人逐列验收拍板: 独立字段成列;「用户主页标识」拼串保留双写(存量兼容,勿再新增读取方)
52|       "用户主页标识": [id||"", purl||"", atype||""].filter(Boolean).join(" | "),
53|       "抖音号": id || "", "主页链接": purl || "", "账号类型": atype || "",
54|       "留言时间": cdate || "", "主页IP": (pip||"").trim(),
55|       "地区": region || "", "处理状态": "待分拣",
56|     }};
57|     const res = await (await fetch(`https://open.feishu.cn/open-apis/bitable/v1/apps/${B}/tables/${POOL}/records`, { method: "POST", headers: H, body: JSON.stringify(body) })).json();
58|     if (res.code === 0) { created++; seen.add(rid); }
59|     else console.log("FAIL", nick, JSON.stringify(res).slice(0,100));
60|   }
61|   console.log(`落池 ${created} | 去重 ${dup} | 输入 ${lines.length}`);
62| })();
```

### 文件 B：`batch2.sh`（落池后记账本，zsh）
```
101|   ssh -o ConnectTimeout=20 mmv "set -a; source ~/.credentials/zenithjoy-db.env 2>/dev/null; set +a; node .../push-videos.js /tmp/$TAG.tsv $TAG $LINE && node .../push-raw-comments.js /tmp/$TAG.tsv $TAG $LINE" >> $LOG 2>&1
102|   prc=$?
103|   # 账本 delivery: 落池 ssh 的出口码决定 completed/failed; readback_verified 由探针读回(checks/ YAML)填,这里不硬编码
104|   if (( prc == 0 )); then
105|     wfr stage delivery completed 1 "pushed $NL leads" '[{"type":"log","ref":"'"$LOG"'"}]' '{"leads_written":'"$NL"',"duplicates_skipped":0,"readback_verified":0,"cursor_updates":0}'
106|   else
107|     wfr stage delivery failed 1 "push rc=$prc" '[{"type":"log","ref":"'"$LOG"'"}]' '{"leads_written":0,"duplicates_skipped":0,"readback_verified":0,"cursor_updates":0}'
108|   fi
109|   print "[$(date +%H:%M:%S)] 已落池(视频+评论)" >> $LOG
```
（`$NL` 是本批 TSV 里 LEAD 行的数量，在此片段之前已算出。）

### 文件 C：`next-outreach.js`（触达选单器，节选两段）
```
 57|     }
 58|     const res = await (await fetch(`https://open.feishu.cn/open-apis/bitable/v1/apps/${B}/tables/${LEADS}/records/${rid}`, { method: "PUT", headers: H, body: JSON.stringify({ fields }) })).json();
 59|     console.log(res.code === 0 ? "MARKED " + result : "MARK_FAIL " + JSON.stringify(res).slice(0,120));
 60|     return;
 61|   }
...
103|   const sender = Math.random() < 0.5
104|     ? { profile: "jinoshengyuan-work", id: "langzi63485", label: "小号1 躺赢AI学姐" }
105|     : { profile: "legacy", id: "44997267357", label: "小号2 人工智能小诺考评" };
106|   // 预写触达中(防 tick 重入)
107|   await fetch(`https://open.feishu.cn/open-apis/bitable/v1/apps/${B}/tables/${LEADS}/records/${pick.record_id}`, { method: "PUT", headers: H, body: JSON.stringify({ fields: {
108|     "状态": "触达中", "话术ID": txt(sc.fields["话术ID"]), "话术版本": ver,
109|     "话术内容": msg, "客服编号": txt(sc.fields["客服编号"]) || "无", "客服电话": txt(sc.fields["客服电话"]) || "",
110|     "实际分发号": sender.label + "(" + sender.id + ")", "分配序号": sent + 1,
111|   }}) });
112|   console.log(JSON.stringify({ rid: pick.record_id, nick, dyid, profile_url: lead.profileUrl, ver, script_id: txt(sc.fields["话术ID"]),
113|     msg_b64: Buffer.from(msg).toString("base64"), profile: sender.profile, sender_id: sender.id, seq: sent + 1, dup: Number(pick.fields["重复命中次数"])||0 }));
```
（第 58～59 行属于 `done` 回写模式：私信发出后回写线索表；第 103～113 行属于 `next` 选单模式。）

### 文件 D：`douyin-phone-adb`（手机控制器，`private-message-send` 的一段，zsh）
```
1518|   "$ADB" -s "$SERIAL" shell input tap "$input_x" "$input_y"
1519|   wait_ms 300
1520|   "$ADB" -s "$SERIAL" shell am broadcast -a ADB_CLEAR_TEXT >/dev/null
1521|   "$ADB" -s "$SERIAL" shell am broadcast -a ADB_INPUT_B64 --es msg "$message_b64" >/dev/null
1522|   wait_ms 700
1523|   typed_xml="$EVIDENCE_ROOT/${evidence_id}-typed.xml"
1524|   ui_evidence "${evidence_id}-typed" >/dev/null
1525|   typed_value="$(/usr/bin/xmllint --xpath 'string(//node[@resource-id="com.ss.android.ugc.aweme:id/msg_et"]/@text)' "$typed_xml" 2>/dev/null || true)"
1526|   [[ "$typed_value" == "$message" ]] || die "private-message text readback did not exactly match approved text"
1527|   before_path="$(snapshot_evidence "${evidence_id}-before-send")"
1528|   send_line="$(/usr/bin/grep -oE '<node[^>]+content-desc="发送"[^>]*>' "$typed_xml" | /usr/bin/head -1 || true)"
1529|   [[ -n "$send_line" && "$send_line" == *'clickable="true"'* ]] || die "verified send action was not found after exact text readback"
1530|   send_center="$(node_center "$send_line")" || die "send action bounds could not be parsed"
1531|   read send_x send_y <<< "$send_center"
1532|   "$ADB" -s "$SERIAL" shell input tap "$send_x" "$send_y"
1533|   wait_ms 1200
1534|   restore_ime
1535|   trap - EXIT INT TERM
1536|   sent_xml="$EVIDENCE_ROOT/${evidence_id}-sent.xml"
1537|   ui_evidence "${evidence_id}-sent" >/dev/null
1538|   /usr/bin/grep -F "text=\"$message\"" "$sent_xml" >/dev/null || die "send outcome is unknown because the exact sent bubble was not readable"
1539|   sent_path="$(snapshot_evidence "${evidence_id}-sent")"
1540|   print -- "send_status=sent"
```
（`ui_evidence` 是抓取当前手机界面控件树 XML 并存成文件的函数；`die` 会终止脚本并以非零码退出。）

## 交付

按 code-verify 的交付物格式输出一个 JSON。`subject` 写 `services/phone-adb-controller/{push-raw-comments.js,batch2.sh,next-outreach.js,douyin-phone-adb}@e6fd729d`。
