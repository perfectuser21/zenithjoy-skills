#!/usr/bin/env python3
"""熟化员 v2：findings/escalation 自由文本 → 归一化判例 → ≥3 次开 Brain 任务（本地账本幂等）。
默认演练（不发）；--fire 才 POST。用法: maturation_v2.py --ledger opened.json [--fire] [--base-sha SHA] findings.md escalation.log
key 策略：--key cause（默认，原因子句，同根因合一）| --key stem（主干60字，会把同根因按尾巴拆多条，仅对比用）。"""
import re, sys, json, collections, urllib.request, argparse
BRAIN = "http://localhost:5221/api/brain/tasks"
def strip_head(s):
    s = re.sub(r'^\[[^\]]*\]\s*(\[[^\]]*\]\s*)*', '', s).replace('[固化候选]', '')
    s = re.sub(r'auto\d{8}[-\w]*|单#\d+|PID\s*\d+', '<TAG>', s); s = re.sub(r'\d+(\.\d+)?', '<N>', s)
    return re.sub(r'未注册|不存在|不可用|未连接', '<节点不可达>', s)
def key_stem(s):
    s = re.sub(r'本批|该TAG', '本批', strip_head(s)); return re.sub(r'[；;，,。.、\s]+', ' ', s).strip()[:60]
def key_cause(s):
    s = strip_head(s)
    m = re.search(r'(指定节点[^；;，,。]*<节点不可达>|节点[^；;，,。]*<节点不可达>|WRONG_FOREGROUND|TARGET_ABSENT[^；;，,。]*|锁[^；;，,。]{0,12}|日志路径[^；;，,。]{0,10})', s)
    return m.group(1)[:40] if m else re.sub(r'[；;，,。.、\s]+', ' ', s).strip()[:40]
def task_open(tid):
    try:
        t = json.load(urllib.request.urlopen(f"{BRAIN}/{tid}", timeout=8)); t = t.get('task', t)
        return t.get('status') not in ('completed', 'archived', 'cancelled', 'failed')
    except Exception:
        return True  # 查不到按仍 open：宁可不开，不可重复开
ap = argparse.ArgumentParser(); ap.add_argument('--ledger', required=True); ap.add_argument('--fire', action='store_true')
ap.add_argument('--base-sha', default=''); ap.add_argument('--key', choices=['cause', 'stem'], default='cause'); ap.add_argument('files', nargs='+')
a = ap.parse_args(); keyf = key_cause if a.key == 'cause' else key_stem
grp, first, last = collections.Counter(), {}, {}
for p in a.files:
    for l in open(p, encoding='utf-8'):
        l = l.rstrip('\n')
        if not l.strip(): continue
        k = keyf(l); grp[k] += 1
        st = (re.match(r'^\[([^\]]*)\]', l) or [None, '?'])[1]; first.setdefault(k, st); last[k] = st
try: ledger = json.load(open(a.ledger))
except FileNotFoundError: ledger = {}
opened, skipped = [], []
for k, c in grp.most_common():
    if c < 3: continue
    if k in ledger and task_open(ledger[k]): skipped.append((k, c, ledger[k])); continue
    body = {"title": f"[熟化员自动开单] {k[:40]}，{c}次复现（{first[k]}→{last[k]}）", "priority": "P1",
            "mutation_intent": "write", "change_kind": "bugfix", "repo_hint": "zenithjoy-workspace",
            "map_scope_hint": ["keyword_acquisition"], "base_sha": a.base_sha,
            "description": f"熟化四态 ≥3 自动触发。判例: {k}\n复现: {c} 首次: {first[k]} 最近: {last[k]}\n证据: {' '.join(a.files)}",
            "payload": {"gp_anchor": "line02/keyword_acquisition keep-green", "source": "maturation_v2",
                        "case_key": k, "count": c, "first": first[k], "last": last[k]}}
    if a.fire:
        req = urllib.request.Request(BRAIN, json.dumps(body, ensure_ascii=False).encode(), {'Content-Type': 'application/json'})
        ledger[k] = json.load(urllib.request.urlopen(req, timeout=15)).get('id')
    opened.append((k, c, ledger.get(k, '(演练)')))
json.dump(ledger, open(a.ledger, 'w'), ensure_ascii=False, indent=1)
print(json.dumps({"key": a.key, "cases": len(grp), "ge3": sum(c >= 3 for c in grp.values()), "skipped_open": len(skipped),
                  ("opened" if a.fire else "would_open"): [(k[:50], c, t) for k, c, t in opened]}, ensure_ascii=False, indent=1))
