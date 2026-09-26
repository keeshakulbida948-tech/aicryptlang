# -*- coding: utf-8 -*-
"""
AI 专用软加密语言 —— 程序化造字器 (Procedural Glyph / Font Generator)
=====================================================================
用法:
    python gen_font.py --n 30000 --out ./out

作用:
    给"无字形"的码位 (PUA / 私用区) 程序化生成**互不相同**的图形,
    打包成 TTF 字体 -> 人类装上字体就能"看得见这些符号", 但记不住、猜不出.

为什么要造字:
    Unicode 私用区 U+E000~U+F8FF 等码位在标准字体里没有图案,
    人类看到的是豆腐块 □. 造字后变成"像真文字但看不懂"的图形,
    这才达成"人类看得见->理解不了, AI 读码位->毫无障碍".

字形算法:
    网格量化 + 随机笔画(四边形轮廓) + 可选实心块, 用签名去重保证不重样.
"""
import argparse
import json
import os
import random

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

# ----------------------------------------------------------------------
# 字形生成
# ----------------------------------------------------------------------
GRID = 9          # 9x9 网格
CELL = 95         # 每格 95 单位
ORIGIN = 70       # 左上偏移
STROKE_W = 62     # 笔画粗细(单位)


def _pt(i, j):
    return (ORIGIN + i * CELL, ORIGIN + j * CELL)


def _stroke_quad(p1, p2, w=STROKE_W):
    """把一条线段变成有厚度的四边形轮廓 (否则零面积, 渲染不可见)"""
    (x1, y1), (x2, y2) = p1, p2
    dx, dy = x2 - x1, y2 - y1
    L = (dx * dx + dy * dy) ** 0.5
    if L == 0:
        return None
    nx, ny = -dy / L * w / 2.0, dx / L * w / 2.0
    return [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny),
            (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]


def _clockwise(pts):
    """保证外轮廓为顺时针 (TrueType 填充规则)"""
    area = 0.0
    for k in range(len(pts)):
        x1, y1 = pts[k]
        x2, y2 = pts[(k + 1) % len(pts)]
        area += x1 * y2 - x2 * y1
    return pts if area < 0 else pts[::-1]


def make_glyph(rng, n_stroke, n_fill):
    """返回 (contours, signature)"""
    contours, sig = [], []
    for _ in range(n_stroke):
        i1, j1 = rng.randrange(GRID), rng.randrange(GRID)
        # 偏好正交/短对角线 -> 更像"文字"而不是涂鸦
        i2 = min(GRID - 1, max(0, i1 + rng.choice([-2, -1, 0, 0, 1, 2])))
        j2 = min(GRID - 1, max(0, j1 + rng.choice([-2, -1, 0, 0, 1, 2])))
        if (i1, j1) == (i2, j2):
            i2 = min(GRID - 1, i1 + 1)
        p1, p2 = _pt(i1, j1), _pt(i2, j2)
        q = _stroke_quad(p1, p2)
        if q:
            contours.append(_clockwise(q))
            sig.append(tuple(sorted([(i1, j1), (i2, j2)])))

    for _ in range(n_fill):
        ci, cj = rng.randrange(GRID - 1), rng.randrange(GRID - 1)
        shape = rng.choice(["square", "tri", "hex"])
        if shape == "square":
            pts = [_pt(ci, cj), _pt(ci + 1, cj), _pt(ci + 1, cj + 1), _pt(ci, cj + 1)]
        elif shape == "tri":
            pts = [_pt(ci, cj + 1), _pt(ci + 1, cj + 1), _pt(ci + 1, cj)]
        else:
            pts = [_pt(ci, cj), _pt(ci + 1, cj), _pt(ci + 1, cj + 1),
                   _pt(ci, cj + 1), _pt(ci - 1, cj + 1), _pt(ci - 1, cj)]
        contours.append(_clockwise(pts))
        sig.append(("F", ci, cj, shape))

    return contours, tuple(sorted(sig, key=str))


def gen_glyph_table(n, seed):
    rng = random.Random(seed)
    table, seen = {}, set()
    tries = 0
    while len(table) < n and tries < n * 60:
        tries += 1
        n_stroke = rng.randint(4, 7)
        n_fill = 1 if rng.random() < 0.25 else 0
        contours, sig = make_glyph(rng, n_stroke, n_fill)
        if sig in seen:
            continue
        seen.add(sig)
        table[len(table)] = contours
    return table


# ----------------------------------------------------------------------
# 打包 TTF
# ----------------------------------------------------------------------
def build_font(symbols, out_path, font_name="AI CryptLang", seed=99,
               full_pua=False):
    """symbols: [{'cp','char'}...] -> 写字体; full_pua=True 时覆盖整个私用区"""
    if full_pua:
        cps = []
        for a, b in [(0xE000, 0xF8FF), (0xF0000, 0xFFFFD), (0x100000, 0x10FFFD)]:
            cps += [cp for cp in range(a, b + 1) if (cp & 0xFFFE) != 0xFFFE]
        pua = [{"char": chr(cp)} for cp in cps]
    else:
        def _is_pua(ch):
            if len(ch) != 1:
                return False
            c = ord(ch)
            return (0xE000 <= c <= 0xF8FF) or (0xF0000 <= c <= 0xFFFFD) \
                or (0x100000 <= c <= 0x10FFFD)

        chars = [s["char"] for s in symbols if _is_pua(s["char"])]
        if not chars:
            chars = [s["char"] for s in symbols if len(s["char"]) == 1]
        pua = [{"char": c} for c in chars]
    print(f"   待造字码位: {len(pua)}")

    table = gen_glyph_table(len(pua), seed)
    print(f"   已生成字形: {len(table)} (去重通过)")

    glyph_order = [".notdef"]
    cmap, glyphs, metrics = {}, {}, {}

    notdef_pen = TTGlyphPen(None)
    notdef_pen.moveTo((100, 0)); notdef_pen.lineTo((100, 700))
    notdef_pen.lineTo((600, 700)); notdef_pen.lineTo((600, 0)); notdef_pen.closePath()
    glyphs[".notdef"] = notdef_pen.glyph()
    metrics[".notdef"] = (700, 100)

    n_built = 0
    for s in pua:
        idx = n_built % len(table) if table else 0
        if idx not in table:
            continue
        name = f"g{ord(s['char']):05X}"
        pen = TTGlyphPen(None)
        for contour in table[idx]:
            pen.moveTo(contour[0])
            for p in contour[1:]:
                pen.lineTo(p)
            pen.closePath()
        glyphs[name] = pen.glyph()
        metrics[name] = (1000, 100)
        cmap[ord(s["char"])] = name
        glyph_order.append(name)
        n_built += 1

    print(f"   写入 cmap: {len(cmap)} 个码位")

    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=900, descent=-100)
    fb.setupNameTable({
        "familyName": font_name, "styleName": "Regular",
        "uniqueFontIdentifier": font_name + " Regular",
        "fullName": font_name, "psName": font_name.replace(" ", "") + "-Regular",
        "version": "Version 1.0",
    })
    fb.setupOS2(sTypoAscender=900, sTypoDescender=-100,
                usWinAscent=900, usWinDescent=100,
                sxHeight=500, sCapHeight=700)
    fb.setupPost()
    fb.save(out_path)
    return out_path, len(cmap)


def _build_one(glyphs_list, out_path, font_name, seed):
    """glyphs_list: [char, ...] -> 写单个字体 (限 65535 字形)"""
    assert len(glyphs_list) <= 65534, len(glyphs_list)
    table = gen_glyph_table(len(glyphs_list), seed)
    glyph_order = [".notdef"]
    cmap, glyphs, metrics = {}, {}, {}
    pen = TTGlyphPen(None)
    pen.moveTo((100, 0)); pen.lineTo((100, 700))
    pen.lineTo((600, 700)); pen.lineTo((600, 0)); pen.closePath()
    glyphs[".notdef"] = pen.glyph()
    metrics[".notdef"] = (700, 100)
    for i, ch in enumerate(glyphs_list):
        name = f"g{ord(ch):05X}"
        gp = TTGlyphPen(None)
        for contour in table[i]:
            gp.moveTo(contour[0])
            for p in contour[1:]:
                gp.lineTo(p)
            gp.closePath()
        glyphs[name] = gp.glyph()
        metrics[name] = (1000, 100)
        cmap[ord(ch)] = name
        glyph_order.append(name)

    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=900, descent=-100)
    fb.setupNameTable({
        "familyName": font_name, "styleName": "Regular",
        "uniqueFontIdentifier": font_name + " Regular",
        "fullName": font_name, "psName": font_name.replace(" ", "") + "-Regular",
        "version": "Version 1.0",
    })
    fb.setupOS2(sTypoAscender=900, sTypoDescender=-100,
                usWinAscent=900, usWinDescent=100,
                sxHeight=500, sCapHeight=700)
    fb.setupPost()
    fb.font["post"].formatType = 3.0   # 不存字形名 (超 65535 时 format 2.0 会溢出)
    fb.save(out_path)
    return len(cmap)


def build_fonts_split(out_dir, seed=99):
    """整个私用区拆成多个字体 (TTF 单文件上限 65535 字形)"""
    chunks = [
        ("AICryptLangBMP", [(0xE000, 0xF8FF)]),
        ("AICryptLangP15", [(0xF0000, 0xFFFFD)]),
        ("AICryptLangP16", [(0x100000, 0x10FFFD)]),
    ]
    made = []
    for i, (name, ranges) in enumerate(chunks):
        chars = [chr(cp) for a, b in ranges for cp in range(a, b + 1)
                 if (cp & 0xFFFE) != 0xFFFE]
        path = os.path.join(out_dir, name + ".ttf")
        print(f"   [{name}] 造字 {len(chars):,} 个 -> {os.path.basename(path)}")
        cnt = _build_one(chars, path, name, seed + i)
        size = os.path.getsize(path) / 1024.0
        print(f"       完成 cmap={cnt:,} 文件 {size:.0f} KB")
        made.append((path, cnt))
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    ap.add_argument("--n", type=int, default=30000, help="造字数量上限")
    ap.add_argument("--seed", type=int, default=99)
    ap.add_argument("--full-pua", action="store_true",
                    help="覆盖整个私用区(约 13.7 万码位), 不依赖 symbols.json")
    args = ap.parse_args()

    with open(os.path.join(args.out, "symbols.json"), encoding="utf-8") as f:
        data = json.load(f)
    symbols = data["symbols"][:args.n]

    if args.full_pua:
        print("[造字] 覆盖整个私用区 (拆成多个字体) ...")
        made = build_fonts_split(args.out, args.seed)
        from fontTools.ttLib import TTFont as _TT
        for path, cnt in made:
            got = len(_TT(path).getBestCmap())
            print(f"       重载验证 {os.path.basename(path)}: cmap={got:,}")
        return

    ttf = os.path.join(args.out, "AICryptLang-Regular.ttf")
    print(f"[造字] {len(symbols)} 个 ...")
    path, cnt = build_font(symbols, ttf, seed=args.seed, full_pua=args.full_pua)

    # 自检: 重新加载并验证 cmap
    from fontTools.ttLib import TTFont
    f = TTFont(path)
    got = len(f.getBestCmap())
    size = os.path.getsize(path) / 1024.0
    print(f"[完成] {path}")
    print(f"       重载验证 cmap={got} 个码位, 文件 {size:.1f} KB")


if __name__ == "__main__":
    main()
