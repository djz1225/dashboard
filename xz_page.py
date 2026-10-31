#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 xz/videos.json 渲染成「服务端直出」的静态页面（不依赖 JS 与额外网络请求）。

为什么这么做：手机上弱网（~2KB/s）时，靠 JS fetch JSON 再渲染会先看到空页/加载失败。
这里把卡片与筛选标签全部写进 HTML，JS 只负责筛选/排序（渐进增强），断网也能看。
"""
import json, os, re, html

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
.parts{font-size:12px;color:#6b7d66;line-height:1.5}
.foot{margin-top:auto;display:flex;align-items:center;gap:8px;padding-top:3px}
.plays{font-size:12px;color:var(--mut)}
.go{margin-left:auto;display:inline-flex;align-items:center;min-height:36px;padding:0 13px;border-radius:9px;background:#eff6e9;border:1px solid #d9e6cb;color:#345b42;font-weight:700;font-size:13px;text-decoration:none}
.go:hover{background:#e6f1dc}
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
  apply();
})();
"""


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def fmt_play(n):
    n = int(n or 0)
    return f"{n/10000:.1f}万" if n >= 10000 else str(n)


def card_html(it):
    tags = [f'<span class="tag sub">{esc(it["subject"])}</span>']
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
                  str(it.get("score", 0))])
    hay = (it.get("title", "") + " " + up + " " + " ".join(it.get("teachers") or [])).lower()
    return (
        f'<article class="card" data-s="{esc(it["subject"])}" data-t="{esc(hay)}" data-k="{esc(k)}">'
        f'<a class="cover" href="{esc(it.get("url"))}" target="_blank" rel="noopener">{img}'
        f'<span class="pg">{int(it.get("pages") or 0)} P</span>'
        f'<span class="dur">{esc(it.get("dur_txt",""))}</span></a>'
        f'<div class="body"><div class="ttl">{esc(it.get("title"))}</div>'
        f'<div class="meta">{"".join(tags)}<span class="tag">UP：{esc(up)}</span></div>'
        f'<div class="foot"><span class="plays">▶ {fmt_play(it.get("play"))} 播放</span>'
        f'<a class="go" href="{esc(it.get("url"))}" target="_blank" rel="noopener">去学习 ↗</a>'
        f'</div></div></article>'
    )


def _ts(d):
    """YYYY-MM-DD -> 可比较整数"""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(d or ""))
    return int("".join(m.groups())) if m else 0


def render(data, offline=False):
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
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>考研西医综合（306）成套教学视频</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>考研西医综合（306）成套教学视频</h1>
  <div class="sub">收录 B 站公开的多分 P / 长系列精讲课程，剔除散课与失效视频</div>
  <div class="upd">数据更新：{esc(data.get("updated",""))}（北京时间） · 共 {len(items)} 套 · 每天自动刷新</div>
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
</body>
</html>
"""


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
    return p1, p2, len(data.get("items") or [])
