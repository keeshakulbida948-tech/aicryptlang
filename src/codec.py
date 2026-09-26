# -*- coding: utf-8 -*-
"""
上下文密钥编解码器 v2 (Context-Keyed Codec)
===========================================
"意义由上下文赋予"的工程实现:
    编码 = 明文 --(上下文密钥 K)--> 符号串
    解码 = 符号串 --(同一把 K)--> 明文

特点:
  * 密钥 K 任意字符串(如"2026-09-20 晚 聊天 话题A"), 同句不同 K -> 完全不同的密文
  * 支持多码位组合符号 (基字+叠加符), 只要同一池子内字符长度统一 -> 定长无分隔切分
  * 人类解密: 必须枚举 K 或反推符号映射表 -> 计算量离谱
  * AI 解密: 密钥+密文一起给它, 秒解; 没密钥也能靠上下文猜个七八分

用法:
    python codec.py demo
    python codec.py selftest --pool out/symbols.json
    python codec.py encode --key "今晚聊游戏" --text "明天下午三点老地方见"
    python codec.py decode --key "今晚聊游戏" --text "<密文>"
"""
import argparse
import hashlib
import json
import os
import random
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
MAX_UNIT = 8          # 单元长度上限
DEFAULT_UNIT = 3      # 默认单元长度 (1 个明文汉字 -> 3 个符号)


# ----------------------------------------------------------------------
def load_symbols(path=None):
    """兼容两种格式: format=chars (字符数组) / format=detailed (带元数据)"""
    path = path or os.path.join(OUT, "symbols.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    syms = data["symbols"]
    if syms and isinstance(syms[0], dict):
        syms = [s["char"] for s in syms]
    # 定长统一: 只保留出现最多的那种字符长度
    from collections import Counter
    lens = Counter(len(s) for s in syms)
    keep, _ = lens.most_common(1)[0]
    return [s for s in syms if len(s) == keep], keep


def build_alphabet():
    chars = [chr(c) for c in range(0x20, 0x7F)]
    chars += list("，。：；！？、（）《》“”‘’—…· ")
    chars += [chr(c) for c in range(0x4E00, 0x9FA6)]
    return [c for c in chars if c not in "\r\n"]


def unit_len(symbols, alphabet, cap=DEFAULT_UNIT):
    """每个明文字符用几个符号表示 (池子越大越长, 编解码双方由此推导, 无需约定)"""
    return max(1, min(cap, MAX_UNIT, len(symbols) // len(alphabet)))


def derive_codebook(key, symbols, alphabet, cap=DEFAULT_UNIT):
    """确定性映射: 同 key + 同符号池 -> 同映射表"""
    seed = int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "big")
    rng = random.Random(seed)
    ul = unit_len(symbols, alphabet, cap)
    pool = rng.sample(symbols, len(alphabet) * ul)
    return {ch: "".join(pool[i * ul:(i + 1) * ul]) for i, ch in enumerate(alphabet)}


def encode(text, key, symbols, alphabet, sym_chars, cap=DEFAULT_UNIT):
    book = derive_codebook(key, symbols, alphabet, cap)
    unknown = sorted({c for c in text if c not in book})
    if unknown:
        raise ValueError(f"字符集外的字: {unknown[:20]}")
    return "".join(book[c] for c in text)


def decode(cipher, key, symbols, alphabet, sym_chars, cap=DEFAULT_UNIT):
    book = derive_codebook(key, symbols, alphabet, cap)
    inv = {v: k for k, v in book.items()}
    ul = unit_len(symbols, alphabet, cap)
    chunk = sym_chars * ul
    if len(cipher) % chunk != 0:
        raise ValueError(f"密文长度 {len(cipher)} 不是单元长度 {chunk} 的整数倍")
    return "".join(inv.get(cipher[i:i + chunk], "�")
                   for i in range(0, len(cipher), chunk))


# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["demo", "encode", "decode", "selftest"])
    ap.add_argument("--key", default="")
    ap.add_argument("--text", default="")
    ap.add_argument("--pool", default=None, help="符号池 JSON 路径")
    ap.add_argument("--unit", type=int, default=0, help="单元长度 (0=自动)")
    args = ap.parse_args()

    symbols, sym_chars = load_symbols(args.pool)
    alphabet = build_alphabet()
    cap = args.unit or DEFAULT_UNIT
    if len(symbols) < len(alphabet):
        print(f"❌ 符号池({len(symbols)}) 小于明文字符集({len(alphabet)}), "
              f"至少要 {len(alphabet)} 个符号才能一一映射。\n"
              f"   请加大 --n 或加大 --composite-ratio。")
        return
    ul = unit_len(symbols, alphabet, cap)

    print(f"[池子] {os.path.basename(args.pool or 'out/symbols.json')} | "
          f"可用符号 {len(symbols):,} 个 | 单符号字符长度 {sym_chars} | "
          f"明文字符集 {len(alphabet)} | 单元长度 {ul} 符号/字")
    print(f"[参数] 明文 1 字 -> {ul} 符号 -> {sym_chars * ul} 个字符\n")

    if args.action == "selftest":
        msgs = ["明天下午三点老地方见", "Hello, world! 测试123",
                "带伞，可能会下雨（记得）", "这是一条端到端往返测试"]
        ok = 0
        for m in msgs:
            for k in ["key-A", "key-B", "2026-09-20 晚 聊天"]:
                c = encode(m, k, symbols, alphabet, sym_chars, cap)
                assert decode(c, k, symbols, alphabet, sym_chars, cap) == m, (m, k)
                ok += 1
        print(f"✅ selftest 通过: {ok} 组往返全部无损")
        return

    if args.action == "demo":
        plain = "明天下午三点，老地方见。带伞。"
        print(f"明文: {plain}\n")
        for k in ["今晚聊游戏", "工作群 讨论排期", "小红书 版本B"]:
            c = encode(plain, k, symbols, alphabet, sym_chars, cap)
            back = decode(c, k, symbols, alphabet, sym_chars, cap)
            print(f"[上下文密钥] {k}")
            print(f"  密文: {c}")
            print(f"  回解: {back}   {'✅' if back == plain else '❌'}")
            print(f"  密文长度: {len(c)} 字符 / 明文 {len(plain)} 字\n")
        c = encode(plain, "今晚聊游戏", symbols, alphabet, sym_chars, cap)
        print(f"人类视角(前20符号): {c[:20 * sym_chars * ul]}...")
        return

    if not args.key or not args.text:
        print("需要 --key 和 --text")
        return
    if args.action == "encode":
        print(encode(args.text, args.key, symbols, alphabet, sym_chars, cap))
    else:
        print(decode(args.text, args.key, symbols, alphabet, sym_chars, cap))


if __name__ == "__main__":
    main()
