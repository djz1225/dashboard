#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""考研西医综合（306）成套教学视频 抓取器

- 多关键词搜 B 站公开搜索 -> 只保留「成套 / 连续」的长系列（多分 P 或超长单集）
- 逐条取视频详情做有效性校验（失效 / 私密 / 稿件不可见自动剔除），统计分 P、总时长、播放
- 自动打标：科目（全程/生理/生化/病理/内科/外科/真题/带背）+ 主讲老师
- 输出 xz/videos.json；抓取失败或结果过少时保留旧文件，不覆盖好数据

纯标准库实现（urllib + http.cookiejar），可在 GitHub Actions 直接运行。
被 build_site.py import 时会调用 refresh()，实现看板每次构建自动更新。
"""
import json, os, re, sys, time, datetime, http.cookiejar, urllib.request, urllib.parse

OUT = os.path.dirname(os.path.abspath(__file__))
XZ = os.path.join(OUT, "xz")
JSON_PATH = os.path.join(XZ, "videos.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

KEYWORDS = [
    "西综考研 全程", "306西医综合", "西医综合 精讲", "西综 系统课", "西综 基础班",
    "西综 强化班", "贺银成 西医综合", "天天师兄 西综", "刘忠保 西综", "昭昭 西医综合",
    "西医综合 生理 精讲", "西医综合 生化 精讲", "西医综合 病理 精讲",
    "西医综合 内科学 精讲", "西医综合 外科学 精讲", "西医综合 诊断学",
    "西综 历年真题 精讲", "西综 冲刺 带背", "病理学 考研 精讲",
    "生物化学 考研 精讲", "外科学 考研 精讲", "内科学 十版 精讲",
    "病理学 十版 精讲", "生理学 十版 精讲", "徐琦 外科", "天天师兄 外科",
    "外科学 精读", "外科学全 精讲", "西医内科学 全讲", "外科 带读 考研",
]

SUBJECTS = ["全程系统课", "生理", "生化", "病理", "内科", "外科", "真题精讲", "冲刺带背"]
TEACHERS = ["贺银成", "天天师兄", "刘忠保", "昭昭", "徐琦", "唐子益", "马威", "侯英健",
            "小亮", "傲视天鹰", "隋准", "张蕴新", "李睿", "杨净", "王强", "王逸", "刘毓琳"]

# 非「考研西医综合（306）」的噪声：其他专业 / 其他考试 / 非考研场景
BAD = ["主治", "同等学力", "执业", "护理", "中医", "中药", "口腔", "规培", "住培",
       "专升本", "副高", "调剂", "期刊", "论文", "助产", "护士",
       "计算机", "408", "管综", "199管理", "教育综合", "333", "法硕", "心理学", "新传",
       "翻译硕士", "英语", "政治强化", "数学", "会计", "金融", "经济学", "体育", "艺术",
       "公卫", "预防医学", "兽医", "药学", "检验", "影像技术", "康复治疗",
       "王镜岩", "朱圣庚", "杨荣武", "338", "827", "生物专业", "生物考研", "求臻",
       "动物", "春考", "同力", "耳鼻咽喉", "妇产", "儿科", "眼科学", "皮肤性病",
       "期末", "助理医师", "医学教育网", "精品课", "全文逐字逐句", "听书",
       "事业单位", "综应", "公务员", "三支一扶", "转本", "对口"]

SUBJ_KEYS = [("内科", ["内科", "诊断学"]), ("外科", ["外科"]),
             ("病理", ["病理"]), ("生化", ["生化", "生物化学"]),
             ("生理", ["生理"])]


def relevant(title, parts=()):
    """相关性：必须指向考研西综/306，或带考研语境的医学五大科目课程。"""
    if any(b in title for b in BAD):
        return False
    if re.search(r"西综|西医综合|306|临床医学综合", title):
        return True
    txt = title + " " + " ".join(list(parts)[:6])
    subj = re.search(r"生理|生化|生物化学|病理|内科|外科|诊断", txt)
    ctx = re.search(r"考研|医学生|人卫|第十版|十版|第9版|第九版|考点|命题|真题"
                    r"|精讲|精读|带读|本科教学|合集|系统", title)
    return bool(subj and ctx)


# ---------------- HTTP（纯标准库，带 cookie） ----------------
_OPENER = None


def opener():
    global _OPENER
    if _OPENER is None:
        cj = http.cookiejar.CookieJar()
        _OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        _OPENER.addheaders = [("User-Agent", UA), ("Referer", "https://www.bilibili.com/"),
                              ("Accept", "application/json, text/plain, */*"),
                              ("Accept-Language", "zh-CN,zh;q=0.9")]
        try:  # 取 buvid3 等风控 cookie
            _OPENER.open("https://www.bilibili.com/", timeout=15).read()
        except Exception:
            pass
    return _OPENER


def api(path, params, retries=2):
    url = "https://api.bilibili.com" + path + "?" + urllib.parse.urlencode(params)
    last = None
    for i in range(retries):
        try:
            with opener().open(url, timeout=20) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            last = e
            time.sleep(1.2 * (i + 1))
    print(f"  [warn] api fail {path} {params.get('keyword') or params.get('bvid')}: "
          f"{type(last).__name__}", file=sys.stderr)
    return None


# ---------------- 文本与时间 ----------------
def fix_cover(u):
    u = (u or "").strip()
    if not u:
        return ""
    if u.startswith("//"):
        return "https:" + u
    return u.replace("http://", "https://")


def clean(t):
    t = re.sub(r"<[^>]+>", "", t or "")
    for a, b in (("&amp;", "&"), ("&quot;", '"'), ("&#39;", "'"), ("&lt;", "<"), ("&gt;", ">")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


def dur_seconds(d):
    try:
        parts = [int(x) for x in str(d).split(":")]
    except Exception:
        return 0
    sec = 0
    for p in parts:
        sec = sec * 60 + p
    return sec


def fmt_dur(sec):
    h, m = sec // 3600, (sec % 3600) // 60
    return f"{h}小时{m:02d}分" if h else f"{m}分钟"


def classify(title, parts):
    """先认阶段（真题 / 带背冲刺），再认科目，最后归全程系统课。"""
    txt = title + " " + " ".join(parts[:40])
    hit = {name for name, keys in SUBJ_KEYS if any(k in title for k in keys)}
    if "真题" in title or "历年" in title:
        sub = "真题精讲"
    elif any(k in title for k in ["冲刺", "押题", "带背", "抽背", "背诵", "磨耳朵", "速通", "串讲"]):
        sub = "冲刺带背"
    elif len(hit) == 1:
        sub = hit.pop()
    else:
        sub = "全程系统课"
    return sub, [t for t in TEACHERS if t in txt]


def search(kw, page=1):
    d = api("/x/web-interface/search/type",
            {"search_type": "video", "keyword": kw, "page": page, "order": "totalrank"})
    if not d or d.get("code") != 0:
        return []
    return (d.get("data") or {}).get("result") or []


def detail(bvid):
    d = api("/x/web-interface/view", {"bvid": bvid})
    if not d or d.get("code") != 0:
        return None
    return d.get("data")


# ---------------- 主流程 ----------------
def collect():
    cand = {}
    for kw in KEYWORDS:
        rs = search(kw, 1) + search(kw, 2)
        print(f"[search] {kw}: {len(rs)}")
        for r in rs:
            bv = r.get("bvid")
            title = clean(r.get("title"))
            if not bv or not title or not relevant(title):
                continue
            dur = dur_seconds(r.get("duration"))
            play = int(r.get("play") or 0)
            if dur < 1200 and play < 3000:      # 太短的散课先剔除
                continue
            cand[bv] = {"bvid": bv, "title": title, "up": r.get("author"),
                        "mid": r.get("mid"), "play": play,
                        "pubdate": int(r.get("pubdate") or 0),
                        "cover": fix_cover(r.get("pic")), "dur_hint": dur}
        time.sleep(0.6)

    print(f"[cand] {len(cand)} raw candidates")
    # 只校验最可能入选的候选，控制请求量与风控风险
    top = sorted(cand.values(), key=lambda x: (-x["play"], -x["dur_hint"]))[:130]

    items = []
    for c in top:
        bv = c["bvid"]
        d = detail(bv)
        time.sleep(0.3)
        if not d:                                  # 失效 / 私密 / 被删
            continue
        pages = d.get("pages") or []
        c["pages"] = len(pages) or int(d.get("videos") or 1)
        c["dur"] = int(d.get("duration") or c["dur_hint"])
        stat = d.get("stat") or {}
        c["play"] = int(stat.get("view") or c["play"])
        c["fav"] = int(stat.get("favorite") or 0)
        c["pubdate"] = int(d.get("pubdate") or c["pubdate"])
        c["title"] = clean(d.get("title") or c["title"])
        owner = d.get("owner") or {}
        c["up"] = owner.get("name") or c["up"]
        c["mid"] = owner.get("mid") or c["mid"]
        c["cover"] = fix_cover(d.get("pic")) or c["cover"]
        parts = [clean(p.get("part")) for p in pages if p.get("part")]
        c["parts"] = parts[:8]
        # 成套门槛：多分 P（≥10 集）或总时长 ≥4 小时
        if not (c["pages"] >= 10 or c["dur"] >= 4 * 3600):
            continue
        if not relevant(c["title"], parts):
            continue
        if not re.search(r"西综|西医综合|306|临床医学综合", c["title"]) and \
           not re.search(r"生理|生化|生物化学|病理|内科|外科|诊断",
                         c["title"] + " " + " ".join(parts[:6])):
            continue
        c["subject"], c["teachers"] = classify(c["title"], parts)
        c["url"] = f"https://www.bilibili.com/video/{bv}"
        c["date"] = datetime.datetime.utcfromtimestamp(c["pubdate"]).strftime("%Y-%m-%d")
        c["dur_txt"] = fmt_dur(c["dur"])
        c.pop("dur_hint", None)
        items.append(c)

    # 打分：成套度 + 总时长 + 播放 + 新鲜度，考研语境加权
    now = time.time()
    for it in items:
        fresh = max(0.0, 1 - max(0.0, (now - it["pubdate"]) / 86400) / 900)
        base = (2.2 * min(it["pages"], 120) / 120 +
                2.0 * min(it["dur"] / 3600, 60) / 60 +
                2.0 * min(it["play"] ** 0.5 / 700, 1) + 2.2 * fresh)
        t = it["title"]
        if re.search(r"西综|西医综合|306|临床医学综合", t):
            base += 0.45
        if re.search(r"考研|十版|第十版|人卫|命题|考点", t):
            base += 0.2
        if re.search(r"速成课|期末", t):
            base *= 0.8
        if re.search(r"本科教学", t):     # 本科公开课：内容扎实但非应试，轻降权
            base *= 0.86
        # 权威性加权：主流名师 / 知名机构主讲的上榜优先
        if it["teachers"]:
            base += 0.25
        it["score"] = round(base, 3)

    # 去重：同一套课被多方搬运时，按「前 8 个分 P 名」为指纹只留播放最高者
    def norm(t):
        return re.sub(r"[【】\[\]（）()\s|/、，,。·\-—_]+", "", t)

    best = {}
    for it in sorted(items, key=lambda x: (-x["play"], -x["score"])):
        sig = norm("".join(it["parts"][:8]))[:70]
        key = sig if len(sig) >= 12 else norm(it["title"])[:26] + str(it["pages"])
        best.setdefault(key, it)

    # 分科配额：保证各科都有位置，避免长真题/带背挤掉系统课
    QUOTA = {"全程系统课": 14, "内科": 12, "外科": 12, "生理": 10, "生化": 10,
             "病理": 10, "真题精讲": 8, "冲刺带背": 8}
    picked, used = [], {}
    for it in sorted(best.values(), key=lambda x: (-x["score"], -x["play"])):
        s = it["subject"]
        if used.get(s, 0) >= QUOTA.get(s, 8):
            continue
        used[s] = used.get(s, 0) + 1
        picked.append(it)
    return picked[:70]


def refresh(verbose=True, max_age_hours=6):
    """抓取并写盘；成功返回条数，失败返回 0（旧文件保持不动）。
    若 videos.json 在 max_age_hours 内刚更新过，直接跳过，避免重复抓取。"""
    if max_age_hours and os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, encoding="utf-8") as f:
                old = json.load(f)
            ts = datetime.datetime.strptime(old.get("updated", ""), "%Y-%m-%d %H:%M")
            age = (datetime.datetime.now() - ts).total_seconds() / 3600
            if 0 <= age < max_age_hours:
                print(f"[xz-videos] 数据 {age:.1f} 小时前刚刷新，跳过本轮")
                return old.get("total", 0)
        except Exception:
            pass
    try:
        items = collect()
    except Exception as e:
        print(f"[xz-videos] 抓取异常，沿用旧数据: {type(e).__name__}: {e}")
        return 0
    if len(items) < 5:
        print(f"[xz-videos] 仅 {len(items)} 条，低于阈值，沿用旧数据")
        return 0
    data = {
        "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "哔哩哔哩（公开搜索 + 视频详情有效性校验）",
        "total": len(items),
        "subjects": SUBJECTS,
        "items": items,
    }
    os.makedirs(XZ, exist_ok=True)
    tmp = JSON_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, JSON_PATH)
    if verbose:
        print(f"[xz-videos] 写入 {JSON_PATH}: {len(items)} 套")
        for it in items[:8]:
            print(f"  {it['score']:<5} {it['subject']:<6} {it['pages']:>3}P "
                  f"{it['dur_txt']:<9} {it['title'][:40]}")
    return len(items)


def main():
    # 命令行手动执行时强制刷新（max_age=0）
    return 0 if refresh(max_age_hours=0) >= 5 else 1


if __name__ == "__main__":
    sys.exit(main())
