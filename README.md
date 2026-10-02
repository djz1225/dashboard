# 每日追踪看板 · 云部署（GitHub Pages 免费方案）

部署完成后你会得到一个**固定公网网址**（形如 `https://你的用户名.github.io/仓库名/`），
并且**每天北京时间 14:00 自动更新**，无需任何人工操作、无需服务器。

---

## 一、准备工作
1. 注册一个免费 **GitHub** 账号：https://github.com
2. 安装 **Git**（或用网页上传，见下）。

## 二、创建仓库并上传
1. 在 GitHub 新建仓库（New repository），例如命名 `dashboard`，**设为 Public**。
2. 把本目录（deploy 内所有文件，**含隐藏的 `.github` 文件夹**）上传到仓库：
   - 网页方式：Add file → Upload files → 拖入所有文件与文件夹 → Commit。
   - 命令行方式：
     ```bash
     git init
     git add .
     git commit -m "init dashboard"
     git branch -M main
     git remote add origin https://github.com/你的用户名/dashboard.git
     git push -u origin main
     ```

## 三、开启 Pages 与自动部署
1. 进仓库 **Settings → Pages**，将 **Source** 设为 **GitHub Actions**。
2. 进仓库 **Settings → Actions → General**，确认 **Workflow permissions** 可写、允许 Actions 运行。
3. 进 **Actions** 标签 → 选择 `update-dashboard` → 点 **Run workflow** 手动跑一次。
4. 跑完后在 **Settings → Pages** 顶部会显示你的网址：
   **`https://你的用户名.github.io/dashboard/`** —— 这就是你的固定看板网址。

## 四、日常
- **全自动**：`update.yml` 每天 UTC 06:00（北京 14:00）自动抓数据、重建、发布。
- **手动更新**：在 Actions 页点 `Run workflow`。
- **更新文章**：编辑 `articles.json`（或把新的对比提要 md 放进 `specialties/`）后提交，Actions 会自动重建。
- **改样式**：编辑 `build_site.py` 提交即可。

## 五、文件说明
| 文件 | 作用 |
|------|------|
| `fetch_data.py` | 抓 A股/美股行情 + 解析 `specialties/` 提要 → `data.json` |
| `build_site.py` | 生成网站 → `site/`（部署目录）|
| `maintain.py` | 校验 `articles.json` 链接、去重、重建 |
| `articles.json` | 三专科发表文章（标题/要点/原文链接）|
| `specialties/` | 三专科每日对比提要（md，供看板解析）|
| `.github/workflows/update.yml` | 定时任务 + 自动部署 |

## 六、可选：其他云平台
- **Cloudflare Pages** / **Vercel**：同样支持"静态托管 + 定时任务"，把 `site/` 发布、用其 Cron 触发 `fetch_data.py && build_site.py` 即可。
- **自有服务器**：`crontab` 加 `0 14 * * * cd 项目 && python3 fetch_data.py && python3 build_site.py`，用 Nginx 指向 `site/`。

> 数据来源：新浪财经；仅供学习参考，不构成投资或诊疗建议。
