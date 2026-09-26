# -*- coding: utf-8 -*-
"""
AI 专用软加密语言 —— 符号池生成器 v2 (Symbol Pool Generator)
=============================================================
用法:
    python gen_symbols.py --n 100000
    python gen_symbols.py --n 1000000 --composite-ratio 1.0 --composite-marks 2

核心:
  * "随机"是采样, 不是胡编 —— 乱编会产生非法/代理区/非字符码位, 编辑器直接崩
  * 两种符号类型:
      单码位符号  : 1 个字符, 从 PUA/CJK/古文字/符号池取样
      组合序列符号: 1 基字 + 固定 M 个叠加符 -> 字符长度恒为 1+M
  * 长度统一是关键: 定长才能无分隔符切分, 编解码才不用分隔符
  * 组合序列空间 = |基字池| × |标记池|^M  ->  十亿级以上
"""
import argparse
import csv
import json
import os
import random
import sys
import unicodedata

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ----------------------------------------------------------------------
# 1. 单码位符号池
# ----------------------------------------------------------------------

def _is_usable(cp: int) -> bool:
    if 0xD800 <= cp <= 0xDFFF:
        return False
    if 0xFDD0 <= cp <= 0xFDEF:
        return False
    if (cp & 0xFFFE) == 0xFFFE:
        return False
    cat = unicodedata.category(chr(cp))
    if cat in ("Cc", "Cs", "Cf", "Zl", "Zp", "Cn"):
        return False
    return True


def pool_pua():
    for a, b in [(0xE000, 0xF8FF), (0xF0000, 0xFFFFD), (0x100000, 0x10FFFD)]:
        for cp in range(a, b + 1):
            yield cp, "PUA"


def pool_cjk_ext():
    ranges = [
        (0x20000, 0x2A6DF, "CJK-ExtB"), (0x2A700, 0x2B739, "CJK-ExtC"),
        (0x2B740, 0x2B81D, "CJK-ExtD"), (0x2B820, 0x2CEA1, "CJK-ExtE"),
        (0x2CEB0, 0x2EBE0, "CJK-ExtF"), (0x30000, 0x3134A, "CJK-ExtG"),
        (0x31350, 0x323AF, "CJK-ExtH"), (0x3400, 0x4DBF, "CJK-ExtA"),
    ]
    for a, b, tag in ranges:
        for cp in range(a, b + 1):
            yield cp, tag


def pool_historic():
    ranges = [
        (0x10000, 0x1007F, "LinearB"), (0x10900, 0x1091F, "Phoenician"),
        (0x12000, 0x123FF, "Cuneiform"), (0x13000, 0x1342F, "Hieroglyph"),
        (0x14400, 0x14646, "Anatolian"),
        (0x16800, 0x16A38, "Bamum"), (0x1B170, 0x1B2FB, "Nushu"),
        (0x10300, 0x1032F, "OldItalic"), (0x10330, 0x1034F, "Gothic"),
        (0x10500, 0x10527, "Elbasan"), (0x10800, 0x1083F, "Cypriot"),
        (0x11000, 0x1107F, "Brahmi"), (0x11100, 0x1114F, "Chakma"),
        (0x11400, 0x1147F, "NewTaiLue"),
        (0x1D000, 0x1D1FF, "Musical"), (0x1D300, 0x1D35F, "TaiXuanJing"),
        (0x4DC0, 0x4DFF, "Yijing"),
    ]
    for a, b, tag in ranges:
        for cp in range(a, b + 1):
            yield cp, tag


def pool_symbols():
    ranges = [
        (0x2190, 0x21FF, "Arrows"), (0x2200, 0x22FF, "MathOps"),
        (0x2300, 0x23FF, "Technical"), (0x25A0, 0x25FF, "Geometric"),
        (0x2600, 0x26FF, "MiscSymbols"), (0x2700, 0x27BF, "Dingbats"),
        (0x2980, 0x29FF, "MathOpsSup"), (0x2A00, 0x2AFF, "MathOpsSupB"),
        (0x1F300, 0x1F5FF, "MiscSymbolsPict"),
        (0x1F700, 0x1F77F, "Alchemical"),
        (0x1F780, 0x1F7FF, "GeometricExt"),
        (0x1F900, 0x1F9FF, "SupplementalPict"),
    ]
    for a, b, tag in ranges:
        for cp in range(a, b + 1):
            yield cp, tag


POOLS = {
    "pua": pool_pua,
    "cjk": pool_cjk_ext,
    "historic": pool_historic,
    "symbols": pool_symbols,
}

# ----------------------------------------------------------------------
# 2. 组合序列池
# ----------------------------------------------------------------------
MARKS_POOL = None

HOST_POOL = ([cp for cp in range(0x4E00, 0x9FA6)]      # CJK 基本区 20902
             + [cp for cp in range(0x3400, 0x4DBF)]    # CJK 扩展A 6592
             + [cp for cp in range(0xE000, 0xF8FF)])   # 私用区 6400


def build_marks_pool(mode="fonts"):
    """扫描全 Unicode 收集已分配组合标记 (Mn/Mc/Me)
    mode='fonts': 只保留本机字体能渲染的 (否则人类看到的叠加符会消失)
    mode='all'  : 全部标记
    """
    marks = [cp for cp in range(0x0300, 0x110000)
             if unicodedata.category(chr(cp)) in ("Mn", "Mc", "Me")
             and not (0xFE00 <= cp <= 0xFE0F)          # 变化选择符, 不可见
             and not (0xE0100 <= cp <= 0xE01EF)]       # 变化选择符扩展
    if mode != "fonts":
        return marks
    cm = set()
    try:
        from fontTools.ttLib import TTFont, TTCollection
    except ImportError:
        return marks
    for fn in ("msyh.ttc", "simsun.ttc", "simsunb.ttf", "mingliub.ttc",
               "NotoSansSC-VF.ttf", "SimsunExtG.ttf", "seguisym.ttf",
               "seguiemj.ttf", "arial.ttf", "times.ttf"):
        p = os.path.join(r"C:\Windows\Fonts", fn)
        if not os.path.exists(p):
            continue
        try:
            fonts = TTCollection(p).fonts if fn.endswith(".ttc") \
                else [TTFont(p, fontNumber=0)]
            for f in fonts:
                cm |= set(f.getBestCmap().keys())
        except Exception:
            continue
    covered = [cp for cp in marks if cp in cm]
    return covered if covered else marks


def gen_composite(rng, marks=2):
    """1 基字 + 固定 M 个叠加符 -> 字符长度恒为 1+M"""
    base = rng.choice(HOST_POOL)
    picked = rng.sample(MARKS_POOL, marks)
    return "".join(chr(c) for c in [base] + picked)


# ----------------------------------------------------------------------
# 3. 采样
# ----------------------------------------------------------------------
def build_catalog(seed=20260920, quotas=None):
    quotas = quotas or {"pua": 0.35, "cjk": 0.35, "historic": 0.20, "symbols": 0.10}
    catalog, stats = [], {}
    for name in quotas:
        cps = [(cp, tag) for cp, tag in POOLS[name]() if _is_usable(cp)]
        stats[name] = {"available": len(cps)}
        catalog.append((name, cps))
    return catalog, stats


def sample_symbols(n=50000, seed=20260920, quotas=None,
                   composite_ratio=0.0, composite_marks=2, marks_mode="fonts"):
    global MARKS_POOL
    rng = random.Random(seed)
    quotas = quotas or {"pua": 0.35, "cjk": 0.35, "historic": 0.20, "symbols": 0.10}
    pools, stats = build_catalog(seed, quotas)

    result, seen = [], set()
    n_comp = int(n * composite_ratio)
    n_main = n - n_comp

    for name, cps in pools:
        want = int(n_main * quotas[name])
        picked = rng.sample(cps, min(want, len(cps)))
        for cp, tag in picked:
            if cp in seen:
                continue
            seen.add(cp)
            ch = chr(cp)
            try:
                nm = unicodedata.name(ch)
            except ValueError:
                nm = "PRIVATE-USE"
            result.append({"cp": f"U+{cp:04X}", "char": ch, "name": nm, "pool": tag})

    while len(result) < n_main:                      # 补齐
        cp, tag = rng.choice(pools[0][1])
        if cp in seen:
            continue
        seen.add(cp)
        try:
            nm = unicodedata.name(chr(cp))
        except ValueError:
            nm = "PRIVATE-USE"
        result.append({"cp": f"U+{cp:04X}", "char": chr(cp), "name": nm, "pool": tag})

    if n_comp:
        if MARKS_POOL is None:
            print("       扫描全 Unicode 组合标记池 ...")
            MARKS_POOL = build_marks_pool(marks_mode)
            print(f"       组合标记可用 {len(MARKS_POOL)} 个")
        space = len(HOST_POOL) * (len(MARKS_POOL) ** composite_marks)
        print(f"       组合序列理论空间 {space:,} 个")
        made, sig, guard = 0, set(), 0
        while made < n_comp and guard < n_comp * 20:
            guard += 1
            s = gen_composite(rng, composite_marks)
            if s in sig:
                continue
            sig.add(s)
            result.append({
                "cp": "+".join(f"U+{ord(c):04X}" for c in s),
                "char": s, "name": f"COMPOSITE-{made}",
                "pool": f"composite{composite_marks}",
            })
            made += 1

    rng.shuffle(result)
    for i, item in enumerate(result):
        item["id"] = i + 1
    return result, stats


# ----------------------------------------------------------------------
# 4. 字体覆盖率检测
# ----------------------------------------------------------------------
def font_coverage(symbols):
    try:
        from fontTools.ttLib import TTFont, TTCollection
    except ImportError:
        return {"error": "fontTools 未安装"}
    fonts_dir = r"C:\Windows\Fonts"
    targets = ["simsunb.ttf", "SimsunExtG.ttf", "msyh.ttc",
               "simsun.ttc", "NotoSansSC-VF.ttf", "mingliub.ttc",
               "arial.ttf", "times.ttf", "seguisym.ttf", "seguiemj.ttf"]
    here = os.path.dirname(os.path.abspath(__file__))
    custom = [os.path.join(here, "out", n) for n in
              ("AICryptLangBMP.ttf", "AICryptLangP15.ttf", "AICryptLangP16.ttf")]
    report = {}
    union_cm = set()

    for fn in targets:
        path = os.path.join(fonts_dir, fn)
        if not os.path.exists(path):
            continue
        try:
            fonts = TTCollection(path).fonts if fn.endswith(".ttc") \
                else [TTFont(path, fontNumber=0)]
            cm = set()
            for f in fonts:
                cm |= set(f.getBestCmap().keys())
            union_cm |= cm
            sample = symbols[:5000]
            base_ok = sum(1 for s in sample if ord(s["char"][0]) in cm)
            mark_ok = sum(1 for s in sample
                          if all(ord(c) in cm for c in s["char"][1:]))
            full_ok = sum(1 for s in sample
                          if all(ord(c) in cm for c in s["char"]))
            report[fn] = {
                "glyphs_in_font": len(cm),
                "base_%": round(base_ok * 100.0 / len(sample), 2),
                "marks_%": round(mark_ok * 100.0 / len(sample), 2),
                "full_%": round(full_ok * 100.0 / len(sample), 2),
            }
        except Exception as e:
            report[fn] = {"error": str(e)}

    # 关键数字: 本机全部字体(含自造字体)的并集覆盖率
    for path in custom:
        if not os.path.exists(path):
            continue
        try:
            cm = set(TTFont(path, fontNumber=0).getBestCmap().keys())
            union_cm |= cm
            report[os.path.basename(path)] = {"glyphs_in_font": len(cm)}
        except Exception as e:
            report[os.path.basename(path)] = {"error": str(e)}

    sample = symbols[:5000]
    base_ok = sum(1 for s in sample if ord(s["char"][0]) in union_cm)
    full_ok = sum(1 for s in sample
                  if all(ord(c) in union_cm for c in s["char"]))
    report["__UNION_本机全部字体__"] = {
        "glyphs_union": len(union_cm),
        "base_%": round(base_ok * 100.0 / len(sample), 2),
        "full_%": round(full_ok * 100.0 / len(sample), 2),
    }
    return report


# ----------------------------------------------------------------------
# 5. 演示: 上下文密钥编码
# ----------------------------------------------------------------------
def demo_encode(symbols, seed=7, unit=2):
    rng = random.Random(seed)
    plain = "明天下午三点，老地方见。带伞。"
    codebook = {ch: "".join(rng.choice(symbols)["char"] for _ in range(unit))
                for ch in set(plain)}
    cipher = "".join(codebook[ch] for ch in plain)
    lines = ["# 上下文密钥软加密 · 演示", "",
             f"明文: {plain}", "", "本轮映射表 (仅本轮有效):"]
    for ch, sym in codebook.items():
        lines.append(f"  {ch} -> {sym}")
    lines += ["", f"密文: {cipher}", ""]
    return "\n".join(lines)


# ----------------------------------------------------------------------
# 6. main
# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50000)
    ap.add_argument("--seed", type=int, default=20260920)
    ap.add_argument("--composite-ratio", type=float, default=0.0)
    ap.add_argument("--composite-marks", type=int, default=2)
    ap.add_argument("--marks-mode", choices=["fonts", "all"], default="fonts",
                    help="叠加符池: fonts=只取本机字体能渲染的(推荐)")
    ap.add_argument("--compact", action="store_true",
                    help="大池子用: 只写字符数组, 不写详细元数据")
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "out"))
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    print(f"[1/5] 采样 {args.n} 个符号 (seed={args.seed}, "
          f"composite={args.composite_ratio}, marks={args.composite_marks}) ...")
    symbols, stats = sample_symbols(
        args.n, args.seed, composite_ratio=args.composite_ratio,
        composite_marks=args.composite_marks, marks_mode=args.marks_mode)
    print(f"       实际产出 {len(symbols)} 个")

    # 长度分布自检: 组合序列模式下必须长度统一
    from collections import Counter
    lens = Counter(len(s["char"]) for s in symbols)
    print(f"       字符长度分布: {dict(lens)}")
    if args.composite_ratio >= 1.0 and len(lens) != 1:
        print("       ⚠ 长度不统一, 定长切分会失败")

    compact = args.compact or args.n > 60000
    print(f"[2/5] 写文件 (compact={compact}) ...")
    if compact:
        with open(os.path.join(args.out, "symbols.json"), "w", encoding="utf-8") as f:
            json.dump({"count": len(symbols), "seed": args.seed,
                       "pool_stats": stats, "format": "chars",
                       "symbols": [s["char"] for s in symbols]}, f,
                      ensure_ascii=False)
    else:
        with open(os.path.join(args.out, "symbols.json"), "w", encoding="utf-8") as f:
            json.dump({"count": len(symbols), "seed": args.seed,
                       "pool_stats": stats, "format": "detailed",
                       "symbols": symbols}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.out, "symbols.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(s["char"] for s in symbols))
    if not compact:
        with open(os.path.join(args.out, "symbols_index.csv"), "w",
                  encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "codepoint", "char", "name", "pool"])
            for s in symbols:
                w.writerow([s["id"], s["cp"], s["char"], s["name"], s["pool"]])

    print("[3/5] 池子统计 ...")
    cnt = Counter(s["pool"] for s in symbols)
    for k, v in cnt.most_common(8):
        print(f"       {k:14s} {v:>8d}")
    if len(cnt) > 8:
        print(f"       ... 共 {len(cnt)} 个池子")

    print("[4/5] 生成上下文密钥演示 ...")
    with open(os.path.join(args.out, "sample_message.txt"), "w", encoding="utf-8") as f:
        f.write(demo_encode(symbols))

    print("[5/5] 字体覆盖率检测 (前 5000 个抽样) ...")
    cov = font_coverage(symbols)
    with open(os.path.join(args.out, "coverage.json"), "w", encoding="utf-8") as f:
        json.dump(cov, f, ensure_ascii=False, indent=1)
    for k, v in cov.items():
        print(f"       {k:20s} {v}")

    print(f"\n完成 -> {args.out}")


if __name__ == "__main__":
    main()
