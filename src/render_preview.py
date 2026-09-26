# -*- coding: utf-8 -*-
"""渲染预览 v3: 真实编码演示范例  ->  out/preview.png"""
import json
import os
import random

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SYMFONT = os.path.join(OUT, "AICryptLang-Regular.ttf")
CNFONT = r"C:\Windows\Fonts\msyh.ttc"
MONO = r"C:\Windows\Fonts\consola.ttf"

W, H = 1760, 1090
img = Image.new("RGB", (W, H), (252, 252, 250))
d = ImageDraw.Draw(img)

f_title = ImageFont.truetype(CNFONT, 34)
f_sub = ImageFont.truetype(CNFONT, 21)
f_cn = ImageFont.truetype(CNFONT, 23)
f_sym = ImageFont.truetype(SYMFONT, 46)
f_sym_s = ImageFont.truetype(SYMFONT, 34)
f_mono = ImageFont.truetype(MONO, 19)

with open(os.path.join(OUT, "symbols.json"), encoding="utf-8") as f:
    data = json.load(f)
symbols = data["symbols"]
pua = [s for s in symbols if len(s["char"]) == 1 and 0xE000 <= ord(s["char"]) <= 0xF8FF]


def mix_text(x, y, text, size=44, fill=(15, 15, 40)):
    fc = ImageFont.truetype(CNFONT, size)
    fs = ImageFont.truetype(SYMFONT, size)
    for ch in text:
        o = ord(ch)
        is_cn = 0x4E00 <= o <= 0x9FFF or ch in "，。：！？（）、"
        f_ = fc if is_cn else fs
        d.text((x, y), ch, font=f_, fill=(70, 25, 25) if is_cn else fill)
        x += f_.getlength(ch)
    return x


d.text((50, 30), "AI 专用软加密语言 · 符号池 & 编码演示", font=f_title, fill=(20, 20, 20))
d.text((50, 76), "图形 = 人类看到的；码位 = AI 看到的。同一串符号，意义由本轮上下文临时赋予。",
       font=f_sub, fill=(120, 120, 120))

d.text((50, 112), "① 自造字形抽样 · 私用区（人类视角，装字体后可见）", font=f_cn, fill=(30, 30, 30))
y = 150
for row in range(5):
    x = 50
    for col in range(30):
        i = row * 30 + col
        if i < len(pua):
            d.text((x, y), pua[i]["char"], font=f_sym, fill=(15, 15, 40))
        x += 56
    y += 60

d.text((50, 470), "② 编码演示 · 同一句话，本轮密钥 vs 下一轮密钥（结果完全不同）", font=f_cn, fill=(30, 30, 30))
plain = "明天下午三点老地方见"
rng = random.Random(20260920)
book_a = {ch: "".join(rng.choice(pua)["char"] for _ in range(2)) for ch in set(plain)}
rng2 = random.Random(777)
book_b = {ch: "".join(rng2.choice(pua)["char"] for _ in range(2)) for ch in set(plain)}

d.text((50, 508), "明文：", font=f_cn, fill=(30, 30, 30))
mix_text(140, 506, plain, size=32)
d.text((50, 560), "密文 A：", font=f_cn, fill=(30, 30, 30))
ex = mix_text(160, 556, "".join(book_a[c] for c in plain), size=40)
d.text((ex + 30, 560), "← 同一个「明」字，两轮完全不同 →", font=f_sub, fill=(160, 60, 60))
d.text((50, 622), "密文 B：", font=f_cn, fill=(30, 30, 30))
mix_text(160, 618, "".join(book_b[c] for c in plain), size=40)

d.text((50, 692), "③ 本轮映射表（只在本轮有效，换轮即废）", font=f_cn, fill=(30, 30, 30))
items = list(book_a.items())[:10]
for i, (ch, sym) in enumerate(items):
    col, row = i % 5, i // 5
    x = 50 + col * 340
    yy = 730 + row * 62
    d.text((x, yy), ch, font=ImageFont.truetype(CNFONT, 32), fill=(30, 30, 30))
    d.text((x + 42, yy + 2), "=", font=f_sub, fill=(140, 140, 140))
    d.text((x + 68, yy), sym, font=f_sym_s, fill=(15, 15, 40))

d.text((50, 862), "④ AI 视角 · 它读到的就是这些码位（毫无难度）", font=f_cn, fill=(30, 30, 30))
d.text((50, 898), " ".join(s["cp"] for s in pua[:12]), font=f_mono, fill=(20, 90, 40))

from collections import Counter
cnt = Counter(s["pool"] for s in symbols)
d.text((50, 946), f"总符号 {data['count']}  |  自造字形(私用区) {len(pua)}  |  池子 {len(cnt)} 类",
       font=f_sub, fill=(60, 60, 60))
d.text((50, 976), "   ".join(f"{k}:{v}" for k, v in cnt.most_common(7)), font=f_sub, fill=(60, 60, 60))
d.text((50, 1018), "⚠ 不装 AICryptLang-Regular.ttf 时 ①②③ 的符号显示为豆腐块 □ —— 人类连看都看不了",
       font=f_sub, fill=(150, 60, 60))
d.text((50, 1046), "⚠ 对 AI 无影响：符号以 UTF-8 传输，AI 按码位/语义理解，装不装字体都一样",
       font=f_sub, fill=(150, 60, 60))

img.save(os.path.join(OUT, "preview.png"))
print("saved", os.path.join(OUT, "preview.png"))
