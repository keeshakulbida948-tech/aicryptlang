# -*- coding: utf-8 -*-
"""生成一个本地符号查看器 (HTML + 数据)，方便人类翻看符号池"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

with open(os.path.join(OUT, "symbols.json"), encoding="utf-8") as f:
    data = json.load(f)
syms = data["symbols"]
if syms and isinstance(syms[0], dict):
    syms = [s["char"] for s in syms]

N = 5000
view = syms[:N]
with open(os.path.join(OUT, "_view_data.js"), "w", encoding="utf-8") as f:
    f.write("window.SYM_DATA = ")
    json.dump({"total": data.get("count", len(syms)), "shown": len(view),
               "symbols": view}, f, ensure_ascii=False)
    f.write(";\n")

html = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>AICryptLang 符号查看器</title>
<style>
@font-face{font-family:ACL_BMP;src:url('AICryptLangBMP.ttf');}
@font-face{font-family:ACL_P15;src:url('AICryptLangP15.ttf');}
@font-face{font-family:ACL_P16;src:url('AICryptLangP16.ttf');}
body{margin:0;background:#fbfbf9;color:#1a1a1a;
     font-family:"Microsoft YaHei",sans-serif;}
header{padding:18px 24px;border-bottom:1px solid #e3e3dd;background:#fff;}
h1{margin:0 0 6px;font-size:20px;}
.sub{color:#8a8a8a;font-size:13px;}
.meta{margin-top:8px;font-size:13px;color:#444;}
.bar{padding:12px 24px;background:#fff;border-bottom:1px solid #e3e3dd;
     position:sticky;top:0;display:flex;gap:10px;align-items:center;flex-wrap:wrap;}
button{padding:6px 14px;border:1px solid #cfcfc7;background:#fff;border-radius:6px;
       cursor:pointer;font-size:13px;}
button:hover{background:#f2f2ee;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(84px,1fr));
      gap:8px;padding:20px 24px 60px;}
.cell{border:1px solid #e6e6e0;border-radius:8px;background:#fff;
      padding:8px 4px 6px;text-align:center;overflow:hidden;}
.cell .g{font-size:34px;line-height:1.25;
   font-family:ACL_BMP,ACL_P15,ACL_P16,"Microsoft YaHei",SimSun,serif;}
.cell .cp{font-size:10px;color:#9a9a9a;margin-top:4px;
   font-family:Consolas,monospace;word-break:break-all;}
.note{padding:0 24px 40px;font-size:13px;color:#a04040;line-height:1.9;}
code{background:#f1f1ec;padding:1px 5px;border-radius:4px;}
</style></head><body>
<header>
  <h1>AICryptLang 符号查看器</h1>
  <div class="sub">每个符号 = 1 基字 + 2 叠加符（3 个码位）。红框里的码位就是 AI 读到的东西。</div>
  <div class="meta" id="meta"></div>
</header>
<div class="bar">
  <button onclick="prev()">← 上一页</button>
  <button onclick="next()">下一页 →</button>
  <button onclick="shuffleView()">随机看一批</button>
  <span id="pageinfo" style="font-size:13px;color:#555"></span>
</div>
<div class="grid" id="grid"></div>
<div class="note">
  如果上面显示的是豆腐块 □ —— 说明字体没装。把
  <code>out\\AICryptLangBMP.ttf</code>、<code>AICryptLangP15.ttf</code>、
  <code>AICryptLangP16.ttf</code> 双击安装后重开本页即可。<br>
  注：私用区符号不在系统字体回退链里，所以三个字体要全装。
</div>
<script src="_view_data.js"></script>
<script>
const PAGE = 96;
let page = 0;
function cpsOf(s){return Array.from(s).map(c=>'U+'+c.codePointAt(0).toString(16).toUpperCase().padStart(4,'0')).join('+');}
function render(){
  const arr = window.SYM_DATA.symbols;
  const total = arr.length;
  const start = page*PAGE;
  const slice = arr.slice(start, start+PAGE);
  document.getElementById('grid').innerHTML = slice.map(s=>
    `<div class="cell"><div class="g">${s}</div><div class="cp">${cpsOf(s)}</div></div>`
  ).join('');
  document.getElementById('pageinfo').textContent =
    `第 ${page+1} / ${Math.ceil(total/PAGE)} 页（本页 ${slice.length} 个）`;
  document.getElementById('meta').textContent =
    `池子总符号 ${window.SYM_DATA.total.toLocaleString()} 个 ｜ 本页随机抽样自前 ${total} 个`;
}
function next(){const n=Math.ceil(window.SYM_DATA.symbols.length/PAGE);page=(page+1)%n;render();}
function prev(){const n=Math.ceil(window.SYM_DATA.symbols.length/PAGE);page=(page-1+n)%n;render();}
function shuffleView(){
  const a=window.SYM_DATA.symbols;
  for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}
  page=0;render();
}
render();
</script>
</body></html>
"""
with open(os.path.join(OUT, "符号查看器.html"), "w", encoding="utf-8") as f:
    f.write(html)
print("已生成:")
print(" ", os.path.join(OUT, "符号查看器.html"))
print(" ", os.path.join(OUT, "_view_data.js"))
