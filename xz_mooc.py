#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全网多源课程抓取：中国大学 MOOC（icourse163）+ 学堂在线（xuetangx）

两者均为公开搜索接口，无需登录：
- MOOC：先 GET 首页取 NTESSTUDYSI cookie，再 POST searchCourse.rpc（form 表单，mocCourseQueryVo=JSON）
- 学堂在线：POST /api/v1/lms/get_product_list/?page=N，body JSON，需 header xtbz=xt

统一输出结构，供 xz_videos 合并：
{source, title, url, school, teachers[], learners, cover, date, subject}
"""
import json, re, time, datetime, urllib.request, urllib.parse, http.cookiejar

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

MOOC_KEYWORDS = ["内科学", "诊断学", "生理学", "外科学", "病理学", "生物化学",
                 "西医综合", "临床医学", "外科学总论", "内科学各系统"]
XT_KEYWORDS = ["内科学", "诊断学", "生理学", "外科学", "病理学", "生物化学",
               "西医综合", "临床医学"]

# 医学生本科主干课白名单（用于过滤中医/兽医/植物等干扰）
GOOD_SUBJ = ["内科学", "诊断学", "生理学", "外科学", "病理学", "生物化学", "药理学",
             "医学免疫学", "人体解剖学", "组织学", "医学微生物学", "临床医学",
             "西医综合", "循证医学", "医学统计学", "神经病学", "传染病学"]
BAD_WORDS = ["中医", "中药", "兽医", "植物", "动物", "心理", "护理", "口腔", "针灸",
             "推拿", "药理(中药)", "康复治疗", "药学", "检验技术", "影像技术",
             "公共卫生事业", "卫生事业管理", "食品", "农业", "林业", "畜牧"]

SUBJ_MAP = [("诊断", ["诊断学", "诊断"]), ("内科", ["内科学", "内科"]),
            ("外科", ["外科学", "外科"]), ("病理", ["病理学", "病理"]),
            ("生化", ["生物化学", "生化"]), ("生理", ["生理学", "生理"])]


def _get(url, hdr=None, timeout=25):
    req = urllib.request.Request(url, headers=hdr or {"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _post(url, data, hdr=None, timeout=25):
    h = {"User-Agent": UA}
    if hdr:
        h.update(hdr)
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def classify(title):
    for name, keys in SUBJ_MAP:
        if any(k in title for k in keys):
            return name
    return "全程系统课"


def relevant(title):
    if any(b in title for b in BAD_WORDS):
        return False
    return any(g in title for g in GOOD_SUBJ)


def ts_ms_to_date(ms):
    try:
        return datetime.datetime.utcfromtimestamp(int(ms) / 1000).strftime("%Y-%m-%d")
    except Exception:
        return ""


# ---------------- 中国大学 MOOC ----------------
def fetch_mooc(keywords=None, page_size=20):
    keywords = keywords or MOOC_KEYWORDS
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA)]
    try:
        op.open("https://www.icourse163.org/", timeout=20).read()
    except Exception as e:
        print(f"  [mooc] 首页失败 {e}")
        return []
    csrf = next((c.value for c in cj if c.name.upper().startswith("NTES")), "")
    if not csrf:
        print("  [mooc] 未取到 csrf")
        return []

    out, seen = [], set()
    for kw in keywords:
        vo = json.dumps({"keyword": kw, "pageIndex": 1, "highlight": True, "orderBy": 0,
                         "stats": 30, "pageSize": page_size, "prodectType": 1},
                        ensure_ascii=False)
        try:
            body = urllib.parse.urlencode({"mocCourseQueryVo": vo}).encode()
            # 必须复用带 cookie 的 opener，否则被判「非法跨域请求」
            req = urllib.request.Request(
                "https://www.icourse163.org/web/j/mocSearchBean.searchCourse.rpc"
                f"?csrfKey={csrf}", data=body,
                headers={"User-Agent": UA,
                         "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                         "Referer": "https://www.icourse163.org/search.htm",
                         "Origin": "https://www.icourse163.org",
                         "X-Requested-With": "XMLHttpRequest",
                         "Accept": "application/json"})
            txt = op.open(req, timeout=25).read().decode("utf-8", "replace")
            lst = (json.loads(txt).get("result") or {}).get("list") or []
        except Exception as e:
            print(f"  [mooc] {kw} 失败 {type(e).__name__}")
            continue
        print(f"[mooc] {kw}: {len(lst)}")
        for it in lst:
            d = (it.get("mocCourseCard") or {}).get("mocCourseCardDto") or {}
            if not d:
                continue
            name = (d.get("name") or "").strip()
            if not name or not relevant(name):
                continue
            tp = d.get("termPanel") or {}
            term_id = tp.get("id")
            short = d.get("shortName") or ""
            if not term_id or not short:
                continue
            url = f"https://www.icourse163.org/course/{short}-{term_id}"
            if url in seen:
                continue
            seen.add(url)
            lects = [p.get("realName") or p.get("nickName") or ""
                     for p in (tp.get("lectorPanels") or [])][:4]
            school = (d.get("schoolPanel") or {}).get("name") or ""
            out.append({
                "source": "中国大学MOOC",
                "title": name,
                "url": url,
                "school": school,
                "teachers": [x for x in lects if x],
                "learners": int(d.get("learnerCount") or tp.get("enrollCount") or 0),
                "cover": d.get("imgUrl") or "",
                "date": ts_ms_to_date(d.get("firstPublishTime") or tp.get("startTime")),
                "subject": classify(name),
                "kind": "mooc",
            })
        time.sleep(0.5)
    return out


# ---------------- 学堂在线 ----------------
def fetch_xuetangx(keywords=None, pages=2):
    keywords = keywords or XT_KEYWORDS
    out, seen = [], set()
    for kw in keywords:
        for pno in range(1, pages + 1):
            body = json.dumps({"query": kw, "chief_org": [], "classify": [],
                               "selling_type": [], "status": [], "appid": 10000},
                              ensure_ascii=False).encode()
            try:
                txt = _post(f"https://www.xuetangx.com/api/v1/lms/get_product_list/?page={pno}",
                            body, {"Content-Type": "application/json", "xtbz": "xt",
                                   "Referer": "https://www.xuetangx.com/"})
                lst = (json.loads(txt).get("data") or {}).get("product_list") or []
            except Exception as e:
                print(f"  [xt] {kw} p{pno} 失败 {type(e).__name__}")
                break
            if pno == 1:
                print(f"[xt] {kw}: 命中")
            for it in lst:
                name = (it.get("name") or "").strip()
                if not name or not relevant(name):
                    continue
                sign = it.get("sign") or ""
                if not sign or sign in seen:
                    continue
                seen.add(sign)
                tchs = [t.get("name", "") for t in (it.get("teacher") or [])][:4]
                school = ""
                for t in (it.get("teacher") or []):
                    if t.get("org_name"):
                        school = t["org_name"]
                        break
                out.append({
                    "source": "学堂在线",
                    "title": name,
                    "url": f"https://www.xuetangx.com/course/{sign}",
                    "school": school,
                    "teachers": [x for x in tchs if x],
                    "learners": int(it.get("enroll_num_v4") or it.get("enroll_play_num") or 0),
                    "cover": it.get("cover") or "",
                    "date": ts_ms_to_date(it.get("created")),
                    "subject": classify(name),
                    "kind": "mooc",
                })
            time.sleep(0.4)
    return out


def fetch_all():
    items = []
    for name, fn in (("中国大学MOOC", fetch_mooc), ("学堂在线", fetch_xuetangx)):
        try:
            got = fn()
            print(f"[{name}] 入库 {len(got)} 套")
            items += got
        except Exception as e:
            print(f"[{name}] 整体失败 {type(e).__name__}: {e}")
    # 去重：同名课程只留一个来源
    best = {}
    for it in items:
        key = re.sub(r"[【】\[\]（）()\s]+", "", it["title"])[:20]
        if key not in best or it["learners"] > best[key]["learners"]:
            best[key] = it
    return list(best.values())


if __name__ == "__main__":
    got = fetch_all()
    print(f"共 {len(got)} 套")
    for it in sorted(got, key=lambda x: -x["learners"])[:20]:
        print(f"  {it['source']:<10} {it['subject']:<5} {it['learners']:>7} "
              f"{it['school'][:12]:<14} {it['title'][:26]}")
    with open("/tmp/mooc_courses.json", "w", encoding="utf-8") as f:
        json.dump(got, f, ensure_ascii=False, indent=1)
