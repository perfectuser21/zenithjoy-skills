#!/usr/bin/env python3
"""日报输出后置检查器：扫价格编造 + 隐含资源承诺。
用法: python3 post_check.py <日报文件.md> [--json]
退出码: 0=干净 1=有违规
设计给经济档模型(DeepSeek/mini/Haiku)生产链路兜底; 命中行需人工改写或用 §13.1 标准句式替换。"""
import json, re, sys

# 价格数字/量级(产品价格未提供时任何数字量级都算编造; X/XX 占位符除外)
PRICE = [
    r'(几|数)(千|万|十万|百万)',
    r'(上|近|超)?百万级?',
    r'[0-9]+(\.[0-9]+)?\s*(元|块钱?|万元?|千元?)(?![件个家条名位])',
    r'(降到|提升|回本|回报|ROI)[^。\n]{0,8}[0-9]+(\.[0-9]+)?\s*[%％倍]',
    r'[0-9]+(\.[0-9]+)?\s*[%％]\s*(的)?(提升|增长|回报|转化)',
]
# 隐含既有资源承诺(案例/数据/报价单/模型/做法 + 发送/展示/拥有语义)
RES = r'(案例|数据|报价单|价格表|模型|截图)'          # 宽匹配：不含"做法/效果"（会误伤"负责任的做法是…给您看到进展"）
RES2 = r'(案例|数据|报价单|价格表|模型|做法|截图|效果)'  # 窄语境("发个/看一个"后)可用全集
PROMISE = [
    RES + r'[^。\n]{0,15}(发您|发你|发过去|给您看(?!到)|给你看(?!到)|一并发|马上整理|整理好|今天[^。\n]{0,4}发您|明天[^。\n]{0,4}发您)',
    r'(发个|发一个|给您看一个|给你看一个)[^。\n]{0,15}' + RES2,
    r'我们(正好|确实)?有[^。\n]{0,12}' + RES,
    r'服务过[^。\n]{0,12}(家|个|位|不少)',
    r'帮[^。\n]{0,10}(同行|客户)[^。\n]{0,15}(从[^。\n]{0,8}(降|升)到|做到)',
    r'(行业|赛道)[^。\n]{0,10}(成本|获客|转化)[^。\n]{0,8}(模型|数据|区间)',
]
# 高风险承诺
RISK = [r'保(证)?(成交|回本|效果|上量)', r'(无条件|全额)退款']
# 同句已标注"待补充/未提供/核实"的降级为提示
SAFE = re.compile(r'(未提供|待补充|待核实|核实后|确认后|内部确认|可以对外|可对外|能对外|暂无法|不给您拍|无法提供|待产品信息|发我吗|发我一份|发我看|能发我)')
# 否定/拒绝语境
# 违禁承诺类(保成交等)整句出现否定/边界词即豁免——这类词几乎只在"划边界"语境出现
NEG_LINE = re.compile(r'(不|别|勿|拒绝|不要|不能|不得|禁止|放弃|避免|没法|无法|超出|不承诺|不接受|不签|坚决不|警惕|风险|边界)')
# 价格/资源承诺类只认紧邻(6字内)的祈使否定，防止"我们不是标准件。我们帮同行从XX降到YY"被误豁免
NEG_STRICT = re.compile(r'(不要|不得|禁止|避免|不能|不会|无法|没法|勿|别|拒绝|放弃)[^。\n]{0,6}$')

def check(text):
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for cat, pats in (('价格编造', PRICE), ('隐含资源承诺', PROMISE), ('违禁承诺', RISK)):
            for p in pats:
                m = re.search(p, line)
                if m:
                    # 命中位置前 12 字符内或整句含否定/拒绝语境 → 提示不判违规
                    ctx = line[max(0, m.start()-12):m.start()]
                    if SAFE.search(line):
                        level = '提示(同句已标注待补充)'
                    elif (cat == '违禁承诺' and NEG_LINE.search(line)) or NEG_STRICT.search(ctx):
                        level = '提示(否定语境)'
                    else:
                        level = '违规'
                    hits.append({'line': lineno, 'level': level, 'category': cat,
                                 'matched': m.group(0), 'text': line.strip()[:120]})
                    break
    return hits

if __name__ == '__main__':
    text = open(sys.argv[1]).read() if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else sys.stdin.read()
    hits = check(text)
    viol = [h for h in hits if h['level'] == '违规']
    if '--json' in sys.argv:
        print(json.dumps({'violations': viol, 'warnings': [h for h in hits if h['level'] != '违规']}, ensure_ascii=False, indent=1))
    else:
        for h in hits:
            print(f"[{h['level']}] L{h['line']} {h['category']}: {h['matched']} | {h['text']}")
        print(f"—— 违规 {len(viol)} 处，提示 {len(hits)-len(viol)} 处")
    sys.exit(1 if viol else 0)
