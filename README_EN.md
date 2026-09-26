# AICryptLang — A Symbol System That Only Humans Find Hard

> **Soft "encryption" for AI-to-AI communication.**
> A pool of millions of symbols whose meaning is assigned *per context*.
> Humans can't read it; AI doesn't care.

*(中文说明见 [README.md](README.md) — 中文为主文档，本文为英文速览。)*

---

## What it is

A symbol-based communication/encoding layer designed around one asymmetry:

| | Humans | AI |
|---|---|---|
| Working memory for symbols | 4–7 chunks | whole context window |
| Memorizing a 1M-entry codebook | impossible | trivial |
| Recovering meaning from context | slow & unreliable | core strength |

So we push exactly on the two human weak spots: **memory capacity** and **context bandwidth**.

Three ideas:

1. **Don't invent symbols — sample them.** Unicode already ships 155k+ assigned code points and 137k private-use code points. On top of that, *composite sequences* (1 base + M combining marks) push the theoretical space into the **billions**.
2. **Meaning is per-context.** A codebook is deterministically derived from a natural-language *context key* (e.g. `"chat about games tonight"`). Change the key → the whole codebook is void.
3. **Rotate key = rotate everything.** Ciphertexts from round 1 tell you nothing about round 2.

## Three layers

```
Layer 3  Glyph layer    what human eyes see   (procedural fonts, 137,468 PUA glyphs)
Layer 2  Composite layer how the pool gets huge (1 base + M marks, fixed length)
Layer 1  Code-point layer what AI actually reads (PUA / CJK Ext / historic / symbols)
```

## Measured

| Metric | Value |
|---|---|
| Composite symbol pool | **1,000,000** |
| Theoretical space | **4,392,403,200** |
| Procedural glyphs | **137,468** (split into 3 TTF files) |
| Round-trip encode/decode | **12/12 lossless** |
| Unit length | 3 symbols/char → 9 code points per CJK char |

## ⚠️ It is NOT cryptography

This is an **encoding / obfuscation / steganography layer**, not an encryption layer.
It targets *humans*, not machines. For real confidentiality: `AICryptLang(AES-GCM(plaintext))`.

## Quick start

```powershell
pip install fonttools pillow

python src/gen_symbols.py --n 1000000 --composite-ratio 1.0 --composite-marks 2
python src/gen_font.py --full-pua
python src/codec.py selftest
python src/codec.py encode --key "context key" --text "your message"
```

Install the generated fonts (`out/AICryptLangBMP.ttf`, `...P15.ttf`, `...P16.ttf`) to see the glyphs.

## License

MIT
