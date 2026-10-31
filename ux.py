#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一交互与视觉增强组件（被 build_site.py / xz_page.py 复用）

包含 8 项：
1) 粘性章节导航（scrollspy + 平滑跳转 + 移动端横向滑动）
2) 回到顶部按钮（滚过 400px 才出现）
3) 更新时间徽章（呼吸脉冲 + 相对时间）
4) 涨跌箭头 + 色块徽章（▲▼ / 浅红浅绿底）
5) 卡片微交互（hover 上浮 2px + 阴影加深）
6) 表格斑马纹 + 悬停高亮
7) 移动端与打印适配
8) theme-color（手机地址栏跟随主题绿）
"""

THEME_COLOR = "#3f6b4f"

import os  # noqa: E402  (供 write_injected 使用)

UX_CSS = """
/* ===== 1. 粘性章节导航 ===== */
.snav{position:sticky;top:0;z-index:70;display:flex;gap:6px;overflow-x:auto;
  margin:0 0 16px;padding:9px 2px;background:rgba(238,243,232,.92);
  -webkit-backdrop-filter:saturate(180%) blur(10px);backdrop-filter:saturate(180%) blur(10px);
  border-bottom:1px solid var(--line);scrollbar-width:none;-webkit-overflow-scrolling:touch;
  scroll-snap-type:x proximity}
.snav::-webkit-scrollbar{display:none}
.snav a{flex:0 0 auto;scroll-snap-align:center;white-space:nowrap;text-decoration:none;
  padding:6px 13px;border-radius:999px;font-size:13.5px;font-weight:700;color:#3a5440;
  border:1px solid transparent;transition:background .18s,border-color .18s,color .18s,box-shadow .18s}
.snav a:hover{background:#e6efdd;border-color:#cfe0bf}
.snav a.on{background:linear-gradient(135deg,#54895f,#3f6b4f);color:#fff;border-color:#3f6b4f;
  box-shadow:0 4px 12px -7px rgba(63,107,79,.9)}
.snav.scrolled{box-shadow:0 6px 16px -14px rgba(40,70,40,.75);border-bottom-color:#cfdcc4}

/* ===== 2. 回到顶部 ===== */
#toTop{position:fixed;right:20px;bottom:24px;z-index:90;width:46px;height:46px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;cursor:pointer;padding:0;
  border:1px solid #cfe0bf;background:rgba(255,255,255,.95);color:var(--acc);
  font-size:19px;font-weight:700;line-height:1;
  box-shadow:0 8px 22px -10px rgba(40,70,40,.55),0 1px 3px rgba(40,70,40,.10);
  opacity:0;visibility:hidden;transform:translateY(10px);
  transition:opacity .22s ease,transform .22s ease,visibility .22s,background .18s}
#toTop.on{opacity:1;visibility:visible;transform:translateY(0)}
#toTop:hover{background:#f2f8ea;border-color:#a9c797;transform:translateY(-2px)}
#toTop:active{transform:translateY(0)}

/* ===== 3. 更新时间徽章（呼吸脉冲 + 相对时间） ===== */
.updated .live{display:inline-flex;align-items:center;gap:6px;color:#4e8259;font-size:12px;
  font-weight:700;margin-left:8px;padding:2px 10px 2px 8px;border-radius:999px;
  background:rgba(78,130,89,.09);border:1px solid rgba(78,130,89,.16)}
.updated .live::before{content:"";width:7px;height:7px;border-radius:50%;background:#4e8259;
  box-shadow:0 0 0 0 rgba(78,130,89,.6);animation:uxpulse 1.9s ease-out infinite}
@keyframes uxpulse{
  0%{box-shadow:0 0 0 0 rgba(78,130,89,.55);opacity:1}
  70%{box-shadow:0 0 0 7px rgba(78,130,89,0);opacity:.72}
  100%{box-shadow:0 0 0 0 rgba(78,130,89,0);opacity:1}
}
.updated .rel{display:inline-flex;align-items:center;gap:4px;margin-left:7px;font-size:12px;
  font-weight:700;color:#43594a;background:#eef4e7;border:1px solid #dfe8d4;
  border-radius:999px;padding:2px 10px;font-variant-numeric:tabular-nums}
.updated .rel::before{content:"\\27F3";font-size:11px;opacity:.65;font-weight:400}

/* ===== 4. 涨跌箭头 + 色块徽章 ===== */
.pill{display:inline-flex;align-items:center;justify-content:flex-end;gap:3px;
  padding:2px 9px;border-radius:999px;font-weight:800;font-variant-numeric:tabular-nums;
  font-size:14px;line-height:1.5;white-space:nowrap}
.pill .ar{font-size:11px;line-height:1}
.pill.up{color:var(--up);background:rgba(192,57,43,.09);border:1px solid rgba(192,57,43,.20)}
.pill.down{color:var(--down);background:rgba(30,132,73,.09);border:1px solid rgba(30,132,73,.20)}
.pill.flat{color:#5a6b56;background:#f0f3ec;border:1px solid #e0e7d8}
.ipct.pill{font-size:15px;padding:3px 11px}

/* ===== 5. 卡片微交互 ===== */
.icard,.scard,.chart,.tbl,.card,.item{transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease}
.icard:hover,.scard:hover,.chart:hover,.tbl:hover{
  transform:translateY(-2px);
  box-shadow:0 12px 26px -16px rgba(40,70,40,.55),0 2px 6px rgba(40,70,40,.08);
  border-color:#bcd3b0}
.card:hover{transform:translateY(-2px);box-shadow:0 12px 26px -16px rgba(40,70,40,.5);border-color:#b6cfa6}
.item:hover{background:#fbfdf8}
.histrow:hover{background:#f2f8ea}

/* ===== 6. 表格斑马纹 + 悬停高亮 ===== */
table tbody tr:nth-child(even){background:#f6faf0}
table tbody tr:hover{background:#ebf4e0}
table tbody tr:nth-child(even):hover{background:#e9f3de}
table.arttbl tbody tr.art-p{background:#fbfdf8}
table.arttbl tbody tr.art-p:hover{background:#f2f8ea}
table.itbl tbody tr:nth-child(even){background:#f4f9ed}
table.itbl tbody tr:hover{background:#eaf3f2}

/* ===== 7-a. 移动端 ===== */
@media(max-width:560px){
  .snav{margin:0 0 12px;padding:8px 26px 8px 2px;gap:5px;
    -webkit-mask-image:linear-gradient(90deg,#000 0,#000 calc(100% - 22px),transparent 100%);
    mask-image:linear-gradient(90deg,#000 0,#000 calc(100% - 22px),transparent 100%)}
  .snav a{font-size:12.5px;padding:5px 11px}
  #toTop{width:44px;height:44px;right:12px;bottom:16px;font-size:18px;
    background:linear-gradient(135deg,rgba(84,137,95,.96),rgba(63,107,79,.96));color:#fff;border-color:#3f6b4f;
    box-shadow:0 10px 22px -8px rgba(63,107,79,.8),0 1px 3px rgba(40,70,40,.25)}
  .updated{display:flex;flex-wrap:wrap;align-items:center;gap:5px}
  .updated .live{margin-left:0;font-size:11.5px;padding:2px 8px}
  .updated .rel{font-size:11.5px;padding:2px 8px;margin-left:2px}
  .pill{font-size:13px;padding:2px 7px}
  .icard:hover,.scard:hover,.chart:hover,.tbl:hover,.card:hover{transform:none}
}

/* ===== 7-b. 打印 ===== */
@media print{
  .snav,#toTop,.toolnav,.nav,.nav-btns,.hist-cta,.cover,.acts,.tip{display:none!important}
  body{background:#fff!important;padding:0!important;color:#000}
  .wrap{max-width:100%!important;border:none!important;box-shadow:none!important;padding:0!important}
  .icard,.scard,.chart,.tbl,.card{box-shadow:none!important;border:1px solid #ccc!important;
    break-inside:avoid;page-break-inside:avoid;transform:none!important}
  header{break-after:avoid}
  h2,h3{break-after:avoid}
  a{color:#000!important;text-decoration:none!important}
  table{font-size:11pt}
  table tbody tr{background:#fff!important}
}
"""

UX_JS = r"""
/* ===== 统一交互：粘性导航 scrollspy / 回顶 / 相对时间 ===== */
(function(){
  var toTop=document.getElementById('toTop');
  var snav=document.getElementById('snav');
  var links=snav?[].slice.call(snav.querySelectorAll('a')):[];
  var targets=links.map(function(a){return document.getElementById(a.getAttribute('data-t'));});

  function onScroll(){
    var y=window.pageYOffset||document.documentElement.scrollTop||0;
    if(toTop){
      if(y>400)toTop.classList.add('on');else toTop.classList.remove('on');
    }
    if(snav)snav.classList[y>8?'add':'remove']('scrolled');
    if(links.length){
      var idx=-1;
      for(var i=0;i<targets.length;i++){
        var t=targets[i];if(!t)continue;
        var top=t.getBoundingClientRect().top+y;
        if(top-130<=y)idx=i;
      }
      if(idx<0)idx=0;
      links.forEach(function(a,j){a.classList.toggle('on',j===idx);});
      var cur=links[idx];
      if(cur&&snav.scrollWidth>snav.clientWidth+4){
        var l=cur.offsetLeft-(snav.clientWidth-cur.offsetWidth)/2;
        if(Math.abs(snav.scrollLeft-l)>4)snav.scrollTo({left:Math.max(0,l),behavior:'smooth'});
      }
    }
  }
  var raf=false;
  window.addEventListener('scroll',function(){
    if(raf)return;raf=true;
    requestAnimationFrame(function(){raf=false;onScroll();});
  },{passive:true});
  window.addEventListener('resize',onScroll);
  onScroll();

  if(toTop){
    toTop.addEventListener('click',function(){
      try{window.scrollTo({top:0,behavior:'smooth'});}
      catch(e){window.scrollTo(0,0);}
    });
  }

  if(links.length){
    links.forEach(function(a){
      a.addEventListener('click',function(e){
        var t=document.getElementById(a.getAttribute('data-t'));
        if(!t)return;e.preventDefault();
        var y=(window.pageYOffset||0)+t.getBoundingClientRect().top-64;
        try{window.scrollTo({top:y,behavior:'smooth'});}
        catch(err){window.scrollTo(0,y);}
        if(history.replaceState)history.replaceState(null,'','#'+a.getAttribute('data-t'));
      });
    });
  }

  /* 相对时间：解析「YYYY-MM-DD HH:MM 北京时间」，任意时区浏览器均可算 */
  function parseBJ(s){
    var m=/(\d{4})-(\d{1,2})-(\d{1,2})\D+(\d{1,2}):(\d{2})/.exec(s||'');
    if(!m)return null;
    return Date.UTC(+m[1],+m[2]-1,+m[3],+m[4]-8,+m[5]);
  }
  function relText(t){
    if(!t)return '';
    var d=Date.now()-t;if(d<0)d=0;
    var mi=Math.floor(d/60000);
    if(mi<1)return '刚刚';
    if(mi<60)return mi+' 分钟前';
    var h=Math.floor(mi/60);
    if(h<24)return h+' 小时前';
    var dd=Math.floor(h/24);
    if(dd<30)return dd+' 天前';
    return Math.floor(dd/30)+' 个月前';
  }
  function refreshRel(){
    [].forEach.call(document.querySelectorAll('[data-bjtime]'),function(el){
      var t=parseBJ(el.getAttribute('data-bjtime'));
      el.textContent=relText(t)||'时间未知';
    });
  }
  window.__uxRefreshRel=refreshRel;
  refreshRel();
  setInterval(refreshRel,30000);
})();
"""

TO_TOP_HTML = '<button id="toTop" type="button" aria-label="回到顶部" title="回到顶部">↑</button>'


def sticky_nav(sections):
    """sections: [(anchor_id, label), ...]"""
    parts = []
    for i, (aid, label) in enumerate(sections):
        on = ' class="on"' if i == 0 else ""
        parts.append(f'<a href="#{aid}" data-t="{aid}"{on}>{label}</a>')
    return f'<nav class="snav" id="snav" aria-label="章节导航">{"".join(parts)}</nav>'


def theme_meta(color=THEME_COLOR):
    return f'<meta name="theme-color" content="{color}">'


def updated_badge(updated_text):
    """更新时间徽章：文本 + 呼吸脉冲 + 相对时间（data-bjtime 供 JS 计算）"""
    return (f'数据更新：<b>{updated_text}</b>'
            f'<span class="live">自动刷新中</span>'
            f'<span class="rel" data-bjtime="{updated_text}">刚刚</span>')


def pct_chip(pct, extra_cls="", arrow=True):
    """涨跌色块徽章 HTML（红涨绿跌）"""
    p = float(pct or 0)
    cls = "up" if p > 0 else ("down" if p < 0 else "flat")
    ar = ("▲" if p > 0 else ("▼" if p < 0 else "—")) if arrow else ""
    sign = "+" if p > 0 else ""
    arh = f'<span class="ar">{ar}</span>' if ar else ""
    return f'<span class="pill {cls} {extra_cls}">{arh}{sign}{p:.2f}%</span>'


def inject_head(html, css_extra="", color=THEME_COLOR):
    """给已有 HTML 注入 theme-color（若缺）并追加 CSS"""
    if 'name="theme-color"' not in html:
        html = html.replace('<meta charset="utf-8">',
                            f'<meta charset="utf-8">\n{theme_meta(color)}', 1)
        if 'name="theme-color"' not in html:
            html = html.replace('<meta charset="UTF-8">',
                                f'<meta charset="UTF-8">\n{theme_meta(color)}', 1)
    if css_extra:
        if "</head>" in html:
            html = html.replace("</head>", f"<style>{css_extra}</style>\n</head>", 1)
    return html


QUIZ_CSS = """
/* 刷题类页面的轻量增强：回顶按钮 / 卡片微交互 / 打印 */
#toTop{position:fixed;right:18px;bottom:78px;z-index:200;width:44px;height:44px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;cursor:pointer;padding:0;
  border:1px solid rgba(0,0,0,.07);background:rgba(255,255,255,.96);color:#0f766e;
  font-size:18px;font-weight:700;line-height:1;
  box-shadow:0 8px 22px -10px rgba(15,118,110,.55),0 1px 3px rgba(0,0,0,.10);
  opacity:0;visibility:hidden;transform:translateY(10px);
  transition:opacity .22s ease,transform .22s ease,visibility .22s;
  -webkit-tap-highlight-color:transparent}
#toTop.on{opacity:1;visibility:visible;transform:translateY(0)}
#toTop:active{transform:scale(.94)}
/* 卡片微交互 + 表格斑马纹（仅桌面悬停设备生效，避免移动端误触发） */
tbody tr:nth-child(even),.list>li:nth-child(even){background:rgba(15,118,110,.03)}
@media(hover:hover){
  .card,.opt,.qcard,.stat-card{transition:box-shadow .18s ease,transform .18s ease,border-color .18s ease}
  .card:hover,.qcard:hover{box-shadow:0 10px 22px -14px rgba(15,118,110,.45);border-color:rgba(15,118,110,.28)}
  tbody tr:hover,.list>li:hover{background:rgba(15,118,110,.07)}
}
@media(max-width:560px){#toTop{width:40px;height:40px;right:12px;bottom:72px;font-size:16px}}
@media print{#toTop{display:none!important}}
"""


def inject_quiz(html, color="#0f766e"):
    """刷题页：补 theme-color + 回顶按钮 + 轻量 UX 样式"""
    if 'name="theme-color"' not in html:
        html = inject_head(html, "", color)
    html = inject_head(html, QUIZ_CSS, color)
    if 'id="toTop"' not in html and "</body>" in html:
        html = html.replace("</body>", TO_TOP_HTML + "\n<script>(function(){var b=document.getElementById('toTop');if(!b)return;var f=function(){var y=window.pageYOffset||document.documentElement.scrollTop||0;b.classList[y>400?'add':'remove']('on');};window.addEventListener('scroll',f,{passive:true});f();b.addEventListener('click',function(){try{window.scrollTo({top:0,behavior:'smooth'});}catch(e){window.scrollTo(0,0);}});})();</script>\n</body>", 1)
    return html


def write_injected(src, dst, mode="page", color=THEME_COLOR):
    """读 src（HTML）→ 注入 UX → 写 dst"""
    with open(src, encoding="utf-8", errors="replace") as f:
        h = f.read()
    h = inject_quiz(h, color) if mode == "quiz" else inject_ux(h)
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(h)
    return dst


def inject_ux(html, with_top=True, with_js=True, css=True):
    """给任意页面追加 UX 样式/回顶按钮/交互脚本"""
    if css and "uxpulse" not in html:
        html = inject_head(html, UX_CSS)
    if with_top and 'id="toTop"' not in html and "</body>" in html:
        html = html.replace("</body>", TO_TOP_HTML + "\n</body>", 1)
    if with_js and "__uxRefreshRel" not in html and "</body>" in html:
        html = html.replace("</body>", f"<script>{UX_JS}</script>\n</body>", 1)
    return html
