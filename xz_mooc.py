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

# 第二轮「双一流」建设高校（节选常见校名，用于院校层次排序）
DOUBLE_FIRST = {
    "北京大学", "清华大学", "浙江大学", "南京大学", "武汉大学", "中山大学", "东南大学",
    "华中科技大学", "西安交通大学", "山东大学", "中南大学", "郑州大学", "苏州大学",
    "北京师范大学", "西北农林科技大学", "南京医科大学", "天津医科大学",
    "南京中医药大学", "广州中医药大学", "成都中医药大学", "南京林业大学",
    "北京体育大学", "复旦大学", "上海交通大学", "四川大学", "同济大学", "南开大学",
    "厦门大学", "吉林大学", "中国科学技术大学", "哈尔滨工业大学", "首都师范大学",
}
# 高职高专（职业院校 / 高等专科学校）
VOC_KEYS = ["职业技术学院", "职业学院", "高等专科学校", "专科学校", "卫生学校",
            "职业大学", "高等职业学校"]

TIER_LABEL = {1: "双一流", 2: "本科院校", 3: "高职高专", 4: "网络平台"}


def tier_of(school):
    """1=双一流 2=普通本科 3=高职高专"""
    s = (school or "").strip()
    if not s:
        return 2
    if any(k in s for k in VOC_KEYS):
        return 3
    for u in DOUBLE_FIRST:
        if u in s:
            return 1
    return 2


# ---------- 306 临床医学综合能力（西医）考纲科目判定 ----------
# 考纲五门：生理学、生物化学、病理学、内科学（含诊断学）、外科学
CORE_RULES = [
    ("病理", ["病理"], ["肿瘤病理", "分子病理", "病理技术"]),
    ("生理", ["生理"], ["运动生理", "植物生理", "动物生理", "生理学基础)",
                         "病理生理"]),
    ("生化", ["生物化学", "生化"], ["实验", "植物", "动物", "食品", "工业"]),
    ("内科", ["内科学", "内科"], ["小儿内科", "儿科", "中西医", "中医", "康复"]),
    ("外科", ["外科学", "外科"], ["小儿外科", "儿科", "中西医", "中医", "护理"]),
    ("诊断", ["诊断学"], ["影像诊断", "放射诊断", "超声诊断", "检验诊断", "中医诊断",
                          "心理诊断", "儿科影像", "实验诊断"]),
]
# 明确不在 306 考纲内的课程
OFF_SYLLABUS = ["解剖", "药理学", "医学统计", "卫生统计", "传染病学", "流行病学",
                "医学影像学", "影像学", "耳鼻咽喉", "妇产科", "妇科学", "产科学",
                "儿科学", "眼科学", "皮肤性病", "精神病学", "神经病学", "核医学",
                "沟通", "英语", "导论", "概论", "概要", "护理", "口腔", "中医",
                "针灸", "推拿", "康复", "营养", "卫生事业", "医学伦理", "医患",
                "研讨会", "成立大会", "论坛", "蓝皮书", "思政", "人文", "文献检索"]
# 属考纲科目下的专题分支（可看，但非系统全程课）
SUB_TOPIC = ["胸外", "神经外", "血管外", "肝胆胰", "微创", "烧伤", "泌尿外",
             "骨科学", "肿瘤病理", "临床技能", "前沿", "进展", "黑科技", "整合课程",
             "病例分析", "实验", "结构生物化学", "高级生物化学", "分子病理",
             "重力生理", "航天生理"]


def exam_level(title):
    """返回 (level, 说明)。level: core=考纲核心系统课 / sub=考纲专题分支 / no=不在考纲
    另返回 subject_hint（用于归类）。"""
    t = title or ""
    hit_subj = None
    for subj, keys, excludes in CORE_RULES:
        if any(k in t for k in keys):
            if any(e in t for e in excludes):
                continue
            hit_subj = subj
            break
    if any(k in t for k in OFF_SYLLABUS) and not hit_subj:
        return "no", "非306考纲科目", None
    if not hit_subj:
        return "no", "非306考纲科目", None
    if any(k in t for k in SUB_TOPIC):
        return "sub", "考纲专题分支", hit_subj
    return "core", "考纲核心科目", hit_subj


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
                "school_clean": school,
                "tier": tier_of(school),
                "exam": exam_level(name)[0],
                "exam_note": exam_level(name)[1],
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
                    "school_clean": school,
                    "tier": tier_of(school),
                    "exam": exam_level(name)[0],
                    "exam_note": exam_level(name)[1],
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
