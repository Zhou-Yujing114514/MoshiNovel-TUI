#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""摩柿小说下载站 (MoshiNovel) 终端版 TUI

对标 VoidTerminal-TUI：命令行小说搜索 / 任务 / 下载 / 在线阅读。
用法：
    python3 moshi_tui.py
依赖：仅 Python 3.8+ 标准库（urllib / json / http.cookiejar）。
"""
import argparse
import getpass
import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

__version__ = "2.2.1"

BASE_URL = os.environ.get("MOSHI_BASE_URL", "https://morax.kdns.fr")


def _sanitize_filename(name):
    """把服务端返回的书名净化为安全的本地文件名：
    - 只取 basename（去掉目录成分 / 盘符）
    - 过滤 .. 、路径分隔符、非法字符
    """
    s = (name or "book").strip()
    # 统一分隔符并只取最后一段，避免 ../ 或 绝对路径
    s = s.replace("\\", "/")
    if "/" in s:
        s = s.split("/")[-1]
    # 去掉 Windows 盘符前缀
    if len(s) >= 2 and s[1] == ":":
        s = s[2:]
    # 替换非法字符
    for ch in '\\/:*?"<>|':
        s = s.replace(ch, "_")
    # 折叠 ..
    s = s.replace("..", "_")
    # 去掉前导点/空格
    s = s.lstrip(" .")
    return s or "book"

# 颜色（终端支持时启用）
def _c(code):
    if sys.stdout.isatty():
        return f"\033[{code}m"
    return ""

RESET = _c(0)
BOLD = _c(1)
DIM = _c(2)
CYAN = _c(36)
GREEN = _c(32)
YELLOW = _c(33)
RED = _c(31)
BLUE = _c(34)

# 会话
_opener = None
_cookie_jar = None
_current_user = None


def _cookie_path():
    cfg = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
        os.path.expanduser("~"), ".config")
    return os.path.join(cfg, "moshi_tui", "cookies.lwp")


def make_opener():
    """创建带持久化 Cookie 的 opener。Cookie 文件权限 600，避免会话泄露。"""
    global _opener, _cookie_jar
    path = _cookie_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        os.chmod(os.path.dirname(path), 0o700)
    except OSError:
        pass
    _cookie_jar = http.cookiejar.LWPCookieJar(path)
    if os.path.exists(path):
        try:
            _cookie_jar.load(ignore_discard=True, ignore_expires=True)
        except (http.cookiejar.LoadError, OSError, ValueError):
            pass
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    _opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(_cookie_jar)
    )
    _opener.addheaders = [("Content-Type", "application/json")]


def _save_cookies():
    """把会话 Cookie 落盘，并确保文件权限为 600。"""
    global _cookie_jar
    try:
        path = _cookie_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        _cookie_jar.save(ignore_discard=True, ignore_expires=True)
        os.chmod(path, 0o600)
    except Exception:
        pass


def api(method, path, body=None):
    """调用摩柿 API，返回 (status, json|text)。"""
    url = BASE_URL + path
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _opener.open(req, timeout=30) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        status = e.code
    except Exception as e:
        return 0, {"error": str(e)}
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except Exception:
        decoded = raw.decode("utf-8", errors="replace")
    return status, decoded


def fetch_me():
    global _current_user
    status, data = api("GET", "/api/me")
    if status == 200 and isinstance(data, dict) and data.get("user"):
        _current_user = data["user"]
    else:
        _current_user = None
    return _current_user


def cmd_search(args):
    q = " ".join(args.q)
    if not q:
        print(f"{YELLOW}用法: search <书名/链接/ID>{RESET}")
        return
    print(f"{DIM}正在搜索「{q}」…{RESET}")
    status, data = api("GET", "/api/search?q=" + urllib.parse.quote(q))
    items = data.get("items", []) if isinstance(data, dict) else []
    if not items:
        print(f"{YELLOW}没有找到结果{RESET}")
        return
    print(f"\n{BOLD}搜索结果 ({len(items)}){RESET}")
    for i, it in enumerate(items):
        author = it.get("author") or "未知作者"
        print(f"  {CYAN}[{i}]{RESET} {BOLD}{it.get('title')}{RESET}  {DIM}{author}{RESET}")
        intro = (it.get("intro") or "").strip()
        if intro:
            print(f"       {DIM}{intro[:80]}{RESET}")
    print(f"\n{DIM}提示: 用 download <编号> <txt|epub|pdf> 提交任务; preview <编号> 在线预览{RESET}")


def cmd_download(args):
    status, data = api("GET", "/api/search?q=" + urllib.parse.quote(args.book))
    items = data.get("items", []) if isinstance(data, dict) else []
    if not items:
        print(f"{RED}没有找到这本书{RESET}")
        return
    book = items[0]
    fmt = args.format.lower()
    if fmt not in ("txt", "epub", "pdf"):
        print(f"{RED}格式仅支持 txt / epub / pdf{RESET}")
        return
    bid = book.get("book_id")
    if not bid:
        print(f"{RED}搜索结果缺少书籍 ID{RESET}")
        return
    st, resp = api("POST", "/api/tasks", body={"book_id": bid, "format": fmt})
    if isinstance(resp, dict) and resp.get("ok"):
        pos = resp.get("position")
        print(f"{GREEN}已提交「{book['title']}」({fmt.upper()}){RESET}"
              + (f"，队列位置 #{pos}" if pos is not None else ""))
    else:
        err = resp.get("error") if isinstance(resp, dict) else str(resp)
        print(f"{RED}提交失败: {err}{RESET}")


def _task_line(t, me, show_user):
    state = t.get("state", "?")
    mark = {
        "queued": YELLOW + "排队中" + RESET,
        "running": BLUE + "下载中" + RESET,
        "done": GREEN + "已完成" + RESET,
        "failed": RED + "失败" + RESET,
        "canceled": DIM + "已取消" + RESET,
    }.get(state, state)
    fmt = (t.get("format") or "txt").upper()
    prog = t.get("progress") or {}
    phase = prog.get("phase") or ""
    saved = prog.get("saved_chapters")
    total = prog.get("chapter_total")
    extra = " ".join(x for x in [phase, f"{saved}/{total} 章" if saved is not None else ""] if x)
    user = f" [{t.get('username')}]" if show_user and t.get("username") else ""
    pos = f" (#{t.get('position')})" if state == "queued" and t.get("position") is not None else ""
    err = f" {RED}{t.get('error')}{RESET}" if t.get("error") else ""
    title = str(t.get("title") or "?")[:34]
    return f"  {CYAN}{t['id']:>5}{RESET} {title:<34} {fmt:>4} {mark}{pos} {DIM}{extra}{RESET}{user}{err}"


def cmd_tasks(args):
    me = fetch_me()
    st, data = api("GET", "/api/tasks")
    items = data.get("items", []) if isinstance(data, dict) else []
    mine = [t for t in items if not me or (t.get("username") or "").lower() == me.get("username", "").lower()]
    if args.all:
        show = items
    else:
        show = mine
    if not show:
        print(f"{YELLOW}暂无任务{RESET}")
        return
    if isinstance(data, dict) and data.get("running") is not None:
        print(f"{DIM}运行 {data.get('running')} · 排队 {data.get('queued')}{RESET}")
    print(f"\n{BOLD}{'全站提取' if args.all else '我的提取'} ({len(show)}){RESET}")
    for t in show:
        print(_task_line(t, me, args.all))


def _download_file(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "MoshiNovel-TUI"})
    try:
        with _opener.open(req, timeout=60) as resp, open(dest, "wb") as f:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if total:
                    pct = done * 100 // total
                    print(f"\r{DIM}下载中 {pct}% ({done}/{total}){RESET}", end="", flush=True)
        print()
        return True
    except Exception as e:
        print(f"\r{RED}下载失败: {e}{RESET}")
        try:
            if os.path.exists(dest):
                os.remove(dest)
        except OSError:
            pass
        return False


def cmd_fetch(args):
    """fetch <任务ID>：下载已完成任务的产物文件"""
    st, data = api("GET", "/api/tasks")
    items = data.get("items", []) if isinstance(data, dict) else []
    task = next((t for t in items if t["id"] == args.task_id), None)
    if task is None:
        print(f"{RED}未找到任务 {args.task_id}{RESET}")
        return
    if task.get("state") != "done":
        print(f"{YELLOW}任务尚未完成（当前 {task.get('state')}）{RESET}")
        return
    url = task.get("download_url")
    if not url:
        print(f"{RED}该任务无下载链接{RESET}")
        return
    if not url.startswith("http"):
        url = BASE_URL + (url if url.startswith("/") else "/" + url)
    fmt = task.get("format") or "txt"
    if args.out:
        dest = args.out
    else:
        # 服务端 title 不可信：过滤掉路径分隔符、..、盘符等，避免路径穿越
        safe_title = _sanitize_filename(task.get("title") or "book")
        dest = f"{safe_title}.{fmt}"
    print(f"{DIM}保存到: {dest}{RESET}")
    if _download_file(url, dest):
        print(f"{GREEN}完成 → {dest}{RESET}")


def cmd_watch(args):
    """watch [秒]：每 5 秒刷新一次任务列表"""
    interval = args.interval or 5
    print(f"{DIM}每 {interval} 秒刷新，Ctrl+C 退出{RESET}")
    try:
        while True:
            os.system("clear" if os.name == "posix" else "cls")
            st, data = api("GET", "/api/tasks")
            items = data.get("items", []) if isinstance(data, dict) else []
            me = _current_user
            mine = [t for t in items if not me or (t.get("username") or "").lower() == me.get("username", "").lower()]
            print(f"{BOLD}摩柿任务监控 {DIM}({time.strftime('%H:%M:%S')}){RESET}")
            for t in mine[:20]:
                print(_task_line(t, me, False))
            time.sleep(interval)
    except KeyboardInterrupt:
        print()


def cmd_preview(args):
    """preview <书名>：提交 epub 预览任务"""
    status, data = api("GET", "/api/search?q=" + urllib.parse.quote(args.book))
    items = data.get("items", []) if isinstance(data, dict) else []
    if not items:
        print(f"{RED}没有找到这本书{RESET}")
        return
    book = items[0]
    bid = book.get("book_id")
    if not bid:
        print(f"{RED}搜索结果缺少书籍 ID{RESET}")
        return
    st, resp = api("POST", "/api/tasks", body={"book_id": bid, "format": "epub"})
    if isinstance(resp, dict) and resp.get("ok"):
        print(f"{GREEN}预览任务已提交（任务 #{resp.get('id')}）{RESET}")
        print(f"{DIM}完成后可用 read <任务ID> 在线阅读{RESET}")
    else:
        err = resp.get("error") if isinstance(resp, dict) else str(resp)
        print(f"{RED}提交失败: {err}{RESET}")


def cmd_read(args):
    """read <任务ID>：列章节并读取正文"""
    try:
        st, meta = api("GET", f"/api/book/{args.task_id}/meta")
        st, chapters = api("GET", f"/api/book/{args.task_id}/chapters")
    except Exception as e:
        print(f"{RED}读取失败: {e}{RESET}")
        return
    # /chapters 返回 JSON 数组；个别旧版可能返回 {items:[]}，两种都兼容
    if isinstance(chapters, list):
        cl = chapters
    elif isinstance(chapters, dict):
        cl = chapters.get("items", [])
    else:
        cl = []
    if not cl:
        print(f"{YELLOW}暂无章节（任务可能仍在下载）{RESET}")
        return
    title = meta.get("title") if isinstance(meta, dict) else None
    print(f"\n{BOLD}{title or '书籍'} · 共 {len(cl)} 章{RESET}")
    # 每行一章，用编号选择
    for i, ch in enumerate(cl[:200]):
        print(f"  {CYAN}{i:>3}{RESET} {ch.get('title')}")
    try:
        idx = int(input(f"\n{DIM}输入章节号（0-{len(cl)-1}）: {RESET}").strip())
    except (ValueError, EOFError):
        return
    if idx < 0 or idx >= len(cl):
        print(f"{RED}章节号超出范围{RESET}")
        return
    st, content = api("GET", f"/api/book/{args.task_id}/chapter/{idx}")
    if not isinstance(content, str):
        content = str(content)
    print(f"\n{BOLD}{cl[idx].get('title')}{RESET}\n")
    print(content)
    print(f"\n{DIM}上一章: read {args.task_id}（输入 {idx-1}）· 本章 {idx}{RESET}")


def cmd_login(args):
    global _current_user
    username = args.username or input("用户名: ").strip()
    # 密码不再通过命令行位置参数传入（会出现在 shell 历史 / 进程列表中）。
    # 若未显式提供 --password，则用 getpass 不回显输入。
    password = getattr(args, "password", None)
    if not password:
        try:
            password = getpass.getpass("密码: ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
    st, resp = api("POST", "/api/login", body={"username": username, "password": password})
    user = resp.get("user") if isinstance(resp, dict) else None
    if user:
        _current_user = user
        print(f"{GREEN}登录成功：{user.get('username')}（{'管理员' if user.get('is_admin') else '用户'}）{RESET}")
    else:
        err = resp.get("error") if isinstance(resp, dict) else str(resp)
        print(f"{RED}登录失败: {err}{RESET}")


def cmd_logout(args):
    global _current_user
    api("POST", "/api/logout", body={})
    _current_user = None
    print(f"{GREEN}已退出登录{RESET}")


def cmd_whoami(args):
    me = fetch_me()
    if me:
        title = me.get("title") or ""
        roles = []
        if me.get("is_admin"):
            roles.append("管理员")
        if me.get("high_rank"):
            roles.append("高权限")
        print(f"{BOLD}{me.get('username')}{RESET}"
              + (f"（{title}）" if title else "")
              + f"  {DIM}{' · '.join(roles) if roles else '普通用户'}{RESET}")
    else:
        print(f"{YELLOW}未登录{RESET}")


def cmd_site(args):
    st, data = api("GET", "/api/site")
    if isinstance(data, dict):
        for k in ("site_title", "site_version", "site_owner", "site_notice"):
            if data.get(k):
                print(f"  {BOLD}{k.replace('site_', '').replace('_', ' ')}:{RESET} {data[k]}")
        if data.get("disabled"):
            print(f"  {RED}站点已禁用{RESET}")
        if data.get("maintenance"):
            print(f"  {YELLOW}维护模式{RESET}")
    else:
        print(f"{RED}无法获取站点信息{RESET}")


def main():
    parser = argparse.ArgumentParser(
        prog="moshi_tui",
        description="摩柿小说下载站 (MoshiNovel) 终端版",
    )
    parser.add_argument("--version", action="version",
                        version=f"moshi_tui {__version__}")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("search", help="搜索小说")
    p.add_argument("q", nargs="+")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("download", help="提交下载任务")
    p.add_argument("book", help="书名 / 链接 / ID")
    p.add_argument("format", nargs="?", default="txt", help="txt / epub / pdf")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("tasks", help="查看任务列表")
    p.add_argument("-a", "--all", action="store_true", help="显示全站任务")
    p.set_defaults(func=cmd_tasks)

    p = sub.add_parser("fetch", help="下载任务产物文件")
    p.add_argument("task_id", type=int)
    p.add_argument("-o", "--out", help="保存路径")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("watch", help="监控任务队列")
    p.add_argument("interval", type=int, nargs="?", default=5)
    p.set_defaults(func=cmd_watch)

    p = sub.add_parser("preview", help="提交 epub 预览任务")
    p.add_argument("book")
    p.set_defaults(func=cmd_preview)

    p = sub.add_parser("read", help="在线阅读")
    p.add_argument("task_id", type=int)
    p.set_defaults(func=cmd_read)

    p = sub.add_parser("login", help="登录")
    p.add_argument("username", nargs="?")
    # 密码不再接受位置参数（会泄漏到 shell 历史 / ps 输出）。
    # 未提供时强制用 getpass 不回显输入。--password 仅用于脚本，不推荐。
    p.add_argument("--password", help=argparse.SUPPRESS)
    p.set_defaults(func=cmd_login)

    p = sub.add_parser("logout", help="退出登录")
    p.set_defaults(func=cmd_logout)

    p = sub.add_parser("whoami", help="当前用户")
    p.set_defaults(func=cmd_whoami)

    p = sub.add_parser("site", help="站点信息")
    p.set_defaults(func=cmd_site)

    args = parser.parse_args()
    make_opener()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    try:
        args.func(args)
    except KeyboardInterrupt:
        print()
    finally:
        _save_cookies()


if __name__ == "__main__":
    main()
