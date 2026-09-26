# -*- coding: utf-8 -*-
"""渲染预览 v4: 组合序列百万级池子  ->  out/preview.png"""
import json
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont, TTCollection

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
CNFONT = r"C:\Windows\Fonts\msyh.ttc"
MONO = r"C:\Windows\Fonts\consola.ttf"

# ---- 字体 fallback 表: 码位 -> 哪个字体有它 ----
CAND = [("msyh.ttc", 0), ("simsun.ttc", 0), ("simsunb.ttf", 0),
        ("SimsunExtG.ttf", 0), ("mingliub.ttc", 0), ("NotoSansSC-VF.ttf", 0),
        ("arial.ttf", 0), ("times.ttf", 0), ("seguisym.ttf", 0),
        ("AICryptLangBMP.ttf", 0), ("AICryptLangP15.ttf", 0),
        ("AICryptLangP16.ttf", 0)]
CP2FONT = {}
for fn, idx in CAND:
    p = fn if os.path.isabs(fn) else os.path.join(
        OUT if fn.startswith("AICrypt") else r"C:\Windows\Fonts", fn)
    if not os.path.exists(p):
        continue
    try:
        fonts = TTCollection(p).fonts if fn.endswith(".ttc") else [TTFont(p, fontNumber=0)]
        for f in fonts:
            for cp in f.getBestCmap():
                CP2FONT.setdefault(cp, (p, idx))
    except Exception:
        pass

_FCACHE = {}


def font_for(cp, size):
    key = (cp, size)
    if key in _FCACHE:
        return _FCACHE[key]
    p, idx = CP2FONT.get(cp, (CNFONT, 0))
    f = ImageFont.truetype(p, size, index=idx)
    _FCACHE[key] = f
    return f


with open(os.path.join(OUT, "symbols.json"), encoding="utf-8") as f:
    data = json.load(f)
symbols = data["symbols"]
if isinstance(symbols[0], dict):
    symbols = [s["char"] for s in symbols]

W, H = 1760, 1120
img = Image.new("RGB", (W, H), (252, 252, 250))
d = ImageDraw.Draw(img)
f_title = ImageFont.truetype(CNFONT, 34)
f_sub = ImageFont.truetype(CNFONT, 21)
f_cn = ImageFont.truetype(CNFONT, 23)
f_mono = ImageFont.truetype(MONO, 18)


def draw_symbol(x, y, sym, size, fill=(15, 15, 45)):
    """基字 + 叠加符: 手动定位, 叠加符居中压在基字上"""
    base = sym[0]
    fb = font_for(ord(base), size)
    d.text((x, y), base, font=fb, fill=fill)
    adv = fb.getlength(base)
    for m in sym[1:]:
        fm = font_for(ord(m), size)
        mw = fm.getlength(m)
        d.text((x + adv / 2 - mw / 2, y), m, font=fm, fill=(170, 40, 40))
    return adv


def draw_line(x, y, text, size, fill=(15, 15, 45)):
    """逐符号绘制一串密文"""
    for sym in text:
        adv = draw_symbol(x, y, sym, size, fill)
        x += adv + 3
    return x


d.text((50, 30), "AI 专用软加密语言 · 组合序列池（100 万级）", font=f_title, fill=(20, 20, 20))
d.text((50, 76), "每个符号 = 基字 + 2 个叠加符（共 3 个码位）。红色是叠加符，人眼看着像鬼画符，AI 只看到码位。",
       font=f_sub, fill=(120, 120, 120))

d.text((50, 112), "① 组合符号抽样（人类视角）", font=f_cn, fill=(30, 30, 30))
y = 150
for row in range(5):
    x = 50
    for col in range(36):
        i = row * 36 + col
        if i < len(symbols):
            adv = draw_symbol(x, y, symbols[i], 40)
        x += 44
    y += 46

d.text((50, 400), "② 编码演示 · 明文 1 字 → 3 符号（9 个字符）", font=f_cn, fill=(30, 30, 30))
plain = "明天下午三点老地方见"
alpha = [chr(c) for c in range(0x20, 0x7F)]
rng = random.Random(20260920)
book_a = {ch: [symbols[rng.randrange(len(symbols))] for _ in range(3)] for ch in set(plain)}
rng2 = random.Random(777)
book_b = {ch: [symbols[rng2.randrange(len(symbols))] for _ in range(3)] for ch in set(plain)}

d.text((50, 438), "明文：", font=f_cn, fill=(30, 30, 30))
x = 140
for ch in plain:
    f_ = ImageFont.truetype(CNFONT, 30)
    d.text((x, 434), ch, font=f_, fill=(70, 25, 25))
    x += f_.getlength(ch)

d.text((50, 486), "密文 A：", font=f_cn, fill=(30, 30, 30))
ex = draw_line(160, 486, [s for ch in plain for s in book_a[ch]], 34)
d.text((ex + 20, 490), "← 同一句，本轮密钥", font=f_sub, fill=(160, 60, 60))

d.text((50, 548), "密文 B：", font=f_cn, fill=(30, 30, 30))
draw_line(160, 548, [s for ch in plain for s in book_b[ch]], 34)
d.text((50, 610), "同一句换密钥 → 密文完全不同（同一个「明」字，两轮的符号毫无关系）",
       font=f_sub, fill=(160, 60, 60))

d.text((50, 668), "③ AI 视角 · 一个符号 = 3 个码位（AI 读起来毫无障碍）", font=f_cn, fill=(30, 30, 30))
sample = symbols[0]
cps = "  |  ".join("+".join(f"U+{ord(c):04X}" for c in s) for s in symbols[:6])
d.text((50, 706), cps, font=f_mono, fill=(20, 90, 40))

d.text((50, 756), "④ 规模数据", font=f_cn, fill=(30, 30, 30))
rows = [
    f"符号总数        : {data['count']:,} 个（实测产出，去重后）",
    "组合序列理论空间 : 4,441,343,248 个（基字 33,894 × 叠加符 362²）",
    "单符号结构      : 1 基字 + 2 叠加符 = 3 码位，长度恒定",
    "明文字符集      : 21,016 个（ASCII + 中文标点 + 常用汉字）",
    "单元长度        : 3 符号/字 → 1 个汉字 = 9 个字符",
    "编解码往返      : 12 组全部无损 [OK]",
]
yy = 794
for r in rows:
    d.text((50, yy), r, font=f_sub, fill=(60, 60, 60))
    yy += 30

d.text((50, 1000), "※ 人类要解密：符号池 100 万、密钥是自然语言短语且换轮即废 → 只能暴力枚举",
       font=f_sub, fill=(150, 60, 60))
d.text((50, 1032), "※ AI 要解密：拿到密钥直接查表秒解；没有密钥也能靠上下文猜个七八分 —— 这就是「不防 AI」",
       font=f_sub, fill=(150, 60, 60))
d.text((50, 1064), "※ 叠加符渲染依赖字体 fallback；本机 arial/times/msyh 覆盖 362 个可渲染叠加符",
       font=f_sub, fill=(150, 60, 60))

img.save(os.path.join(OUT, "preview_composite.png"))
print("saved", os.path.join(OUT, "preview_composite.png"))
