#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日看板数据抓取 v2：A股/美股指数 + 板块涨跌榜 + 三专科结构化提要"""
import json, os, re, sys, datetime, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = ROOT
SEARCH_DIRS = [os.path.join(ROOT, "specialties"), ROOT, "/sandbox/workspace/outputs"]
SITE = os.path.join(OUT, "site")

def http_get(url, decode="utf-8", referer=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    if referer:
        req.add_header("Referer", referer)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode(decode, errors="replace")

def q_sina(codes, referer="https://finance.sina.com.cn"):
    url = "https://hq.sinajs.cn/list=" + ",".join(codes)
    txt = http_get(url, "gbk", referer=referer)
    out = {}
    for line in txt.splitlines():
        m = re.search(r'hq_str_([^=]+)="([^"]*)"', line)
        if m:
            out[m.group(1)] = m.group(2).split(",")
    return out

def fetch_cn_index():
    d = q_sina(["sh000001", "sz399001", "sz399006", "sh000300"])
    meta = {"sh000001": "上证指数", "sz399001": "深证成指", "sz399006": "创业板指", "sh000300": "沪深300"}
    res = []
    for code, nm in meta.items():
        f = d.get(code)
        if not f or len(f) < 4: continue
        try:
            prev, cur = float(f[2]), float(f[3])
            pct = (cur - prev) / prev * 100 if prev else 0
        except Exception: continue
        res.append({"name": nm, "price": round(cur, 2), "pct": round(pct, 2)})
    return res

def fetch_cn_sectors():
    txt = http_get("https://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php", "gbk")
    i = txt.find("{")
    if i < 0: return {"up": [], "down": []}
    data = json.loads(txt[i:])
    rows = []
    for k, v in data.items():
        p = v.split(",")
        if len(p) < 7: continue
        try:
            name = p[1].strip() or p[0]; pct = float(p[5])
        except Exception: continue
        rows.append({"name": name, "pct": round(pct, 2)})
    rows.sort(key=lambda x: x["pct"], reverse=True)
    return {"up": rows[:10], "down": rows[-10:][::-1]}

US_SECTORS = {"gb_xlk": "科技", "gb_xle": "能源", "gb_xlf": "金融", "gb_xlv": "医疗",
              "gb_xly": "非必需消费", "gb_xlp": "必需消费", "gb_xli": "工业", "gb_xlb": "材料",
              "gb_xlu": "公用事业", "gb_xlre": "房地产", "gb_xlc": "通信服务"}
def fetch_us_index():
    d = q_sina(["gb_$dji", "gb_$ixic", "gb_$inx"])
    meta = {"gb_$dji": "道琼斯", "gb_$ixic": "纳斯达克", "gb_$inx": "标普500"}
    res = []
    for code, nm in meta.items():
        f = d.get(code)
        if not f or len(f) < 3: continue
        try: cur, pct = float(f[1]), float(f[2])
        except Exception: continue
        res.append({"name": nm, "price": round(cur, 2), "pct": round(pct, 2)})
    return res

def fetch_us_sectors():
    d = q_sina(list(US_SECTORS.keys()))
    rows = []
    for code, nm in US_SECTORS.items():
        f = d.get(code)
        if not f or len(f) < 3: continue
        try: pct = float(f[2])
        except Exception: continue
        rows.append({"name": nm, "pct": round(pct, 2)})
    rows.sort(key=lambda x: x["pct"], reverse=True)
    return {"up": rows[:10], "down": rows[-10:][::-1]}

# ---------------- 三专科结构化解析 ----------------
SPECS = [("肾内科", "肾内科"), ("内分泌", "内分泌·体重管理"), ("心血管", "心血管")]

def _clean(s):
    s = s.strip()
    s = re.sub(r"^[\-\*\u2022\s]+", "", s)
    s = s.replace("**", "").replace("⭐", "").replace("⚠️", "").replace("✓", "").replace("❌", "（不推荐）")
    s = s.replace("✅", "（推荐）").replace("➡️", "→").replace("⭐️", "")
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s

def _level(name, text):
    n = name
    if any(k in n for k in ["红线", "注意", "警示", "禁用", "须知", "风险", "误区"]):
        return "须知"
    if any(k in n for k in ["核心", "关键", "速览", "选择", "逻辑", "结论", "要点", "定义", "目标", "新增", "全景", "对照", "差异", "更新", "文件"]):
        return "核心"
    return "推荐"

def parse_md(md, disp, date):
    lines = md.splitlines()
    title = ""
    for ln in lines:
        if ln.startswith("## 主标题"):
            title = ln.split("：", 1)[-1].strip().lstrip("：").strip()
            break
    items, cur, started = [], None, False

    def flush():
        nonlocal cur
        if cur is not None and cur["points"]:
            items.append(cur)
        cur = None

    for ln in lines:
        if ln.startswith("## ") and not ln.startswith("###"):
            head = ln[3:].strip()
            if head.startswith("主标题"):
                continue
            if any(k in head for k in ["重复内容", "总结", "其他动态", "重复"]):
                flush()
                started = False
                continue
            flush()
            nm = re.sub(r"^[①②③④⑤⑥⑦⑧⑨⑩0-9一二三四五六七八九十]+[、\.\s]+", "", head).strip()
            nm = re.sub(r"^[\*⭐\s]+", "", nm).strip()
            cur = {"name": nm, "points": []}
            started = True
            continue
        if not started or cur is None:
            continue
        st = ln.strip()
        if not st or st.startswith(">"):
            continue
        if st.startswith("#### "):
            sub = re.sub(r"^[#\s]+", "", st).strip("：: ").strip()
            if sub:
                cur["points"].append("【" + sub + "】")
            continue
        if st.startswith("### "):
            sub = re.sub(r"^[#\s①-⑳0-9\.、]+", "", st).strip("：: ").strip()
            sub = re.sub(r"^[\*⭐\s]+", "", sub).strip()
            if not sub:
                continue
            if cur["points"]:
                flush()
            cur = {"name": sub, "points": []}
            continue
        if st.startswith("|"):
            cells = [_clean(c) for c in st.strip().strip("|").split("|") if c.strip()]
            cells = [c for c in cells if c and not re.fullmatch(r"[\-: ]+", c)]
            if len(cells) >= 2:
                cur["points"].append(" ｜ ".join(cells))
            elif cells:
                cur["points"].append(cells[0])
            continue
        s = _clean(st)
        if s:
            cur["points"].append(s)
    flush()
    for it in items:
        it["level"] = _level(it["name"], " ".join(it["points"]))
        it["points"] = [p for p in it["points"] if p]
    summary = ""
    m = re.search(r"##[^#\n]*总结[^\n]*\n+>\s*(.*)", md)
    if m:
        summary = _clean(m.group(1))
    src = ""
    ms = re.search(r"来源声明[:：]\s*(.*)", md)
    if ms:
        src = _clean(ms.group(1))
    return {"title": title, "items": items, "summary": summary, "source": src[:260]}

def _guess_specialty(md):
    head = md[:400]
    if "心血管" in head:
        return "心血管", "心血管"
    if "内分泌" in head:
        return "内分泌", "内分泌·体重管理"
    if "肾内科" in head or "肾脏" in head:
        return "肾内科", "肾内科"
    return None, None

def _file_date(path, md):
    m = re.search(r"(20\d{6})", os.path.basename(path))
    if m:
        try:
            return datetime.datetime.strptime(m.group(1), "%Y%m%d").date()
        except Exception:
            pass
    m = re.search(r"(20\d{2})[-./年](\d{1,2})[-./月](\d{1,2})", md[:600])
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except Exception:
            pass
    return datetime.date.fromtimestamp(os.path.getmtime(path))

def fetch_specialties(days=90):
    """按内容识别专科（不依赖文件名，兼容中文文件名乱码），取每科最新一份。"""
    best = {}
    for base in SEARCH_DIRS:
        if not os.path.isdir(base):
            continue
        for fn in sorted(os.listdir(base)):
            if not fn.lower().endswith(".md"):
                continue
            fp = os.path.join(base, fn)
            try:
                with open(fp, encoding="utf-8", errors="replace") as f:
                    md = f.read()
            except Exception:
                continue
            key, disp = _guess_specialty(md)
            if not key:
                continue
            dt = _file_date(fp, md)
            if key not in best or dt > best[key][0]:
                best[key] = (dt, disp, md)
    res = []
    for key, disp in SPECS:
        if key not in best:
            continue
        dt, _disp, md = best[key]
        s = parse_md(md, disp, dt)
        s["specialty"] = disp
        s["date"] = dt.strftime("%Y-%m-%d")
        s["key"] = key
        s["md"] = md
        res.append(s)
    return res

def load_articles():
    fp = os.path.join(OUT, "articles.json")
    if os.path.exists(fp):
        try:
            with open(fp, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def main():
    bj = datetime.timezone(datetime.timedelta(hours=8))
    data = {
        "updated": datetime.datetime.now(bj).strftime("%Y-%m-%d %H:%M") + " 北京时间",
        "cn_index": fetch_cn_index(),
        "us_index": fetch_us_index(),
        "cn_sectors": fetch_cn_sectors(),
        "us_sectors": fetch_us_sectors(),
        "specialties": fetch_specialties(),
        "articles": load_articles(),
    }
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    for s in data["specialties"]:
        print(f'[{s["specialty"]}] {s["date"]} 条目{len(s["items"])} 标题:{s["title"][:40]}')

if __name__ == "__main__":
    main()
