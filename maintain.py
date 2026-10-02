#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""看板维护：校验文章链接、去重排序、重建网站"""
import json, os, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "articles.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
ORDER = {"肾内科": 0, "内分泌·体重管理": 1, "心血管": 2}

def check_url(u):
    last = ""
    for method in ("GET", "HEAD"):
        try:
            req = urllib.request.Request(u, method=method, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308, 403, 405, 429):
                return e.code  # 重定向/受保护，链接本身有效
            last = f"HTTP {e.code}"
        except Exception as e:
            last = str(e)[:50]
    return last

def is_ok(st):
    return (isinstance(st, int) and (st < 400 or st in (301, 302, 303, 307, 308, 403, 405, 429)))

def main():
    if not os.path.exists(ART):
        print("articles.json 不存在"); return
    with open(ART, encoding="utf-8") as f:
        arts = json.load(f)
    # 去重：同标题保留日期最新
    seen = {}
    for a in arts:
        k = a.get("title", "").strip()
        if k not in seen or a.get("date", "") > seen[k].get("date", ""):
            seen[k] = a
    arts = list(seen.values())
    # 校验链接
    ok = bad = 0
    for a in arts:
        u = a.get("url", "")
        if u:
            st = check_url(u)
            a["url_status"] = st
            if isinstance(st, int) and st < 400:
                ok += 1
            else:
                bad += 1
    # 排序：专科升序 + 组内日期降序
    arts.sort(key=lambda x: x.get("date", ""), reverse=True)
    arts.sort(key=lambda x: ORDER.get(x.get("specialty", ""), 9))
    with open(ART, "w", encoding="utf-8") as f:
        json.dump(arts, f, ensure_ascii=False, indent=2)
    print(f"文章共 {len(arts)} 篇；链接正常 {ok}，异常 {bad}")
    for a in arts:
        if not (isinstance(a.get("url_status"), int) and a["url_status"] < 400):
            print("  [异常]", a.get("url_status"), "|", a.get("title", "")[:40], "|", a.get("url", "")[:60])
    os.system(f"python3 {os.path.join(HERE, 'fetch_data.py')} >/dev/null 2>&1")
    os.system(f"python3 {os.path.join(HERE, 'build_site.py')}")

if __name__ == "__main__":
    main()
