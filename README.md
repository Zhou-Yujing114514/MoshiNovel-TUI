# 摩柿小说下载站 · 终端版 TUI (MoshiNovel-TUI)

摩拉克斯牌洋柿子小说下载站的命令行客户端，纯 Python 3.8+ 标准库实现，零第三方依赖，对接 `https://morax.kdns.fr`。

## 功能

- 🔍 搜索小说（书名 / 分享链接 / 书籍 ID）
- 📥 提交下载任务（TXT / EPUB / PDF）
- 📋 任务列表（我的提取 / 全站提取）、队列监控（watch）
- 📖 在线阅读（read 命令）
- 👤 登录 / 退出 / 当前用户
- 🏠 站点信息

## 安装与使用

```bash
# 无需安装，直接运行（需要 Python 3.8+）
python3 moshi_tui.py --help

# 搜索
python3 moshi_tui.py search 诡秘之主

# 提交下载（默认 txt）
python3 moshi_tui.py download 诡秘之主 epub

# 查看我的任务（5 秒自动刷新监控）
python3 moshi_tui.py watch

# 下载任务产物文件
python3 moshi_tui.py fetch 123

# 在线阅读
python3 moshi_tui.py read 123

# 登录
python3 moshi_tui.py login 用户名
```

命令一览：`search` `download` `tasks` `fetch` `watch` `preview` `read` `login` `logout` `whoami` `site`

## 相关项目

- 网页版：https://morax.kdns.fr
- iOS 原生版：https://github.com/Zhou-Yujing114514/MoshiNovel-iOS
- 虚空终端 TUI：https://github.com/Zhou-Yujing114514/VoidTerminal-TUI

## 更新日志

### v2.2.1（服务端 v1.0.0 → v2.2.1）
- 书源大幅扩充：mix_sources.json 由 13 个源（8 启用）增至 33 个源（23 启用 / 10 禁用），新增 20 个 legado 格式书源（壁落小说、蚂蚁阅读、顶点中文、天域小说、黑岩阅读网、笔趣阁8 等）
- 杂源引擎重构（mix.go 20KB→36KB）：集成 legado 书源格式支持；新增书名 / 作者从 li 块提取、搜索结果评分排序；新增硬过滤（分类名 / 章节名 / 标签名 / 色情内容拦截）；新增标题归一化、中文数字转整数、广告行识别与过滤统计
- 杂源下载并行化：worker 数 1 → 3，同一时间可处理 3 本不同书
- 14 个书源正则修复：book_url_pattern 精确锚定，解决分类名 / 章节名误收录问题
- 前端新增杂源工具：工具切换（番茄 / 杂源）、SSE 流式搜索（搜到一本显示一本）、杂源下载队列与番茄队列分离、搜索结果带源标签
- 新增 API：GET /api/mix/search（SSE 流式）、POST /api/mix/tasks、GET /dl-mix/{path}
- 新增工具：convert_legado.py（legado 书源转换脚本）、legado_work/（书源测试工作区）
- 页脚新增四生万物工作室官网链接
- 限流调整：每 IP 15 次 / 5 分钟（原 5 次 / 15 分钟）
- app 镜像已于 2026-09-16 07:29 重建

### v1.1.0
- 服务端书源扩充，可检索 / 可下载的书籍来源进一步增多
- 杂源搜索优化，提升杂源结果的相关性与响应稳定性
- 修复在线阅读章节接口，解决章节内容偶发解析失败
- 会话 Cookie 持久化到 `~/.config/moshi_tui/`（文件权限 600），下载文件名经净化处理

