#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日看板数据抓取 v2：A股/美股指数 + 板块涨跌榜 + 三专科结构化提要"""
import json, os, re, sys, time, datetime, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = ROOT
SEARCH_DIRS = [os.path.join(ROOT, "specialties"), ROOT, "/sandbox/workspace/outputs"]
SITE = os.path.join(OUT, "site")

def http_get(url, decode="utf-8", referer=None, retries=2):
    """带重试的 GET；失败抛异常，由调用方决定降级"""
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            if referer:
                req.add_header("Referer", referer)
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode(decode, errors="replace")
        except Exception as e:
            last = e
            time.sleep(0.8 * (i + 1))
    raise last


def http_get_safe(url, decode="utf-8", referer=None):
    """失败返回 None，不抛异常"""
    try:
        return http_get(url, decode, referer)
    except Exception as e:
        print(f"  [warn] GET failed: {url[:70]} ({type(e).__name__})")
        return None


# ---------- 行情数据源：腾讯为主动，新浪为备 ----------
def q_tencent(codes):
    """腾讯行情 qt.gtimg.cn —— 返回 {code: fields[]}"""
    txt = http_get_safe("https://qt.gtimg.cn/q=" + ",".join(codes), "gbk")
    if not txt:
        return {}
    out = {}
    for line in txt.splitlines():
        if '="' not in line:
            continue
        key = line.split('="')[0].replace('v_', '').strip()
        val = line.split('="')[1].rstrip('";')
        out[key] = val.split('~')
    return out


def q_sina_http(codes, referer="https://finance.sina.com.cn"):
    """新浪行情 http 版（https 已 403）—— 备用源"""
    txt = http_get_safe("http://hq.sinajs.cn/list=" + ",".join(codes), "gbk", referer)
    if not txt:
        return {}
    out = {}
    for line in txt.splitlines():
        m = re.search(r'hq_str_([^=]+)="([^"]*)"', line)
        if m:
            out[m.group(1)] = m.group(2).split(",")
    return out

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
    meta = {"sh000001": "上证指数", "sz399001": "深证成指", "sz399006": "创业板指", "sh000300": "沪深300"}
    res = []
    # 主源：腾讯
    d = q_tencent(list(meta.keys()))
    for code, nm in meta.items():
        f = d.get(code)
        if not f or len(f) < 33:
            continue
        try:
            cur, pct = float(f[3]), float(f[32])
        except Exception:
            continue
        res.append({"name": nm, "price": round(cur, 2), "pct": round(pct, 2)})
    if res:
        return res
    # 备源：新浪
    print("  [cn_index] 腾讯源不可用，切换新浪")
    d = q_sina_http(list(meta.keys()))
    for code, nm in meta.items():
        f = d.get(code)
        if not f or len(f) < 4:
            continue
        try:
            prev, cur = float(f[2]), float(f[3])
            pct = (cur - prev) / prev * 100 if prev else 0
        except Exception:
            continue
        res.append({"name": nm, "price": round(cur, 2), "pct": round(pct, 2)})
    return res

def fetch_cn_sectors():
    txt = http_get_safe("https://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php", "gbk")
    if not txt:
        print("  [cn_sectors] 板块接口不可用，返回空")
        return {"up": [], "down": []}
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
    meta = {"usDJI": "道琼斯", "usIXIC": "纳斯达克", "usINX": "标普500"}
    res = []
    # 主源：腾讯
    d = q_tencent(list(meta.keys()))
    for code, nm in meta.items():
        f = d.get(code)
        if not f or len(f) < 33:
            continue
        try:
            cur, pct = float(f[3]), float(f[32])
        except Exception:
            continue
        res.append({"name": nm, "price": round(cur, 2), "pct": round(pct, 2)})
    if res:
        return res
    # 备源：新浪
    print("  [us_index] 腾讯源不可用，切换新浪")
    sina_meta = {"gb_$dji": "道琼斯", "gb_$ixic": "纳斯达克", "gb_$inx": "标普500"}
    d = q_sina_http(list(sina_meta.keys()))
    for code, nm in sina_meta.items():
        f = d.get(code)
        if not f or len(f) < 3:
            continue
        try:
            cur, pct = float(f[1]), float(f[2])
        except Exception:
            continue
        res.append({"name": nm, "price": round(cur, 2), "pct": round(pct, 2)})
    return res

US_ETF_TENCENT = {"usXLK": "科技", "usXLE": "能源", "usXLF": "金融", "usXLV": "医疗",
                  "usXLY": "非必需消费", "usXLP": "必需消费", "usXLI": "工业",
                  "usXLB": "材料", "usXLU": "公用事业", "usXLRE": "房地产", "usXLC": "通信服务"}

def fetch_us_sectors():
    rows = []
    # 主源：腾讯
    d = q_tencent(list(US_ETF_TENCENT.keys()))
    for code, nm in US_ETF_TENCENT.items():
        f = d.get(code)
        if not f or len(f) < 33:
            continue
        try:
            pct = float(f[32])
        except Exception:
            continue
        rows.append({"name": nm, "pct": round(pct, 2)})
    # 备源：新浪
    if not rows:
        print("  [us_sectors] 腾讯源不可用，切换新浪")
        d = q_sina_http(list(US_SECTORS.keys()))
        for code, nm in US_SECTORS.items():
            f = d.get(code)
            if not f or len(f) < 3:
                continue
            try:
                pct = float(f[2])
            except Exception:
                continue
            rows.append({"name": nm, "pct": round(pct, 2)})
    rows.sort(key=lambda x: x["pct"], reverse=True)
    if not rows:
        return {"up": [], "down": []}
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

def _md_title(md):
    for ln in md.splitlines():
        if ln.startswith("## 主标题"):
            return ln.split("：", 1)[-1].strip().lstrip("：").strip()
    return ""

def _key_from_name(fn):
    """历史归档用文件名前缀定专科，比正文关键词更可靠（正文常提到其他专科）。"""
    if fn.startswith("肾内科"):
        return "肾内科", "肾内科"
    if fn.startswith("内分泌"):
        return "内分泌", "内分泌·体重管理"
    if fn.startswith("心血管"):
        return "心血管", "心血管"
    return None, None

def fetch_specialty_history():
    """收集每科所有日期的提要（仅元信息 + md 全文用于建页），按日期倒序。
    只扫描仓库内目录（specialties/ 与根目录），避免把外部临时目录里的
    十日串联记忆卡等非每日提要文件混入历史。
    输出：{"肾内科": [{"date","title","file"}, ...], ...}"""
    seen = {}
    repo_dirs = [os.path.join(ROOT, "specialties"), ROOT]
    for base in repo_dirs:
        if not os.path.isdir(base):
            continue
        for fn in sorted(os.listdir(base)):
            if not fn.lower().endswith(".md"):
                continue
            if any(x in fn for x in ["记忆卡", "串联", "quiz"]):
                continue
            fp = os.path.join(base, fn)
            try:
                with open(fp, encoding="utf-8", errors="replace") as f:
                    md = f.read()
            except Exception:
                continue
            key, _disp = _key_from_name(fn)
            if not key:
                key, _disp = _guess_specialty(md)
            if not key:
                continue
            dt = _file_date(fp, md)
            k = (key, dt.isoformat())
            if k in seen:
                continue
            seen[k] = {"date": dt.isoformat(), "title": _md_title(md), "file": fn}
    hist = {}
    for key, _disp in SPECS:
        rows = [v for (kk, _d), v in seen.items() if kk == key]
        rows.sort(key=lambda x: x["date"], reverse=True)
        hist[key] = rows
    return hist

def load_articles():
    fp = os.path.join(OUT, "articles.json")
    if os.path.exists(fp):
        try:
            with open(fp, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def _safe(fn, default, label):
    """单项失败不影响整体构建"""
    try:
        r = fn()
        return r if r is not None else default
    except Exception as e:
        print(f"  [ERROR] {label} 抓取失败: {type(e).__name__}: {str(e)[:100]}")
        return default


def main():
    bj = datetime.timezone(datetime.timedelta(hours=8))
    data = {
        "updated": datetime.datetime.now(bj).strftime("%Y-%m-%d %H:%M") + " 北京时间",
        "cn_index": _safe(fetch_cn_index, [], "A股指数"),
        "us_index": _safe(fetch_us_index, [], "美股指数"),
        "cn_sectors": _safe(fetch_cn_sectors, {"up": [], "down": []}, "A股板块"),
        "us_sectors": _safe(fetch_us_sectors, {"up": [], "down": []}, "美股板块"),
        "specialties": _safe(fetch_specialties, [], "三专科提要"),
        "specialty_history": _safe(fetch_specialty_history, {}, "专科历史"),
        "articles": _safe(load_articles, [], "文章列表"),
    }
    # 数据完整性提示（不阻断构建）
    if not data["cn_index"] and not data["us_index"]:
        print("  [WARN] 指数数据全部为空，页面将显示'暂无数据'")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    for s in data["specialties"]:
        print(f'[{s["specialty"]}] {s["date"]} 条目{len(s["items"])} 标题:{s["title"][:40]}')
    for k, rows in data["specialty_history"].items():
        print(f"[history] {k}: {len(rows)} 篇 ({rows[-1]['date'] if rows else '-'} ~ {rows[0]['date'] if rows else '-'})")

if __name__ == "__main__":
    main()
