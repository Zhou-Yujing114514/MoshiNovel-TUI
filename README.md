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
