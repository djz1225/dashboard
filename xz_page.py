#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 xz/videos.json 渲染成「服务端直出」的静态页面（不依赖 JS 与额外网络请求）。

为什么这么做：手机上弱网（~2KB/s）时，靠 JS fetch JSON 再渲染会先看到空页/加载失败。
这里把卡片与筛选标签全部写进 HTML，JS 只负责筛选/排序（渐进增强），断网也能看。
"""
import json, os, re, html

sys_path_fix = os.path.dirname(os.path.abspath(__file__))
import sys as _sys
if sys_path_fix not in _sys.path:
    _sys.path.insert(0, sys_path_fix)
import ux  # 统一交互/视觉增强组件

CSS = """
:root{--bg:#eef3e8;--card:#fff;--ink:#20301f;--mut:#5a6b56;--line:#d3ddc7;--acc:#3f6b4f}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.65;padding:20px 12px 50px;margin:0;-webkit-text-size-adjust:100%}
.wrap{max-width:1080px;margin:0 auto}
header{background:linear-gradient(135deg,#4a7a58,#2f5540);color:#fff;border-radius:14px;padding:18px 18px}
header h1{margin:0 0 5px;font-size:20px;letter-spacing:.3px}
header .sub{font-size:13px;opacity:.92;line-height:1.6}
header .upd{margin-top:10px;font-size:12.5px;opacity:.95}
.toolbar{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px;margin:12px 0;display:flex;flex-direction:column;gap:9px}
.row{display:flex;flex-wrap:wrap;gap:7px;align-items:center}
#subRow{overflow-x:auto;flex-wrap:nowrap;-webkit-overflow-scrolling:touch;scrollbar-width:none;padding-bottom:2px}
#subRow::-webkit-scrollbar{display:none}
.chip{flex:0 0 auto;white-space:nowrap;border:1px solid var(--line);background:#f7faf3;color:#3d4f3a;border-radius:999px;padding:5px 12px;font-size:13px;cursor:pointer;user-select:none}
.chip:hover{border-color:#9dbf8d}
.chip.on{background:linear-gradient(135deg,#54895f,#3f6b4f);color:#fff;border-color:#3f6b4f;font-weight:600}
.chip .cnt{opacity:.72;font-size:11.5px;margin-left:3px}
input[type=search]{flex:1 1 200px;min-height:38px;border:1px solid var(--line);border-radius:9px;padding:0 11px;font-size:14px;background:#fbfdf8;color:var(--ink);outline:none}
input[type=search]:focus{border-color:#9dbf8d;background:#fff}
.sortsel{min-height:38px;border:1px solid var(--line);border-radius:9px;background:#fbfdf8;color:var(--ink);padding:0 8px;font-size:13.5px}
.stat{font-size:12.5px;color:var(--mut)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
.card:hover{border-color:#b6cfa6}
.cover{position:relative;display:block;height:150px;background:#dbe5d2;overflow:hidden}
.cover img{width:100%;height:100%;object-fit:cover;display:block}
.cover .dur{position:absolute;right:7px;bottom:7px;background:rgba(20,32,22,.84);color:#fff;font-size:11.5px;border-radius:5px;padding:1px 6px}
.cover .pg{position:absolute;left:7px;bottom:7px;background:rgba(63,107,79,.94);color:#fff;font-size:11.5px;border-radius:5px;padding:1px 6px}
.body{padding:10px 12px 12px;display:flex;flex-direction:column;gap:7px;flex:1}
.ttl{font-size:14.5px;font-weight:700;line-height:1.45;color:#1d3a28}
.meta{display:flex;flex-wrap:wrap;gap:5px;font-size:12px;color:var(--mut)}
.tag{background:#eef4e7;border:1px solid #e2ead8;border-radius:5px;padding:0 6px;color:#40603f}
.tag.sub{background:#e8f0f8;border-color:#d6e4f2;color:#2f5d8a;font-weight:600}
.tag.tc{background:#fdf1e3;border-color:#f4e0c7;color:#8a5a20}
.tag.pin{background:#c0392b;border-color:#a93226;color:#fff;font-weight:700}
.card.pinned{border-color:#e0b04a;box-shadow:0 0 0 2px rgba(224,176,74,.28)}
.parts{font-size:12px;color:#6b7d66;line-height:1.5}
.foot{margin-top:auto;display:flex;align-items:center;gap:8px;padding-top:3px}
.plays{font-size:12px;color:var(--mut)}
.go{margin-left:auto;display:inline-flex;align-items:center;min-height:36px;padding:0 13px;border-radius:9px;background:#eff6e9;border:1px solid #d9e6cb;color:#345b42;font-weight:700;font-size:13px;text-decoration:none}
.go:hover{background:#e6f1dc}
.mini{font-size:11.5px;color:#5a6b56;background:#f4f8ef;border:1px solid #e2ead8;border-radius:6px;padding:3px 7px;cursor:pointer;text-decoration:none}
.tip{background:#fff6e5;border:1px solid #f2d8a8;color:#7a5312;border-radius:9px;padding:9px 11px;font-size:12.5px;line-height:1.6;margin:10px 0;display:none}
.tip.show{display:block}
.empty{background:var(--card);border:1px dashed var(--line);border-radius:12px;padding:28px;text-align:center;color:var(--mut);font-size:14px}
footer{margin-top:22px;font-size:12px;color:var(--mut);line-height:1.75}
footer a{color:#3b6ea5;text-decoration:none}
@media(max-width:640px){
 body{padding:12px 9px 40px}
 .grid{grid-template-columns:1fr;gap:10px}
 .cover{height:165px}
}
"""

JS = """
(function(){
  var grid=document.getElementById('grid');
  var cards=[].slice.call(grid.querySelectorAll('.card'));
  var q=document.getElementById('q'), sel=document.getElementById('sort');
  var stat=document.getElementById('stat'), subRow=document.getElementById('subRow');
  var cur='全部', total=cards.length;
  function apply(){
    var kw=(q.value||'').trim().toLowerCase();
    var shown=0;
    cards.forEach(function(c){
      var ok=(cur==='全部'||c.getAttribute('data-s')===cur);
      if(ok&&kw){ ok=(c.getAttribute('data-t')||'').indexOf(kw)>=0; }
      c.style.display=ok?'':'none';
      if(ok)shown++;
    });
    var name=cur==='全部'?'':'（'+cur+'）';
    stat.textContent='共 '+shown+' 套课程'+name+(kw?'，关键词「'+q.value.trim()+'」':'');
    if(!shown){
      if(!grid.querySelector('.empty')){
        var d=document.createElement('div'); d.className='empty';
        d.textContent='没有匹配的课程，换个关键词试试'; grid.appendChild(d);
      }
    }else{
      var e=grid.querySelector('.empty'); if(e)e.remove();
    }
  }
  function sortBy(){
    var k=sel.value, arr=cards.slice();
    var idx={score:5,date:1,play:2,dur:3,pages:4}[k]||5;
    arr.sort(function(a,b){
      var x=a.getAttribute('data-k').split('|'), y=b.getAttribute('data-k').split('|');
      if(y[6]!==x[6])return y[6]==='1'?1:-1;   // 置顶始终在前
      return (parseFloat(y[idx])||0)-(parseFloat(x[idx])||0);
    });
    arr.forEach(function(c){grid.appendChild(c);});
  }
  subRow.addEventListener('click',function(e){
    var c=e.target.closest?e.target.closest('.chip'):null; if(!c)return;
    cur=c.getAttribute('data-s');
    [].forEach.call(subRow.querySelectorAll('.chip'),function(x){
      x.className='chip'+(x.getAttribute('data-s')===cur?' on':'');
    });
    q.value=''; apply();
  });
  q.addEventListener('input',function(){
    if(this.value.trim()&&cur!=='全部'){
      cur='全部';
      [].forEach.call(subRow.querySelectorAll('.chip'),function(x){
        x.className='chip'+(x.getAttribute('data-s')==='全部'?' on':'');
      });
    }
    apply();
  });
  sel.addEventListener('change',sortBy);
  if(/MicroMessenger/i.test(navigator.userAgent))document.getElementById('tip').className='tip show';
  document.addEventListener('click',function(e){
    var b=e.target.closest?e.target.closest('[data-cp]'):null; if(!b)return;
    var v=b.getAttribute('data-cp'), t=b.textContent;
    function done(){b.textContent='已复制 ✓';setTimeout(function(){b.textContent=t;},1400);}
    function fb(){var i=document.createElement('textarea');i.value=v;i.style.position='fixed';i.style.opacity='0';
      document.body.appendChild(i);i.select();try{document.execCommand('copy');done();}catch(x){prompt('长按复制',v);}document.body.removeChild(i);}
    if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(v).then(done).catch(fb);}else{fb();}
  });
  apply();
})();
"""


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def fmt_play(n):
    n = int(n or 0)
    return f"{n/10000:.1f}万" if n >= 10000 else str(n)


def card_html(it):
    tags = []
    if it.get("pinned"):
        tags.append('<span class="tag pin">置顶</span>')
    tags.append(f'<span class="tag sub">{esc(it["subject"])}</span>')
    for t in (it.get("teachers") or [])[:3]:
        tags.append(f'<span class="tag tc">{esc(t)}</span>')
    tags.append(f'<span class="tag">{esc(it.get("date",""))}</span>')
    cover = it.get("cover") or ""
    img = (f'<img loading="lazy" referrerpolicy="no-referrer" src="{esc(cover)}" alt="">'
           if cover else "")
    up = it.get("up") or ""
    # data-k = 科目|日期|播放|时长|分P|评分 ；data-t = 搜索用串（小写）
    k = "|".join([it["subject"], str(_ts(it.get("date", ""))), str(int(it.get("play") or 0)),
                  str(int(it.get("dur") or 0)), str(int(it.get("pages") or 0)),
                  str(it.get("score", 0)), "1" if it.get("pinned") else "0"])
    hay = (it.get("title", "") + " " + up + " " + " ".join(it.get("teachers") or [])).lower()
    bv = it.get("bvid") or os.path.basename(it.get("url") or "")
    play = f"play/{esc(bv)}.html" if bv else it.get("url")
    _pincls = " pinned" if it.get("pinned") else ""
    return (
        f'<article class="card{_pincls}" data-s="{esc(it["subject"])}" data-t="{esc(hay)}" data-k="{esc(k)}">'
        f'<a class="cover" href="{play}">{img}'
        f'<span class="pg">{int(it.get("pages") or 0)} P</span>'
        f'<span class="dur">{esc(it.get("dur_txt",""))}</span></a>'
        f'<div class="body"><div class="ttl">{esc(it.get("title"))}</div>'
        f'<div class="meta">{"".join(tags)}<span class="tag">UP：{esc(up)}</span></div>'
        f'<div class="foot"><span class="plays">▶ {fmt_play(it.get("play"))} 播放</span>'
        f'<a class="mini" href="{esc(it.get("url"))}" target="_blank" rel="noopener">B站原页</a>'
        f'<a class="go" href="{play}">站内播放 ▶</a>'
        f'</div></div></article>'
    )


def _ts(d):
    """YYYY-MM-DD -> 可比较整数"""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(d or ""))
    return int("".join(m.groups())) if m else 0


VIDEO_UX_EXTRA = """
/* 视频页：深色头部下的徽章配色 + 卡片斑马/悬停增强 */
header .upd .live{background:rgba(255,255,255,.16);border-color:rgba(255,255,255,.28);color:#eaf6e3}
header .upd .live::before{background:#c8f0a8;box-shadow:0 0 0 0 rgba(200,240,168,.7);animation:uxpulse 1.9s ease-out infinite}
header .upd .rel{background:rgba(255,255,255,.14);border-color:rgba(255,255,255,.24);color:#f2fbee}
.toolbar{position:sticky;top:0;z-index:60;box-shadow:0 6px 16px -14px rgba(40,70,40,.6)}
@media print{.toolbar{position:static!important;box-shadow:none!important}}
"""


def render(data, offline=False):
    UXCSS = ux.UX_CSS + VIDEO_UX_EXTRA
    items = data.get("items") or []
    subjects = data.get("subjects") or []
    cnt = {}
    for it in items:
        cnt[it["subject"]] = cnt.get(it["subject"], 0) + 1
    chips = [f'<span class="chip on" data-s="全部">全部<span class="cnt">{len(items)}</span></span>']
    for s in (subjects or list(cnt)):
        if cnt.get(s):
            chips.append(f'<span class="chip" data-s="{esc(s)}">{esc(s)}'
                         f'<span class="cnt">{cnt[s]}</span></span>')
    cards = "\n".join(card_html(it) for it in items)

    foot_links = ("离线单文件版 · 数据截至上方时间" if offline else
                  '<a href="quiz.html">西综 306 刷题</a> · <a href="../index.html">返回看板首页</a>'
                  ' · <a href="videos.json">JSON</a>')
    _html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
{ux.theme_meta()}
<title>考研西医综合（306）成套教学视频</title>
<style>{CSS}{UXCSS}</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>考研西医综合（306）成套教学视频</h1>
  <div class="sub">收录 B 站公开的多分 P / 长系列精讲课程，剔除散课与失效视频</div>
  <div class="upd">数据更新：<b>{esc(data.get("updated",""))}</b>（北京时间） · 共 {len(items)} 套 · 每天自动刷新
    <span class="live">自动刷新中</span><span class="rel" data-bjtime="{esc(data.get("updated",""))}">刚刚</span>
    {'' if offline else ' · <a href="videos_lite.html" style="color:#d6f5cf">网慢？用精简版 →</a>'}
  </div>
</header>

<div class="toolbar">
  <div class="row" id="subRow">{''.join(chips)}</div>
  <div class="row">
    <input type="search" id="q" placeholder="搜标题 / UP 主 / 老师，如 贺银成">
    <select class="sortsel" id="sort">
      <option value="score">按推荐度</option>
      <option value="new">最新发布</option>
      <option value="play">播放量</option>
      <option value="dur">总时长</option>
      <option value="pages">分P最多</option>
    </select>
  </div>
  <div class="row"><span class="stat" id="stat">共 {len(items)} 套课程</span></div>
</div>

<div class="tip" id="tip">微信里点「去学习」可能被拦：可点<b>复制BV</b>，再到哔哩哔哩 App 搜索框粘贴；或用右上角「…」→「在浏览器打开」。</div>
<div class="grid" id="grid">
{cards}
</div>

<footer>
收录口径：多分 P（≥10 集）或总时长 ≥4 小时的成套课程，逐条经视频详情校验（失效 / 私密自动剔除）。<br>
{foot_links}<br>
版权归各 UP 主与机构所有，本站仅做导航索引，不存储视频文件。
</footer>
</div>
<script>{JS}</script>
{ux.TO_TOP_HTML}
<script>{{UXJS}}</script>
</body>
</html>
"""
    return _html.replace("{UXJS}", ux.UX_JS)


LITE_CSS = """
:root{--bg:#eef3e8;--card:#fff;--ink:#20301f;--mut:#5a6b56;--line:#d3ddc7;--acc:#3f6b4f}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.6;padding:14px 10px 40px;margin:0;-webkit-text-size-adjust:100%}
.wrap{max-width:760px;margin:0 auto}
header{background:linear-gradient(135deg,#4a7a58,#2f5540);color:#fff;border-radius:12px;padding:14px 15px}
header h1{margin:0 0 4px;font-size:17px}
header .upd{margin-top:6px;font-size:12px;opacity:.95}
.chips{display:flex;gap:6px;overflow-x:auto;padding:10px 0 4px;scrollbar-width:none}
.chips::-webkit-scrollbar{display:none}
.chip{flex:0 0 auto;border:1px solid var(--line);background:#f7faf3;color:#3d4f3a;border-radius:99px;padding:5px 11px;font-size:12.5px;cursor:pointer}
.chip.on{background:#3f6b4f;color:#fff;border-color:#3f6b4f;font-weight:600}
.chip.pin{background:#fdecea;color:#a93226;border-color:#f1b8b2;font-weight:700}
.chip.pin.on{background:#c0392b;color:#fff;border-color:#c0392b}
input{width:100%;min-height:38px;border:1px solid var(--line);border-radius:9px;padding:0 10px;font-size:14px;background:#fbfdf8;margin:6px 0}
.item{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 11px;margin-bottom:8px}
.item .t{font-size:14px;font-weight:700;color:#1d3a28;line-height:1.45;display:block;text-decoration:none}
.item .m{font-size:12px;color:var(--mut);margin-top:5px;display:flex;flex-wrap:wrap;gap:6px}
.tag{background:#eef4e7;border:1px solid #e2ead8;border-radius:5px;padding:0 6px;color:#40603f}
.tag.s{background:#e8f0f8;border-color:#d6e4f2;color:#2f5d8a;font-weight:600}
.tag.pin{background:#c0392b;border-color:#a93226;color:#fff;font-weight:700}
.item.pinned{border-color:#e0b04a;box-shadow:0 0 0 2px rgba(224,176,74,.25)}
.stat{font-size:12px;color:var(--mut);margin:6px 0}
.tip{background:#fff6e5;border:1px solid #f2d8a8;color:#7a5312;border-radius:9px;padding:9px 11px;font-size:12.5px;line-height:1.65;margin:8px 0;display:none}
.tip.show{display:block}
.acts{display:flex;gap:6px;margin-top:6px;flex-wrap:wrap}
.acts button,.acts a{flex:0 0 auto;border:1px solid #d9e6cb;background:#eff6e9;color:#345b42;border-radius:7px;padding:4px 10px;font-size:12px;font-weight:600;text-decoration:none;cursor:pointer;line-height:1.5}
.acts button:active,.acts a:active{background:#e2efd6}
.acts .bv{color:#8a8f8b;background:none;border:none;font-weight:400;padding:4px 0;font-size:11.5px}
footer{margin-top:16px;font-size:11.5px;color:var(--mut)}
"""


LITE_UX = """
.item{transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease}
.item:hover{border-color:#b6cfa6;box-shadow:0 10px 22px -16px rgba(40,70,40,.55);transform:translateY(-1px)}
@media(max-width:560px){.item:hover{transform:none}}
"""


def render_lite(data):
    LITE_UX_CSS = ux.UX_CSS + LITE_UX
    items = data.get("items") or []
    cnt = {}
    for it in items:
        cnt[it["subject"]] = cnt.get(it["subject"], 0) + 1
    npin = sum(1 for it in items if it.get("pinned"))
    chips = [f'<span class="chip on" data-s="全部">全部 {len(items)}</span>']
    if npin:
        chips.append(f'<span class="chip pin" data-s="★置顶">★置顶 {npin}</span>')
    for s, n in sorted(cnt.items(), key=lambda x: -x[1]):
        chips.append(f'<span class="chip" data-s="{esc(s)}">{esc(s)} {n}</span>')
    rows = []
    for it in items:
        hay = (it.get("title", "") + " " + (it.get("up") or "") + " "
               + " ".join(it.get("teachers") or [])).lower()
        bv = (it.get("bvid") or os.path.basename(it.get("url") or "")) or ""
        url = it.get("url") or ""
        play = f"play/{bv}.html" if bv else url
        _pc = " pinned" if it.get("pinned") else ""
        _badge = '<span class="tag pin">置顶</span>' if it.get("pinned") else ""
        rows.append(
            f'<div class="item{_pc}" data-s="{esc(it["subject"])}" data-pin="{"1" if it.get("pinned") else "0"}" data-t="{esc(hay)}">'
            f'<a class="t" href="{play}">{esc(it.get("title"))}</a>'
            f'<div class="m">{_badge}<span class="tag s">{esc(it["subject"])}</span>'
            f'<span>{int(it.get("pages") or 0)} 集</span>'
            f'<span>{esc(it.get("dur_txt",""))}</span>'
            f'<span>▶{fmt_play(it.get("play"))}</span>'
            f'<span>{esc(it.get("date",""))}</span>'
            f'<span>UP：{esc(it.get("up") or "")}</span></div>'
            f'<div class="acts"><a class="play" href="{play}">站内播放 ▶</a>'
            f'<a href="{esc(url)}" target="_blank" rel="noopener">B站原页</a>'
            f'<button data-cp="{esc(bv)}">复制BV</button></div></div>')
    _html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{ux.theme_meta()}
<title>考研西综306 · 教学视频（精简版）</title>
<style>{LITE_CSS}{LITE_UX_CSS}</style></head><body><div class="wrap">
<header><h1>考研西医综合（306）教学视频 · 精简版</h1>
<div class="upd">数据更新：<b>{esc(data.get("updated",""))}</b> · 共 {len(items)} 套 · 无封面图，弱网秒开
<span class="live">自动刷新中</span><span class="rel" data-bjtime="{esc(data.get("updated",""))}">刚刚</span></div></header>
<div class="tip" id="tip">点标题直接进<b>站内播放页</b>（内嵌播放器+选集，不用跳 App）。若播放器空白，点「复制BV」到哔哩哔哩 App 搜索，或右上角「…」→「在浏览器打开」。</div>
<div class="chips" id="chips">{''.join(chips)}</div>
<input id="q" placeholder="搜标题 / UP 主 / 老师">
<div class="stat" id="stat">共 {len(items)} 套</div>
<div id="list">{''.join(rows)}</div>
<footer>点标题直接跳到 B 站课程页 · 版权归各 UP 主所有，本站仅做索引</footer>
</div>{ux.TO_TOP_HTML}<script>
(function(){{
 var list=document.getElementById('list'),items=[].slice.call(list.children),
     chips=document.getElementById('chips'),q=document.getElementById('q'),stat=document.getElementById('stat'),cur='全部';
 function ap(){{var k=q.value.trim().toLowerCase(),n=0;
  items.forEach(function(e){{var base=(cur==='全部')?true:(cur==='★置顶'?e.getAttribute('data-pin')==='1':e.getAttribute('data-s')===cur);
   var ok=base&&(!k||e.getAttribute('data-t').indexOf(k)>=0);e.style.display=ok?'':'none';if(ok)n++;}});
  stat.textContent='共 '+n+' 套'+(k?'（'+q.value.trim()+'）':'');}}
 chips.addEventListener('click',function(e){{var c=e.target.closest('.chip');if(!c)return;cur=c.getAttribute('data-s');
  [].forEach.call(chips.children,function(x){{var pin=x.getAttribute('data-s')==='★置顶';
    x.className='chip'+(pin?' pin':'')+(x.getAttribute('data-s')===cur?' on':'');}});q.value='';ap();}});
 q.addEventListener('input',function(){{if(this.value&&cur!=='全部'){{cur='全部';[].forEach.call(chips.children,function(x){{x.className='chip'+(x.getAttribute('data-s')==='全部'?' on':'');}});}}ap();}});
 if(/MicroMessenger/i.test(navigator.userAgent))document.getElementById('tip').className='tip show';
 document.getElementById('list').addEventListener('click',function(e){{
   var b=e.target.closest('button[data-cp]');if(!b)return;
   var v=b.getAttribute('data-cp'),t=b.textContent;
   function done(){{b.textContent='已复制 ✓';setTimeout(function(){{b.textContent=t;}},1400);}}
   if(navigator.clipboard&&navigator.clipboard.writeText){{navigator.clipboard.writeText(v).then(done).catch(fb);}}else{{fb();}}
   function fb(){{var i=document.createElement('textarea');i.value=v;i.style.position='fixed';i.style.opacity='0';document.body.appendChild(i);i.select();try{{document.execCommand('copy');done();}}catch(x){{prompt('长按复制',v);}}document.body.removeChild(i);}}
 }});
}})();
</script>
<script>{{UXJS}}</script>
</body></html>
"""
    return _html.replace("{UXJS}", ux.UX_JS)


def build(json_path, out_dir):
    """生成 xz/videos.html（含站内链接）与 xz/videos_offline.html（离线单文件）"""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    os.makedirs(out_dir, exist_ok=True)
    p1 = os.path.join(out_dir, "videos.html")
    p2 = os.path.join(out_dir, "videos_offline.html")
    with open(p1, "w", encoding="utf-8") as f:
        f.write(render(data, offline=False))
    with open(p2, "w", encoding="utf-8") as f:
        f.write(render(data, offline=True))
    p3 = os.path.join(out_dir, "videos_lite.html")
    with open(p3, "w", encoding="utf-8") as f:
        f.write(render_lite(data))
    return p1, p3, len(data.get("items") or [])


# ============ 站内播放页：内嵌 B 站官方播放器 + 分P选集 ============
PLAY_CSS = """
:root{--bg:#eef3e8;--card:#fff;--ink:#20301f;--mut:#5a6b56;--line:#d3ddc7}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;margin:0;padding:0 0 30px;-webkit-text-size-adjust:100%}
.top{background:#2f5540;color:#fff;padding:9px 12px;font-size:13px;display:flex;gap:10px;align-items:center}
.top a{color:#d6f5cf;text-decoration:none;font-weight:600}
.top .ttl{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;opacity:.95}
.pwrap{position:relative;width:100%;background:#000;aspect-ratio:16/9}
.pwrap iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.cover-guide{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:9px;padding:16px;text-align:center;background:linear-gradient(135deg,#3d5f49,#22392c);color:#fff}
.cg-t{font-size:14px;font-weight:700}
.cg-s{font-size:11.5px;opacity:.78;line-height:1.6;max-width:420px}
.cg-b{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-top:4px}
.big{border:1px solid rgba(255,255,255,.5);background:rgba(255,255,255,.14);color:#fff;border-radius:9px;padding:8px 14px;font-size:13px;font-weight:700;cursor:pointer;text-decoration:none}
.big:hover{background:rgba(255,255,255,.24)}
.big.ghost{background:rgba(143,240,168,.2);border-color:rgba(143,240,168,.55)}
.bar{padding:10px 12px;background:var(--card);border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:13px}
.bar b{font-size:13.5px}
.btn{border:1px solid #d9e6cb;background:#eff6e9;color:#345b42;border-radius:8px;padding:6px 12px;font-size:12.5px;font-weight:600;text-decoration:none;cursor:pointer}
.btn:disabled{opacity:.42}
.eps{max-width:1080px;margin:10px auto 0;padding:0 10px}
.eps h3{font-size:14px;margin:12px 4px 8px;color:#3d4f3a}
.eplist{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px}
.ep{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:7px 9px;font-size:12.5px;line-height:1.35;cursor:pointer;color:#33452f;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ep:hover{border-color:#9dbf8d}
.ep.on{background:#3f6b4f;color:#fff;border-color:#3f6b4f;font-weight:600}
@media(max-width:600px){.eplist{grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:5px}.ep{font-size:12px;padding:6px 8px}}
"""

PLAY_JS = """
(function(){
 var META=window.__META__||{}, PARTS=window.__PARTS__||[];
 var i=0, f=document.getElementById('pl'), t=document.getElementById('cur'),
     pv=document.getElementById('prev'), nx=document.getElementById('next'),
     list=document.getElementById('eplist');
 if(location.hash){var h=parseInt(location.hash.slice(1),10);if(h>0&&h<=PARTS.length)i=h-1;}
 var tried=false;
 function load(n){
   i=n;
   if(tried){
     f.src='https://player.bilibili.com/player.html?bvid='+META.bvid+'&page='+(n+1)+
           '&high_quality=1&danmaku=1&autoplay=1';
   }
   var g=document.getElementById('gobili');
   g.href='https://www.bilibili.com/video/'+META.bvid+'?p='+(n+1);
   var name=PARTS[n]||('第 '+(n+1)+' 集');
   t.textContent='第 '+(n+1)+'/'+PARTS.length+' 集 · '+name;
   pv.disabled=(n===0); nx.disabled=(n>=PARTS.length-1);
   history.replaceState(null,'','#'+(n+1));
   document.title=name+' · '+META.title;
   [].forEach.call(list.children,function(c,k){c.className='ep'+(k===n?' on':'');});
   if(list.children[n]&&list.children[n].scrollIntoView)list.children[n].scrollIntoView({block:'nearest'});
   window.scrollTo({top:0,behavior:'auto'});
 }
 list.addEventListener('click',function(e){var c=e.target.closest('.ep');if(c)load(+c.getAttribute('data-i'));});
 pv.addEventListener('click',function(){if(i>0)load(i-1)});
 nx.addEventListener('click',function(){if(i<PARTS.length-1)load(i+1)});
 document.addEventListener('keydown',function(e){
   if(e.key==='ArrowLeft'&&i>0)load(i-1);
   if(e.key==='ArrowRight'&&i<PARTS.length-1)load(i+1);});
 document.getElementById('tryplay').addEventListener('click',function(){
   tried=true;
   document.querySelector('.cover-guide').style.display='none';
   f.style.display='block';
   f.src='https://player.bilibili.com/player.html?bvid='+META.bvid+'&page='+(i+1)+
         '&high_quality=1&danmaku=1&autoplay=1';
 });
 document.getElementById('copy').addEventListener('click',function(){
   var b=this, o=b.textContent, v=META.bvid;
   function done(){b.textContent='已复制 ✓';setTimeout(function(){b.textContent=o},1400);}
   function fb(){var x=document.createElement('textarea');x.value=v;x.style.position='fixed';x.style.opacity='0';
     document.body.appendChild(x);x.select();try{document.execCommand('copy');done();}catch(e){prompt('长按复制',v);}document.body.removeChild(x);}
   if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(v).then(done).catch(fb);}else{fb();}
 });
 load(i);
})();
"""


PLAY_UX = """
#toTop{right:14px;bottom:58px}
@media(max-width:560px){#toTop{bottom:52px}}
"""


def render_play(meta, parts):
    PLAY_UX_CSS = ux.UX_CSS + PLAY_UX
    bv = meta.get("bvid") or ""
    eps = "".join(
        f'<div class="ep" data-i="{k}">{k+1}. {esc(p)}</div>'
        for k, p in enumerate(parts))
    if not parts:
        parts = ["正片"]
        eps = '<div class="ep on" data-i="0">1. 正片</div>'
    head = json.dumps({"bvid": bv, "title": meta.get("title", "")}, ensure_ascii=False)
    pj = json.dumps(parts, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
{ux.theme_meta()}
<title>{esc(meta.get("title"))}</title>
<style>{PLAY_CSS}{PLAY_UX_CSS}</style></head><body>
<div class="top"><a href="../videos_lite.html">← 列表</a>
  <span class="ttl">{esc(meta.get("title"))}</span></div>
<div class="pwrap" id="pw"><div class="cover-guide">
  <div class="cg-t">选集后点「去B站看本集」，或用下方「站内试播」</div>
  <div class="cg-s">B 站官方播放器对第三方页面常有限制，站内试播可能提示「视频链接失效」</div>
  <div class="cg-b"><button class="big" id="tryplay">站内试播（可能受限）</button>
  <a class="big ghost" id="gobili" target="_blank" rel="noopener">去B站看本集 ↗</a></div>
</div><iframe id="pl" style="display:none" allowfullscreen allow="autoplay; fullscreen; picture-in-picture" scrolling="no"></iframe></div>
<div class="bar">
  <button class="btn" id="prev">← 上一集</button>
  <button class="btn" id="next">下一集 →</button>
  <b id="cur">加载中…</b>
  <span style="margin-left:auto"></span>
  <button class="btn" id="copy">复制BV号</button>
  <a class="btn" href="https://www.bilibili.com/video/{esc(bv)}" target="_blank" rel="noopener">B站原页</a>
  <a class="btn" href="bilibili://video/{esc(bv)}">用App打开</a>
</div>
<div class="eps"><h3>选集（共 {len(parts)} 集）</h3><div class="eplist" id="eplist">{eps}</div></div>
<script>window.__META__={head};window.__PARTS__={pj};</script>
<script>{PLAY_JS}</script>
{ux.TO_TOP_HTML}
<script>""" + ux.UX_JS + """</script>
</body></html>
"""


def build_play_pages(videos_json, parts_json, out_dir):
    """为每套课生成 xz/play/BVxxx.html（内嵌播放器 + 选集）"""
    with open(videos_json, encoding="utf-8") as f:
        data = json.load(f)
    parts_map = {}
    if os.path.exists(parts_json):
        with open(parts_json, encoding="utf-8") as f:
            parts_map = json.load(f)
    pd = os.path.join(out_dir, "play")
    os.makedirs(pd, exist_ok=True)
    n = 0
    for it in data.get("items") or []:
        bv = it.get("bvid") or ""
        if not bv:
            continue
        parts = parts_map.get(bv) or it.get("parts") or []
        with open(os.path.join(pd, bv + ".html"), "w", encoding="utf-8") as f:
            f.write(render_play(it, parts))
        n += 1
    return n
