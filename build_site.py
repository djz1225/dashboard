#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成看板网站 v3：护眼配色 + 图表化 + 表格化，专科内容更丰富、易读"""
import json, os, re, html, shutil

OUT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(OUT, "site")

SRC_MAP = {
    "KDIGO": "https://kdigo.org/guidelines/",
    "中国慢性肾脏病筛查": "https://rs.yiigle.com/cmaid/1687484",
    "中国CKD": "https://rs.yiigle.com/cmaid/1687484",
    "CKD": "https://kdigo.org/guidelines/",
    "ADPKD": "https://kdigo.org/guidelines/",
    "IgA": "https://kdigo.org/guidelines/",
    "IPNA": "https://www.ipna-online.org/",
    "CRRT": "https://rs.yiigle.com/",
    "血液透析合并肾性贫血": "https://rs.yiigle.com/",
    "ESC": "https://www.escardio.org/guidelines/clinical-practice-guidelines/all-esc-practice-guidelines/",
    "ACC/AHA": "https://www.acc.org/guidelines",
    "ACC": "https://www.acc.org/guidelines",
    "AHA": "https://www.ahajournals.org/",
    "ESH": "https://www.eshonline.org/guidelines/",
    "ADA": "https://diabetesjournals.org/care",
    "AACE": "https://www.aace.com/publications/guidelines",
    "WHO": "https://www.who.int/",
    "肥胖": "https://guide.medlive.cn/",
    "中国成人体重管理指南": "https://guide.medlive.cn/",
    "糖尿病缓解": "https://guide.medlive.cn/",
    "肠促胰素": "https://guide.medlive.cn/",
    "ASN": "https://www.asn-online.org/",
    "MRA": "https://www.escardio.org/guidelines/",
    "高钾": "https://guide.medlive.cn/",
    "CGM": "https://guide.medlive.cn/",
    "降胆固醇": "https://www.chinacirculation.org/",
    "T2DM": "https://guide.medlive.cn/",
}
SPEC_ORDER = ["肾内科", "内分泌·体重管理", "心血管"]
COLORS = {"肾内科": "#3f6b4f", "内分泌·体重管理": "#3b6ea5", "心血管": "#b5651d"}
PALETTE = ["#3f6b4f", "#3b6ea5", "#b5651d", "#8b5cf6", "#c0392b", "#0e9488"]

def esc(t):
    t = re.sub(r"[\u2b50\u26a0\ufe0f\u2705\u274c\U0001f4ca\u25b8]", "", str(t))
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return t

def categorize(title):
    for k in ["指南", "共识", "声明", "标准", "建议", "算法", "纪要"]:
        if k in title:
            return k
    return "其他"

# ---------- 图表 ----------
def bar_chart(title, items, color="#3f6b4f"):
    if not items:
        return ""
    maxv = max(v for _, v in items) or 1
    rows = ""
    for lab, v in items:
        w = max(4, int(v / maxv * 100))
        rows += (f'<div class="brow"><span class="bl">{esc(lab)}</span>'
                 f'<span class="bt"><i style="width:{w}%;background:{color}"></i></span>'
                 f'<span class="bv">{v}</span></div>')
    return f'<div class="chart"><div class="ct">{esc(title)}</div>{rows}</div>'

def multi_bar(title, cats, series):
    """cats: 类别标签; series: [(label,[v...]),...]"""
    if not cats:
        return ""
    maxv = max([max(v) for _, v in series] + [1])
    legend = "".join(f'<span class="lg"><i style="background:{PALETTE[i%len(PALETTE)]}"></i>{esc(lab)}</span>'
                     for i, (lab, _) in enumerate(series))
    rows = ""
    for ci, c in enumerate(cats):
        bars = ""
        for si, (lab, vals) in enumerate(series):
            w = max(2, int(vals[ci] / maxv * 100))
            bars += f'<span class="bt"><i style="width:{w}%;background:{PALETTE[si%len(PALETTE)]}"></i></span>'
        rows += f'<div class="brow"><span class="bl">{esc(c)}</span><span class="bts">{bars}</span></div>'
    return f'<div class="chart"><div class="ct">{esc(title)}</div><div class="legend">{legend}</div>{rows}</div>'

def donut(title, items):
    if not items:
        return ""
    total = sum(v for _, v in items) or 1
    r = 52; c = 2 * 3.14159 * r; off = 0.0; segs = ""
    for i, (lab, v) in enumerate(items):
        L = c * v / total
        segs += (f'<circle r="{r}" cx="60" cy="60" fill="none" stroke="{PALETTE[i%len(PALETTE)]}" '
                 f'stroke-width="18" stroke-dasharray="{L:.2f} {c-L:.2f}" '
                 f'stroke-dashoffset="{-off:.2f}" transform="rotate(-90 60 60)"/>')
        off += L
    legend = "".join(f'<span class="lg"><i style="background:{PALETTE[i%len(PALETTE)]}"></i>{esc(lab)} {v}</span>'
                     for i, (lab, v) in enumerate(items))
    return (f'<div class="chart"><div class="ct">{esc(title)}</div>'
            f'<div class="donut"><svg viewBox="0 0 120 120" width="132" height="132">{segs}</svg>'
            f'<div class="legend dcol">{legend}</div></div></div>')

# ---------- 行情 ----------
def idx_cards(items):
    if not items:
        return '<div class="mut">获取中…</div>'
    out = []
    for it in items:
        pct = it["pct"]; sign = "+" if pct >= 0 else ""
        cls = "up" if pct >= 0 else "down"
        out.append(f'<div class="icard"><div class="iname">{it["name"]}</div>'
                   f'<div class="iprice">{it["price"]:,.2f}</div>'
                   f'<div class="ipct {cls}">{sign}{pct:.2f}%</div></div>')
    return "\n".join(out)

def sec_rows(items):
    if not items:
        return '<tr><td colspan="3" class="mut">暂无数据</td></tr>'
    out = []
    for i, it in enumerate(items, 1):
        pct = it["pct"]; sign = "+" if pct >= 0 else ""
        cls = "up" if pct >= 0 else "down"
        out.append(f'<tr><td class="rk">{i}</td><td class="nm">{it["name"]}</td>'
                   f'<td class="pc {cls}">{sign}{pct:.2f}%</td></tr>')
    return "\n".join(out)

# ---------- 专科提要（要点表格化） ----------
LEVEL_CLS = {"核心": "lv-core", "推荐": "lv-rec", "须知": "lv-note"}

def render_points(points):
    """含 ｜ 的行转为表格；其余为列表"""
    table_rows, texts, in_tbl = [], [], False
    for p in points:
        if "｜" in p:
            table_rows.append([x.strip() for x in p.split("｜")])
            in_tbl = True
        else:
            texts.append(p)
    out = ""
    if texts:
        out += '<ul class="pts">' + "".join(
            f'<li class="sub">{esc(t[1:-1])}</li>' if (t.startswith("【") and t.endswith("】")) else f'<li>{esc(t)}</li>'
            for t in texts) + "</ul>"
    if table_rows:
        ncol = max(len(r) for r in table_rows)
        head = table_rows[0]
        out += '<table class="itbl">'
        out += "<tr>" + "".join(f"<th>{esc(h)}</th>" for h in head) + "</tr>"
        for r in table_rows[1:]:
            r = r + [""] * (ncol - len(r))
            out += "<tr>" + "".join(f"<td>{esc(cell)}</td>" for cell in r) + "</tr>"
        out += "</table>"
    return out or '<div class="mut">详见附件原文</div>'

def spec_cards(specs):
    if not specs:
        return '<div class="mut">暂无专科提要</div>'
    out = []
    for s in specs:
        att = f'attachment_{s["key"]}.html'
        rows = []
        for n, it in enumerate(s["items"], 1):
            lv = it["level"]; lvcls = LEVEL_CLS.get(lv, "lv-rec")
            rows.append(f'''<div class="item">
  <div class="item-h"><span class="num">{n}</span><span class="lv {lvcls}">{lv}</span><span class="inm">{esc(it["name"]).strip()}</span></div>
  {render_points(it["points"])}
  <a class="go" href="{att}" target="_blank">查看原文详解 →</a>
</div>''')
        out.append(f'''<div class="scard">
  <div class="scard-h"><span class="tag">{esc(s["specialty"])}</span><span class="sdate">{s["date"]}</span></div>
  <div class="stitle">{esc(s["title"])}</div>
  <div class="items">{"".join(rows)}</div>
</div>''')
    return "\n".join(out)

# ---------- 文章（表格化 + 图表数据） ----------
def art_table(arts):
    if not arts:
        return '<div class="mut">暂无文章（运行“维护看板”后更新）</div>'
    groups = {}
    for a in arts:
        groups.setdefault(a.get("specialty", "其他"), []).append(a)
    keys = [k for k in SPEC_ORDER if k in groups] + [k for k in groups if k not in SPEC_ORDER]
    out = []
    for sp in keys:
        lst = sorted(groups[sp], key=lambda x: x.get("date", ""), reverse=True)
        rows = ""
        for a in lst:
            url = a.get("url", ""); title = esc(a.get("title", ""))
            link = f'<a class="alink" href="{url}" target="_blank">{title}</a>' if url else title
            pts = "；".join(esc(p) for p in a.get("points", [])[:3])
            rows += (f'<tr><td class="art-t">{link}</td>'
                     f'<td class="art-d">{esc(a.get("date",""))}</td></tr>'
                     f'<tr class="art-p"><td colspan="2">{pts}</td></tr>')
        out.append(f'''<div class="scard">
  <div class="scard-h"><span class="tag">{esc(sp)}</span><span class="sdate">共 {len(lst)} 篇</span></div>
  <table class="arttbl">{rows}</table>
</div>''')
    return "\n".join(out)

KEYWORDS = ["非奈利酮", "SGLT2i", "RASi", "GLP-1", "他汀", "依折麦布", "PCSK9", "LDL-C",
            "Lp(a)", "PREVENT", "MRA", "KFRE", "eGFR", "UACR", "ESA", "HIF-PHI",
            "CKD", "CKM", "减重", "BMI", "房颤", "DOAC", "心衰", "血压",
            "替尔泊肽", "司美格鲁肽", "玛仕度肽", "铁蛋白", "HbA1c", "缓解"]

def keyword_freq(arts):
    text = " ".join((a.get("title", "") + " " + " ".join(a.get("points", []))) for a in arts)
    cnt = []
    for k in KEYWORDS:
        n = text.count(k)
        if n > 0:
            cnt.append((k, n))
    cnt.sort(key=lambda x: -x[1])
    return cnt[:12]

def overview(arts):
    if not arts:
        return '<div class="mut">暂无数据</div>'
    by_sp = {}; by_cat = {}; by_mon = {}
    for a in arts:
        by_sp[a.get("specialty", "其他")] = by_sp.get(a.get("specialty", "其他"), 0) + 1
        cat = categorize(a.get("title", ""))
        by_cat[cat] = by_cat.get(cat, 0) + 1
        mon = (a.get("date", "") or "")[:7]
        if mon:
            by_mon[mon] = by_mon.get(mon, 0) + 1
    sp_items = [(k, by_sp[k]) for k in SPEC_ORDER if k in by_sp]
    cat_items = sorted(by_cat.items(), key=lambda x: -x[1])
    mon_items = sorted(by_mon.items())
    return (bar_chart("各专科收录文章数", sp_items, "#3f6b4f") +
            donut("文章类型占比", cat_items) +
            bar_chart("按月份发布分布", mon_items, "#3b6ea5") +
            bar_chart("热门方向词频", keyword_freq(arts), "#8b5cf6"))

MAIN_CSS = """
:root{--bg:#e9efe3;--card:#ffffff;--ink:#20301f;--mut:#5a6b56;--line:#cfdcc4;
--up:#c0392b;--down:#1e8449;--acc:#3f6b4f;--core:#2f6b46;--rec:#3b6ea5;--note:#b5651d;}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.7;padding:24px 18px}
.wrap{max-width:1180px;margin:0 auto}
header{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:flex-end;gap:10px;border-bottom:2px solid var(--acc);padding-bottom:16px;margin-bottom:8px}
h1{font-size:26px;font-weight:800;color:var(--acc);letter-spacing:.5px}
.updated{color:var(--mut);font-size:14px}
.updated .live{color:#8fa287;font-size:12px;margin-left:6px}
h2{font-size:19px;margin:30px 0 14px;color:#1d3a28;border-left:5px solid var(--acc);padding-left:12px}
.grid{display:grid;gap:14px}
.g4{grid-template-columns:repeat(4,1fr)}
.g2{grid-template-columns:1fr 1fr}
.g3{grid-template-columns:repeat(3,1fr)}
.icard{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;box-shadow:0 1px 3px rgba(40,70,40,.06)}
.iname{color:var(--mut);font-size:14px;font-weight:600}
.iprice{font-size:24px;font-weight:800;margin:6px 0;font-variant-numeric:tabular-nums}
.ipct{font-size:16px;font-weight:700}
.up{color:var(--up)}.down{color:var(--down)}
.tbl{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.tbl h3{font-size:15px;color:#1d3a28;margin-bottom:10px;font-weight:700}
table{width:100%;border-collapse:collapse;font-size:15px}
td,th{padding:8px 6px;border-bottom:1px solid #e6eddd;text-align:left}
th{color:#1d3a28;font-weight:700;background:#f1f6ec}
td.rk{color:var(--mut);width:28px;font-variant-numeric:tabular-nums}
td.nm{font-weight:600}
td.pc{text-align:right;font-weight:700;font-variant-numeric:tabular-nums;width:90px}
tr:last-child td{border-bottom:none}
.mut{color:var(--mut)}
/* 图表 */
.chart{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;box-shadow:0 1px 3px rgba(40,70,40,.06)}
.ct{font-size:15px;font-weight:700;color:#1d3a28;margin-bottom:12px}
.brow{display:flex;align-items:center;gap:10px;margin:7px 0}
.bl{width:110px;font-size:14px;color:#2c3f2c;flex:0 0 110px;text-align:right}
.bt{flex:1;background:#eef3e8;border-radius:6px;height:16px;overflow:hidden;display:block}
.bt i{display:block;height:100%;border-radius:6px}
.bts{flex:1;display:flex;gap:4px}
.bts .bt{height:14px}
.bv{width:34px;text-align:right;font-weight:700;font-variant-numeric:tabular-nums;font-size:14px}
.legend{display:flex;flex-wrap:wrap;gap:12px;margin:6px 0 12px}
.legend.dcol{flex-direction:column;gap:6px}
.lg{font-size:13.5px;color:#2c3f2c;display:inline-flex;align-items:center;gap:6px}
.lg i{width:11px;height:11px;border-radius:3px;display:inline-block}
.donut{display:flex;align-items:center;gap:18px;flex-wrap:wrap}
/* 专科卡 */
.scard{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px 22px;box-shadow:0 2px 6px rgba(40,70,40,.06);display:flex;flex-direction:column}
.scard-h{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.tag{background:#e4efe0;color:var(--acc);border:1px solid #bcd3b0;border-radius:6px;padding:3px 12px;font-size:15px;font-weight:700}
.sdate{color:var(--mut);font-size:14px}
.stitle{font-size:19px;font-weight:800;line-height:1.45;margin-bottom:14px;color:#17281a}
.item{border-top:1px solid #e6eddd;padding:14px 0}
.item:first-child{border-top:none;padding-top:4px}
.item-h{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.num{background:var(--acc);color:#fff;width:26px;height:26px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:15px;font-weight:700;flex:0 0 26px}
.lv{font-size:13px;font-weight:700;padding:1px 9px;border-radius:4px;color:#fff}
.lv-core{background:var(--core)}.lv-rec{background:var(--rec)}.lv-note{background:var(--note)}
.inm{font-size:17.5px;font-weight:700;color:#1d3a28}
.pts{list-style:none;margin:0 0 8px 36px;font-size:17px}
.pts li{position:relative;padding-left:16px;margin-bottom:5px;color:#2c3f2c}
.pts li:before{content:"";position:absolute;left:0;top:.72em;width:6px;height:6px;border-radius:50%;background:#9ab98c}
.pts li.sub{color:var(--acc);font-weight:700;margin-top:6px}
.pts li.sub:before{width:12px;height:3px;border-radius:2px;top:.62em;background:var(--acc)}
table.itbl{margin:6px 0 8px 36px;width:calc(100% - 36px);font-size:15.5px;border:1px solid #e0e9d6;border-radius:8px;overflow:hidden}
table.itbl th{background:#eef5e9;font-size:14.5px;white-space:nowrap}
table.itbl td{border-bottom:1px solid #eaf0e2}
.go{align-self:flex-start;margin-left:36px;color:var(--rec);font-size:15px;font-weight:600;text-decoration:none;border-bottom:1px dashed var(--rec)}
.go:hover{color:#1e4e80}
table.arttbl{font-size:15.5px}
.art-t{font-weight:700}
.art-t a.alink{color:#2f5e8c;text-decoration:none}
.art-t a.alink:hover{text-decoration:underline}
.art-d{color:var(--mut);white-space:nowrap;width:96px;font-size:14px}
tr.art-p td{color:#42533f;font-size:15px;padding-top:2px;border-bottom:1px solid #e6eddd}
footer{margin-top:34px;padding-top:16px;border-top:1px solid var(--line);color:var(--mut);font-size:13px}
@media(max-width:860px){
.g4,.g3{grid-template-columns:1fr 1fr}
.g2{grid-template-columns:1fr}
.bl{width:84px;flex:0 0 84px}
h1{font-size:22px}
.iprice{font-size:20px}
.stitle{font-size:17px}
.inm{font-size:16.5px}
.pts{font-size:15.5px;margin-left:26px}
table.itbl{margin-left:26px;width:calc(100% - 26px)}
.go{margin-left:26px}
}
@media(max-width:560px){
body{padding:14px 10px}
.grid{gap:10px}
.g4,.g3,.g2{grid-template-columns:1fr}
h1{font-size:19px}
h2{font-size:16.5px;margin:24px 0 12px;padding-left:9px}
.icard{padding:12px}
.iprice{font-size:19px}
.tbl{padding:10px 12px}
.chart{padding:12px 14px}
.bl{width:64px;flex:0 0 64px;font-size:12px}
.bv{width:26px;font-size:12px}
.bt{height:13px}
.stitle{font-size:15.5px}
.inm{font-size:15px}
.num{width:22px;height:22px;flex-basis:22px;font-size:13px}
.pts{font-size:14.5px;margin:0 0 8px 12px}
table.itbl{margin-left:12px;width:calc(100% - 12px);font-size:13px}
.go{margin-left:12px;font-size:13.5px}
.tag{font-size:13.5px;padding:2px 9px}
table{font-size:13px}
td,th{padding:6px 5px}
.tbl,.scard{overflow-x:auto}
}
"""

MAIN_TPL = r"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>每日追踪看板</title><style>__CSS__</style></head><body><div class="wrap">
<header><h1>每日追踪看板</h1><div class="updated" id="updated">数据更新：__UPDATED__<span class="live">· 自动刷新中</span></div></header>

<h2>一、大盘行情</h2>
<div class="grid g4" id="cnIdx">__CNIDX__</div><div style="height:14px"></div><div class="grid g4" id="usIdx">__USIDX__</div>

<h2>二、板块涨跌榜（涨 / 跌 前 10）</h2>
<div class="grid g2">
<div class="tbl"><h3>A股 · 行业涨幅前 10</h3><table id="cnUp">__CNUP__</table></div>
<div class="tbl"><h3>A股 · 行业跌幅前 10</h3><table id="cnDn">__CNDN__</table></div>
<div class="tbl"><h3>美股 · 行业涨幅前 10</h3><table id="usUp">__USUP__</table></div>
<div class="tbl"><h3>美股 · 行业跌幅前 10</h3><table id="usDn">__USDN__</table></div>
</div>

<h2>三、三专科指南 · 数据概览</h2>
<div class="grid g2">__OVERVIEW__</div>

<h2>四、三专科指南 · 重点提要</h2>
<div class="grid g2">__SPECS__</div>

<h2>五、三专科 · 最新发表文章</h2>
<div class="grid g2">__ARTS__</div>

<footer>行情来源：新浪财经（A股指数 / 行业板块、美股指数 / SPDR 11 行业 ETF）。专科内容由每日对比提要文件与文章库自动解析，点击标题/链接可查原文。</footer>
</div>
<script>
(function(){
  function $(id){return document.getElementById(id);}
  var last=null;
  function sgn(p){return p>=0?'+':'';}
  function cls(p){return p>=0?'up':'down';}
  function fmt(n){var t=Number(n).toFixed(2).split('.');t[0]=t[0].replace(/\B(?=(\d{3})+(?!\d))/g,',');return t.join('.');}
  function idxHTML(items){
    if(!items||!items.length)return '<div class="mut">获取中…</div>';
    return items.map(function(it){var p=Number(it.pct);
      return '<div class="icard"><div class="iname">'+it.name+'</div><div class="iprice">'+fmt(it.price)+'</div><div class="ipct '+cls(p)+'">'+sgn(p)+p.toFixed(2)+'%</div></div>';
    }).join('');
  }
  function secHTML(items){
    if(!items||!items.length)return '<tr><td colspan="3" class="mut">暂无数据</td></tr>';
    return items.map(function(it,i){var p=Number(it.pct);
      return '<tr><td class="rk">'+(i+1)+'</td><td class="nm">'+it.name+'</td><td class="pc '+cls(p)+'">'+sgn(p)+p.toFixed(2)+'%</td></tr>';
    }).join('');
  }
  function set(id,html){var e=$(id);if(e)e.innerHTML=html;}
  function apply(d){
    var u=$('updated');if(u&&d.updated)u.innerHTML='数据更新：'+d.updated+'<span class="live">· 自动刷新中</span>';
    set('cnIdx',idxHTML(d.cn_index));
    set('usIdx',idxHTML(d.us_index));
    set('cnUp',secHTML((d.cn_sectors||{}).up));
    set('cnDn',secHTML((d.cn_sectors||{}).down));
    set('usUp',secHTML((d.us_sectors||{}).up));
    set('usDn',secHTML((d.us_sectors||{}).down));
  }
  function tick(){
    fetch('data.json?_='+Date.now(),{cache:'no-store'}).then(function(r){return r.json();}).then(function(d){
      if(d&&d.updated!==last){last=d.updated;apply(d);}
    }).catch(function(){});
  }
  setInterval(tick,90000);
  document.addEventListener('visibilitychange',function(){if(!document.hidden)tick();});
  setTimeout(tick,4000);
})();
</script>
</body></html>"""

ATT_CSS = """
:root{--bg:#eef3e8;--card:#fff;--ink:#20301f;--mut:#5a6b56;--line:#d3ddc7;--acc:#3f6b4f;}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.8;padding:28px 18px}
.wrap{max-width:900px;margin:0 auto;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:30px 36px}
h2{font-size:24px;color:var(--acc);margin-bottom:6px}
h3{font-size:19px;color:#1d3a28;margin:22px 0 10px;padding-left:10px;border-left:4px solid var(--acc)}
h4{font-size:17px;color:var(--acc);margin:16px 0 6px}
p{font-size:16.5px;margin:7px 0}
p.q{color:var(--mut);font-size:15px;background:#f3f7ee;border-left:3px solid #bcd3b0;padding:8px 12px;border-radius:0 6px 6px 0}
li{font-size:16.5px;margin:4px 0 4px 20px}
table{width:100%;border-collapse:collapse;margin:12px 0;font-size:15.5px}
td,th{border:1px solid #dbe5d0;padding:8px 10px}
th{background:#eef5e9;font-weight:700;color:#1d3a28}
.src{background:#f3f7ee;border:1px solid #d3ddc7;border-radius:10px;padding:14px 16px;margin:18px 0;font-size:15px}
.src a{color:#3b6ea5;text-decoration:none;font-weight:600}
.back{display:inline-block;margin-top:10px;color:#3b6ea5;font-weight:600;text-decoration:none}
@media(max-width:680px){body{padding:16px 10px}.wrap{padding:18px 14px;border-radius:10px}h2{font-size:20px}h3{font-size:17px}h4{font-size:15.5px}p,li{font-size:15px}table{font-size:14px}td,th{padding:6px 7px}}
"""

def md_to_html(md):
    out, in_tbl = [], False; sec_n = 0
    for raw in md.splitlines():
        s = raw.rstrip()
        if s.startswith("|") and s.count("|") >= 2:
            cells = [c.strip() for c in s.strip().strip("|").split("|")]
            if cells and all(re.fullmatch(r"[-: ]*", c) for c in cells):
                continue
            tag = "th" if not in_tbl else "td"
            if not in_tbl:
                out.append("<table>"); in_tbl = True
            out.append("<tr>" + "".join(f"<{tag}>{esc(c)}</{tag}>" for c in cells) + "</tr>")
            continue
        if in_tbl:
            out.append("</table>"); in_tbl = False
        if s.startswith("# "):
            out.append(f"<h2>{esc(s[2:])}</h2>")
        elif s.startswith("## "):
            head = s[3:]
            if re.match(r"^[一二三四五六七八九十]+、", head) and "总结" not in head and "重复" not in head:
                sec_n += 1
                out.append(f'<h3 id="i{sec_n}">{esc(head)}</h3>')
            else:
                out.append(f"<h3>{esc(head)}</h3>")
        elif s.startswith("### ") or s.startswith("#### "):
            out.append(f"<h4>{esc(re.sub(r'^#+ ', '', s))}</h4>")
        elif s.startswith("> "):
            out.append(f'<p class="q">{esc(s[2:])}</p>')
        elif s.startswith("- ") or s.startswith("* "):
            out.append(f"<li>{esc(s[2:])}</li>")
        elif s.strip() == "":
            continue
        else:
            out.append(f"<p>{esc(s)}</p>")
    if in_tbl:
        out.append("</table>")
    return "\n".join(out)

def build_attachment(s):
    links = find_links(s.get("source", ""))
    link_html = " ".join(f'<a href="{u}" target="_blank">原文出处 {i+1} ↗</a>' for i, u in enumerate(links))
    body = md_to_html(s.get("md", ""))
    src = esc(s.get("source", "")) if s.get("source") else ""
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(s["specialty"])} · 原文详解</title><style>{ATT_CSS}</style></head><body><div class="wrap">
<h2>{esc(s["specialty"])} · 重点提要原文详解</h2>
<p class="q">日期：{s["date"]} ｜ 来源：每日对比提要文件自动解析</p>
<div class="src"><b>内容出处：</b>{src or "见下方正文"}<br>{link_html}</div>
{body}
<a class="back" href="index.html">← 返回看板</a>
</div></body></html>"""

def find_links(source):
    links = []
    for kw, url in SRC_MAP.items():
        if kw and kw.lower() in (source or "").lower() and url not in links:
            links.append(url)
    return links[:3]

def main():
    with open(os.path.join(OUT, "data.json"), encoding="utf-8") as f:
        d = json.load(f)
    os.makedirs(SITE, exist_ok=True)
    html_main = (MAIN_TPL.replace("__CSS__", MAIN_CSS)
                 .replace("__UPDATED__", d.get("updated", ""))
                 .replace("__CNIDX__", idx_cards(d.get("cn_index", [])))
                 .replace("__USIDX__", idx_cards(d.get("us_index", [])))
                 .replace("__CNUP__", sec_rows(d.get("cn_sectors", {}).get("up", [])))
                 .replace("__CNDN__", sec_rows(d.get("cn_sectors", {}).get("down", [])))
                 .replace("__USUP__", sec_rows(d.get("us_sectors", {}).get("up", [])))
                 .replace("__USDN__", sec_rows(d.get("us_sectors", {}).get("down", [])))
                 .replace("__OVERVIEW__", overview(d.get("articles", [])))
                 .replace("__SPECS__", spec_cards(d.get("specialties", [])))
                 .replace("__ARTS__", art_table(d.get("articles", []))))
    shutil.copy(os.path.join(OUT, "data.json"), os.path.join(SITE, "data.json"))
    _quiz = os.path.join(OUT, "quiz.html")
    if os.path.exists(_quiz):
        shutil.copy(_quiz, os.path.join(SITE, "quiz.html"))
        print("site/quiz.html copied")
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_main)
    for s in d.get("specialties", []):
        with open(os.path.join(SITE, f'attachment_{s["key"]}.html'), "w", encoding="utf-8") as f:
            f.write(build_attachment(s))
    print("site/index.html +", len(d.get("specialties", [])), "attachments ->", SITE)

if __name__ == "__main__":
    main()
# trigger build: 2026-10-09 02:35 UTC
# trigger build: 2026-10-09 02:59 UTC
