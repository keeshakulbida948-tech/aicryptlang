# -*- coding: utf-8 -*-
"""统计本机字体可渲染的组合标记数量"""
import os
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8")
from fontTools.ttLib import TTFont, TTCollection

FONTS = ["msyh.ttc", "simsun.ttc", "simsunb.ttf", "mingliub.ttc",
         "NotoSansSC-VF.ttf", "SimsunExtG.ttf", "seguisym.ttf",
         "seguiemj.ttf", "arial.ttf", "times.ttf", "SimSunExtG.ttf"]
cm = set()
used = []
for fn in FONTS:
    p = os.path.join(r"C:\Windows\Fonts", fn)
    if not os.path.exists(p):
        continue
    try:
        fonts = TTCollection(p).fonts if fn.endswith(".ttc") else [TTFont(p, fontNumber=0)]
        for f in fonts:
            cm |= set(f.getBestCmap().keys())
        used.append(fn)
    except Exception as e:
        print("skip", fn, e)

marks = [cp for cp in range(0x300, 0x110000)
         if unicodedata.category(chr(cp)) in ("Mn", "Mc", "Me")]
cov = [cp for cp in marks if cp in cm]
print("fonts used:", used)
print("all marks :", len(marks))
print("covered   :", len(cov))
print("sample    :", [hex(c) for c in cov[:24]])
print("space(M=2):", len(cov) ** 2 * 33894)
