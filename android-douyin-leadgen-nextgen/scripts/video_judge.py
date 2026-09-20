#!/usr/bin/env python3
# video_judge.py --- 0920 video ASR+LLM judgment
import sys, json, base64, urllib.request, subprocess

WAV, TITLE, KW = sys.argv[1], sys.argv[2], sys.argv[3]
KEY = subprocess.check_output(["ssh", "xian-m4", "cat ~/.config/openclaw/locate-api.key"]).decode().strip()
URL = "https://toapis.com/v1/chat/completions"

def call(model, messages, max_tokens=800):
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())

with open(WAV, "rb") as f:
    audio_b64 = base64.b64encode(f.read()).decode()

asr_resp = call("gemini-3-flash-official", [
    {"role": "user", "content": [
        {"type": "text", "text": "\u8bf7\u628a\u8fd9\u6bb5\u97f3\u9891\u5b8c\u6574\u8f6c\u5199\u6210\u6587\u5b57\uff0c\u53ea\u8f93\u51fa\u8f6c\u5199\u6587\u672c\u3002"},
        {"type": "input_audio", "input_audio": {"data": audio_b64, "format": "wav"}}
    ]}
], max_tokens=1500)

transcript = ""
try:
    transcript = asr_resp["choices"][0]["message"]["content"].strip()
except Exception as e:
    print(json.dumps({"verdict": "review", "transcript": "", "reason": "ASR call failed: " + str(e) + "; raw=" + json.dumps(asr_resp)[:300]}, ensure_ascii=False))
    sys.exit(0)

if not transcript:
    print(json.dumps({"verdict": "review", "transcript": "", "reason": "empty transcript"}, ensure_ascii=False))
    sys.exit(0)

SYSTEM = "\u4f60\u662f\u83b7\u5ba2\u89c6\u9891\u5224\u5b9a\u5668\uff0c\u4e1a\u52a1=\u4eba\u5de5\u667a\u80fd\u8bad\u7ec3\u5e08\u804c\u4e1a\u6280\u80fd\u57f9\u8bad\u8003\u8bc1\u3002\u7ed9\u4f60\u4e00\u6761\u89c6\u9891\u7684\u6807\u9898+\u5b8c\u6574\u53e3\u64ad\u8f6c\u5199\u6587\u5b57\uff0c\u5224\u65ad\u8fd9\u6761\u89c6\u9891\u662f\u5426\u503c\u5f97\u8fdb\u5165\u8bc4\u8bba\u533a\u91c7\u96c6\u9636\u6bb5\u3002qualified=\u5185\u5bb9\u771f\u5b9e\u76f8\u5173\uff0c\u503c\u5f97\u91c7\u3002rejected=\u6807\u9898\u515a/\u5185\u5bb9\u65e0\u5173/\u7eafthe搬\u8fd0\u3002review=\u4e0d\u786e\u5b9a\uff0c\u4ea4\u4eba\u5de5\u3002\u53ea\u8f93\u51faJSON: {\"verdict\":\"qualified|rejected|review\",\"reason\":\"<=50\u5b57\"}"

judge_resp = call("gpt-5.6-terra-official", [
    {"role": "system", "content": SYSTEM},
    {"role": "user", "content": "keyword:" + KW + "\ntitle:" + TITLE + "\ntranscript:" + transcript[:2000]}
], max_tokens=200)

try:
    content = judge_resp["choices"][0]["message"]["content"].strip().replace("```json", "").replace("```", "").strip()
    verdict_obj = json.loads(content)
except Exception as e:
    print(json.dumps({"verdict": "review", "transcript": transcript, "reason": "judge parse failed: " + str(e)}, ensure_ascii=False))
    sys.exit(0)

print(json.dumps({
    "verdict": verdict_obj.get("verdict", "review"),
    "transcript": transcript,
    "reason": verdict_obj.get("reason", ""),
}, ensure_ascii=False))
