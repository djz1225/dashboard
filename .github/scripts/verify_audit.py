#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI 侧审计校验：仓库中的提要必须持有有效的审校凭证。
在 GitHub Actions 上运行，运行环境不在助手控制范围内。
"""
import hashlib, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = os.path.join(ROOT, "specialties")

def sha12(p):
    return hashlib.sha1(open(p, "rb").read()).hexdigest()[:12]

def main():
    if not os.path.isdir(SPEC):
        print("无 specialties 目录，跳过"); return 0
    import datetime
    # 只校验「文件名含当日日期」的提要：历史存量无凭证属既成事实，不追溯
    all_mds = sorted(f for f in os.listdir(SPEC) if f.endswith(".md"))
    today = datetime.datetime.utcnow().strftime("%Y%m%d")
    mds = [f for f in all_mds if today in f]
    if not mds:
        print(f"今日（{today}）无提要文件，仅校验审计链")

    fail = []
    print(f"检查 {len(mds)} 份提要\n")
    for f in mds:
        p = os.path.join(SPEC, f)
        rec_p = p + ".review.json"
        # 1) 凭证存在且为 pass
        if not os.path.exists(rec_p):
            fail.append(f"{f}：缺审校凭证（.review.json）")
            print(f"✗ {f}  缺凭证")
            continue
        rec = json.load(open(rec_p, encoding="utf-8"))
        if rec.get("status") != "pass":
            fail.append(f"{f}：审校状态为 {rec.get('status')}")
            print(f"✗ {f}  状态 {rec.get('status')}")
            continue
        # 2) 指纹匹配（文件未被审校后篡改）
        if rec.get("content_sha") != sha12(p):
            fail.append(f"{f}：指纹不符（审校后被改动）")
            print(f"✗ {f}  指纹不符")
            continue
        # 3) 内容底线
        t = open(p, encoding="utf-8", errors="replace").read()
        bad = []
        if "\ufffd" in t:
            bad.append("含乱码")
        for u in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', t):
            if not u.startswith("http"):
                bad.append(f"图片非公网：{u[:30]}")
        rows = max((b.count("\n") for b in re.findall(r'((?:^\|.*\|\s*$\n)+)', t, re.M)), default=0)
        if rows > 12:
            bad.append(f"单表 {rows} 行 >12")
        if bad:
            fail.append(f"{f}：" + "；".join(bad))
            print(f"✗ {f}  " + "；".join(bad))
        else:
            print(f"✓ {f}  pass，指纹 {rec.get('content_sha')}")

    # 4) 审计链完整性
    log = os.path.join(ROOT, "audit", "audit.log.jsonl")
    if os.path.exists(log):
        prev, n, bad = "GENESIS", 0, 0
        for line in open(log, encoding="utf-8"):
            if not line.strip():
                continue
            rec = json.loads(line)
            body = json.dumps({k: rec[k] for k in rec if k != "hash"},
                              ensure_ascii=False, sort_keys=True)
            want = hashlib.sha1((rec["prev"] + body).encode()).hexdigest()[:16]
            if rec["prev"] != prev or rec["hash"] != want:
                bad += 1
            prev = rec["hash"]; n += 1
        print(f"\n审计链 {n} 条，{'完整' if bad == 0 else f'{bad} 处异常'}")
        if bad:
            fail.append(f"审计链 {bad} 处断裂")
    else:
        print("\n无审计日志（首次运行可为空）")

    print()
    if fail:
        print("FAIL —— 以下问题须修复后重新推送：")
        for x in fail:
            print("  - " + x)
        return 1
    print("PASS —— 全部提要持有有效审校凭证，可利用此构建")
    return 0

if __name__ == "__main__":
    sys.exit(main())
