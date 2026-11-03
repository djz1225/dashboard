# -*- coding: utf-8 -*-
"""生成生理学速记卡独立页面 physio.html

单文件、零外部依赖。功能：
  · 按章筛选（13 章）
  · 每张卡：口诀 → 机制图（点击全屏）→ 表格/要点
  · 搜索
  · 学习进度（localStorage）
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from physio_cards import CARDS, CHAPTERS


TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>生理学速记卡 · 第10版</title>
<style>
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{margin:0;background:#f6f8fa;color:#17222b;
  font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;
  font-size:15px;line-height:1.6}
header{background:linear-gradient(135deg,#0f766e,#0d9488);color:#fff;padding:16px 16px 12px;
  position:sticky;top:0;z-index:50;box-shadow:0 2px 12px -4px rgba(15,118,110,.5)}
header h1{margin:0;font-size:18px;font-weight:700}
header .sub{font-size:12.5px;opacity:.9;margin-top:3px}
.wrap{max-width:760px;margin:0 auto;padding:12px}
.toolbar{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.search{flex:1;min-width:140px;padding:9px 12px;border:1px solid #cbd5e1;border-radius:9px;
  font-size:14px;background:#fff;font-family:inherit}
.chips{display:flex;flex-wrap:wrap;gap:6px;padding-bottom:6px}
.chip{padding:6px 11px;border-radius:18px;background:#fff;
  border:1px solid #cbd5e1;font-size:12.5px;color:#475569;cursor:pointer;white-space:nowrap}
.chip.on{background:#0f766e;border-color:#0f766e;color:#fff;font-weight:700}
.stat{font-size:12.5px;color:#4E5B64;margin:4px 0 10px}
.card{background:#fff;border-radius:12px;padding:14px;margin-bottom:14px;
  box-shadow:0 1px 3px rgba(15,23,42,.06);border:1px solid #e8eef4}
.card h2{margin:0 0 10px;font-size:16px;color:#0f766e;display:flex;align-items:center;gap:8px}
.card h2 .lv{font-size:11.5px;background:#ccfbf1;color:#0f766e;padding:2px 7px;
  border-radius:9px;font-weight:700}
.q{background:#f0fdfa;border-left:4px solid #0f766e;padding:10px 12px;
  border-radius:0 8px 8px 0;font-size:14px;line-height:1.65;margin:8px 0 12px}
.fig{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:8px 4px 4px;
  cursor:zoom-in;overflow-x:auto;-webkit-overflow-scrolling:touch;margin:10px 0}
.fig svg{display:block;height:auto;max-width:100%;margin:0 auto}
.fig-cap{text-align:center;font-size:13px;color:#8a5b3b;margin-top:6px;padding:0 6px}
.fig-tip{text-align:center;font-size:12px;color:#94a3b8;margin:2px 0 4px}
th,td{word-break:normal;overflow-wrap:break-word}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:10px 0}
table{width:100%;border-collapse:collapse;font-size:13.5px;min-width:280px}
th{background:#0f766e;color:#fff;padding:7px 8px;text-align:left;font-weight:600}
td{border-bottom:1px solid #eef2f6;padding:7px 8px;vertical-align:top}
tr:nth-child(even) td{background:#fbfdfe}
ul{margin:8px 0;padding-left:20px}
li{margin:5px 0;font-size:14px;color:#334155}
.zoom{position:fixed;inset:0;background:rgba(15,23,42,.93);z-index:999;
  display:none;align-items:center;justify-content:center;padding:12px;overflow:auto}
.zoom.on{display:flex}
.zoom .in{background:#fff;border-radius:12px;padding:12px;max-width:420px;width:100%}
.zoom .in svg{display:block;width:100%;height:auto}
.zoom .tip{text-align:center;font-size:13px;color:#64748b;margin-top:8px}
footer{text-align:center;font-size:12.5px;color:#4E5B64;padding:20px}
@supports (padding: max(0px)){
  header{padding-top:max(16px, env(safe-area-inset-top))}
}
</style>
</head>
<body>
<header>
  <h1>生理学速记卡</h1>
  <div class="sub">人卫第10版 · 13 章 · 机制推演 + 一句话结论</div>
</header>
<div class="wrap">
  <div class="toolbar">
    <input class="search" id="q" placeholder="搜索考点，如「阈电位」「ADH」">
  </div>
  <div class="chips" id="chips"></div>
  <div class="stat" id="stat"></div>
  <div id="list"></div>
</div>
<footer>内容依据《生理学》第10版（罗自强、管又飞主编，人卫社 2024）<br>
仅用于学习，不替代教材原文</footer>

<script>
const CHAPTERS = __CHAPTERS__;   // [[编号, 名称], ...] 有序数组
const CARDS = __CARDS__;
const FIGS = __FIGS__;

let curCh = 'all', kw = '';

function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;')
  .replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}

function renderChips(){
  const el = document.getElementById('chips');
  let h = `<div class="chip ${curCh==='all'?'on':''}" data-ch="all">全部 ${CARDS.length}</div>`;
  for (const [k, name] of CHAPTERS) {
    const n = CARDS.filter(c => c[0].slice(3,5) === k).length;
    h += `<div class="chip ${curCh===k?'on':''}" data-ch="${k}">${k} ${name}<b style="opacity:.65;margin-left:3px">${n}</b></div>`;
  }
  el.innerHTML = h;
  el.querySelectorAll('.chip').forEach(c => {
    c.onclick = () => { curCh = c.dataset.ch; renderChips(); renderList(); };
  });
}

function cardText(c){
  let t = c[1] + ' ';
  for (const b of c[3]) {
    if (b[0] === 'q' || b[0] === 'q2') t += b[1] + ' ';
    else if (b[0] === 'l') t += b[2].join(' ') + ' ';
    else if (b[0] === 't') t += b[1] + ' ' + b[3].flat().join(' ') + ' ';
    else if (b[0] === 'i') {
      t += (b[2]||'') + ' ';
      // 图里的文字也要能被搜到（去掉标签只留文本）
      const raw = (FIGS[b[1]]||'').replace(/<[^>]+>/g,' ');
      t += raw + ' ';
    }
  }
  return t;
}

function renderList(){
  const list = document.getElementById('list');
  let sel = CARDS.filter(c => curCh === 'all' || c[0].slice(3,5) === curCh);
  if (kw) {
    const k = kw.toLowerCase().replace(/\s+/g,'');
    sel = sel.filter(c => cardText(c).toLowerCase().replace(/\s+/g,'').includes(k));
  }
  document.getElementById('stat').textContent =
    `共 ${sel.length} 张卡` + (kw ? `（搜索「${kw}」）` : '');
  let html = '';
  for (const [id, title, lv, blocks] of sel) {
    const ch = id.slice(3,5);
    html += `<div class="card" id="card-${id}" data-fig="${(blocks.find(b=>b[0]==='i')||[])[1]||''}">
      <h2>${esc(title)}<span class="lv">第${Number(ch)}章</span></h2>`;
    for (const b of blocks) {
      if (b[0] === 'q') {
        html += `<div class="q">★ ${esc(b[1])}</div>`;
      } else if (b[0] === 'q2') {
        html += `<div class="q" style="background:#fffbeb;border-color:#b45309">`
             +  `💡 ${esc(b[1])}</div>`;
      } else if (b[0] === 'i') {
        const svg = FIGS[b[1]] || '';
        html += `<div class="fig" onclick="zoomFig('${b[1]}')">${svg}
          <div class="fig-cap">${esc(b[2]||'')}</div>
          <div class="fig-tip">🔍 点击全屏</div></div>`;
      } else if (b[0] === 't') {
        html += `<div class="tw"><table><tr>${b[2].map(h=>`<th>${esc(h)}</th>`).join('')}</tr>`;
        for (const r of b[3]) html += `<tr>${r.map(x=>`<td>${esc(x)}</td>`).join('')}</tr>`;
        html += `</table></div>`;
      } else if (b[0] === 'l') {
        html += `<ul>${b[2].map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`;
      }
    }
    html += `</div>`;
  }
  list.innerHTML = html || '<p style="color:#64748b;padding:20px;text-align:center">没有匹配的卡片</p>';
}

let zEl = null;
function zoomFig(id){
  const svg = FIGS[id];
  if (!svg) return;
  if (!zEl) {
    zEl = document.createElement('div');
    zEl.className = 'zoom';
    zEl.onclick = () => zEl.classList.remove('on');
    document.body.appendChild(zEl);
  }
  zEl.innerHTML = `<div class="in">${svg}<div class="tip">点击任意处关闭</div></div>`;
  zEl.classList.add('on');
}

document.getElementById('q').addEventListener('input', e => {
  kw = e.target.value.trim();
  renderList();
});

renderChips();
renderList();

/* 深链定位：physio.html#PH-04-01 → 切到该章并滚动高亮 */
(function(){
  function gotoHash(){
    var h = (location.hash || '').replace('#','').trim();
    if (!h) return;
    if (h.indexOf('fig_') === 0) {
      var cf = document.querySelector('[data-fig="' + h + '"]');
      if (cf) {
        var mm = /card-PH-(\d{2})-/.exec(cf.id);
        if (mm) { curCh = mm[1]; renderChips(); renderList(); }
        setTimeout(function(){
          var e2 = document.querySelector('[data-fig="' + h + '"]');
          if (e2) {
            e2.scrollIntoView({behavior:'smooth', block:'start'});
            e2.style.transition = 'box-shadow .4s';
            e2.style.boxShadow = '0 0 0 3px #0f766e';
            setTimeout(function(){ e2.style.boxShadow = ''; }, 2400);
          }
        }, 80);
        return;
      }
    }
    var m = /^PH-(\d{2})-/.exec(h) || /^card-PH-(\d{2})-/.exec(h);
    if (m) { curCh = m[1]; renderChips(); renderList(); }
    var el = document.getElementById('card-' + h.replace(/^card-/, ''))
          || document.getElementById(h);
    if (el) {
      el.scrollIntoView({behavior:'smooth', block:'start'});
      el.style.transition = 'box-shadow .4s';
      el.style.boxShadow = '0 0 0 3px #0f766e';
      setTimeout(function(){ el.style.boxShadow = ''; }, 2200);
    }
  }
  window.addEventListener('load', function(){ setTimeout(gotoHash, 60); });
  window.addEventListener('hashchange', gotoHash);
})();
</script>
</body>
</html>
"""


def build(out_path="/workspace/out/physio/physio.html"):
    figs = {}
    for c in CARDS:
        for b in c[3]:
            if b[0] == "i" and b[1] not in figs:
                p = os.path.join("/workspace/out/physio", b[1] + ".svg")
                if not os.path.exists(p):
                    raise SystemExit(f"缺图 {b[1]}")
                figs[b[1]] = open(p, encoding="utf-8").read()

    html = TEMPLATE
    # 关键：必须传有序数组。JS 会把「纯数字字符串键」按数值升序重排，
    # 导致 01 排到 10 之后（踩过）。用数组固定顺序。
    chapters_ordered = [[k, CHAPTERS[k]] for k in sorted(CHAPTERS)]
    html = html.replace("__CHAPTERS__",
                        json.dumps(chapters_ordered, ensure_ascii=False))
    html = html.replace("__CARDS__",
                        json.dumps(CARDS, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("__FIGS__",
                        json.dumps(figs, ensure_ascii=False, separators=(",", ":")))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        fp.write(html)
    return len(html), len(CARDS), len(figs)


if __name__ == "__main__":
    size, nc, nf = build()
    print(f"已生成 physio.html：{size} bytes | {nc} 张卡 | {nf} 张图")
