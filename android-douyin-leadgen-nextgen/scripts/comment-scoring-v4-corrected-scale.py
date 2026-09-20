import json, urllib.request, time, subprocess

KEY = subprocess.check_output(["ssh","xian-m4","cat ~/.config/openclaw/locate-api.key"]).decode().strip()
URL = "https://toapis.com/v1/chat/completions"
SP = "/private/tmp/claude-501/-Users-administrator-worktrees-zenithjoy-session-e208f474/e208f474-4896-48cd-a990-712ff9ccca9d/scratchpad"
samples = json.load(open(f"{SP}/feishu_lead_samples.json"))

SYSTEM = """你是社媒评论分拣器，业务=人工智能训练师职业技能培训考证。判断这条评论的「业务相关性」。

真实判定标准(0914主理人拍板，非常宽松)：
- 只要评论跟视频的AI/考证/学习/职业话题沾边——哪怕只是纯情绪反应、复述内容、简短互动，只要不是明确谈别的专业/别的工作/纯数字刷屏——都算「相关」，要留档（哪怕意向很低）。
- 只有两类明确排除：①同行企业号/竞对账号 ②广告引流软文(如"扣1就涨""加微信""互关互粉")。
- 讨论完全不相关的专业/职业(汽车维修/殡葬/保险等)、纯数字("666")、单纯询问对方工作而非表达自己意愿，判「不相关」。

示例校准：
- "咨询一下谢谢！"（报考流程视频下）→ 相关
- "绝了"（AI教程视频下的赞叹）→ 相关（C级低意向，也要留）
- "学AI锁定三个大神。第一个吴恩达。第二个李宏毅。第三个李沐"→ 相关（在讨论AI学习路径，即使无明确需求）
- "幸福瞬间🥰"（AI转型视频下的情绪反应）→ 相关
- "怎么长的跟石楠花一样[憨笑]"（纯调侃无关内容）→ 不相关
- "我汽车维修与检测都学两年了"（完全不同专业）→ 不相关
- "扣1就涨，已经帮助500+"（导流话术）→ 不相关（广告）
- "你现在在干什么工作呢？"（问对方而非表达自己意愿）→ 不相关

只输出JSON不要markdown：{"relevant":true/false,"reason":"不超过30字"}"""

def call_model(model, comment_text, video_title, region):
    user_msg = f"来源视频：{video_title}\n评论者地区：{region}\n评论原文：{comment_text}"
    body = {"model": model, "messages":[{"role":"system","content":SYSTEM},{"role":"user","content":user_msg}], "max_tokens":150,"temperature":0}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={"Authorization":"Bearer "+KEY,"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        r = json.loads(resp.read().decode())
    c = r["choices"][0]["message"]["content"].strip().replace("```json","").replace("```","").strip()
    return json.loads(c)

def run_eval(model_name):
    results = []
    for s in samples:
        try:
            out = call_model(model_name, s["comment_text"], s.get("source_video",""), s.get("region","未知"))
            pred = out.get("relevant", False)
        except Exception as e:
            results.append({**s, "pred": None, "error": str(e)[:150]}); continue
        gt = s["entered_final_lead"]
        results.append({"comment": s["comment_text"][:40], "gt": gt, "pred": pred, "reason": out.get("reason",""), "agree": pred==gt})
        time.sleep(0.15)
    valid=[r for r in results if r.get("pred") is not None]
    agree=[r for r in valid if r["agree"]]
    tp=sum(1 for r in valid if r["gt"] and r["pred"]); tn=sum(1 for r in valid if not r["gt"] and not r["pred"])
    fp=sum(1 for r in valid if not r["gt"] and r["pred"]); fn=sum(1 for r in valid if r["gt"] and not r["pred"])
    print(f"=== {model_name} (v4 corrected scale) ===")
    print(f"有效={len(valid)}/{len(samples)} 一致率={len(agree)}/{len(valid)}={len(agree)/len(valid)*100:.1f}% TP={tp} TN={tn} FP={fp} FN={fn}")
    for r in valid:
        if not r["agree"]:
            print(f"  MISMATCH gt={r['gt']} pred={r['pred']} | {r['comment']!r} | {r['reason']}")
    return results

r = run_eval("gpt-5.6-terra-official")
json.dump(r, open(f"{SP}/v4_terra_results.json","w"), ensure_ascii=False, indent=2)
