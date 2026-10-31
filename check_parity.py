#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_parity.py —— 看板「模板一致性」自检

作用：把「美化模板 8 项要求」变成可执行的检查项，每次构建后跑一遍。
· 全部通过 → 打印 OK，退出码 0
· 有缺项   → 打印缺项清单，退出码 0（不阻塞发布，仅告警）

检查对象：build_site.py 生成的 site/ 目录
"""
import os
import re
import sys

SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")

CHECKS = [
    ("1 粘性章节导航", ["class=\"snav\"", "position:sticky", "data-t=", "@keyframes"], "index.html"),
    ("2 回到顶部按钮", ["id=\"toTop\"", "y>400"], "index.html"),
    ("3 更新时间徽章", ["class=\"live\"", "uxpulse", "class=\"rel\"", "data-bjtime"], "index.html"),
    ("4 涨跌箭头色块", ["class=\"pill up", "class=\"pill down", "class=\"ar\">▲", "class=\"ar\">▼"], "index.html"),
    ("5 卡片微交互", ["transform:translateY(-2px)", ".icard:hover"], "index.html"),
    ("6 表格斑马纹", ["nth-child(even)", "tbody tr:hover"], "index.html"),
    ("7 移动端与打印", ["@media(max-width:560px)", "@media print"], "index.html"),
    ("8 theme-color", ["name=\"theme-color\"", "#3f6b4f"], "index.html"),
]


def read(name):
    p = os.path.join(SITE, name)
    if not os.path.isfile(p):
        return ""
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def main():
    if not os.path.isdir(SITE):
        print("[parity] site/ 不存在，先运行 build_site.py")
        return 0
    total = fail = 0
    print("[parity] 模板一致性自检")
    for label, needles, page in CHECKS:
        html = read(page)
        missing = [n for n in needles if n not in html]
        total += 1
        if missing:
            fail += 1
            print(f"  ✗ {label}: 缺 {missing}")
        else:
            print(f"  ✓ {label}")

    # 周期美化增强层
    try:
        import beautify
        k, n, desc, _c, _j = beautify.current_pack()
        s, e = beautify.period_range()
        print(f"[parity] 本期视觉皮肤：[{k}] {n}（{s}~{e}），下次切换 {beautify.next_switch()}")
    except Exception as ex:
        print(f"[parity] 周期皮肤读取失败：{type(ex).__name__}: {ex}")

    # 各页 theme-color / 回顶覆盖
    for page in ("history.html", "index.html", "quiz.html", "xz/videos.html"):
        html = read(page)
        if not html:
            continue
        has_theme = 'name="theme-color"' in html
        has_top = 'id="toTop"' in html
        if not (has_theme and has_top):
            print(f"  ! {page}: theme_color={has_theme} 回顶={has_top}")

    print(f"[parity] 结论：{total - fail}/{total} 项通过" + ("" if fail == 0 else f"，{fail} 项待补"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
