#!/usr/bin/env python3
"""变异测试（假绿扫描器）——「新守卫入池的唯一口径」的可重复自动化。

工装·第九轮起立的规矩：**一条新守卫只有在「改坏生产代码必须变红」时才算数**。
此前这条规矩靠每轮人手动打变异、手动看红绿，慢且容易漏。本工具把它变成仓库里的
一个可重复检查：

  ① 取一份**已提交**状态的干净副本（`git archive HEAD`，不含他窗在途未提交改动，
     否则基线会被在途改动搞红，红绿就分不清是谁的锅）；
  ② 先在**未变异**的副本上跑一遍该套件，确认它是绿的（红不红得是变异造成的）；
  ③ 往生产代码里打一处**故意的**变异，重跑同一套件；
  ④ 断言：套件变红 **且** 红在**预期的那条断言**上（不是随便哪条红就算数）。

用法：
  python3 tools/mutation_test.py                 # 默认变异集（不含慢套件）
  python3 tools/mutation_test.py --slow          # 加上慢套件（smoke_test_extra，约十分钟）
  python3 tools/mutation_test.py --only heading  # 只跑某一例
  python3 tools/mutation_test.py --list          # 列出全部变异
  python3 tools/mutation_test.py --keep          # 保留临时副本（调试用）
  python3 tools/mutation_test.py --allow-uncovered  # 放行「守卫尚未落库」的例

依赖：node（dom 冒烟）、playwright + WL_CHROMIUM（浏览器套件）。
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAIL = []
CHECKS = 0

# ── 套件定义：怎么跑、跑多久 ──────────────────────────────────────────────
SUITES = {
    "dom":       (["node", "tools/dom_smoke_test.js"], 600),
    # 用 sys.executable 而不是 "python3"：Windows 上 python3 往往指向另一个
    # 没装 playwright 的解释器 ⇒ 子进程直接 ModuleNotFoundError ⇒ 基线假红、
    # 全部变异被跳过（实为本机跑不起来，不是产品坏了）。
    "smoke":     ([sys.executable, "tools/smoke_test.py"], 1800),
    "roundtrip": ([sys.executable, "tools/smoke_test_roundtrip.py"], 1800),
    "extra":     ([sys.executable, "tools/smoke_test_extra.py"], 3600),
    # layout 由界面窗持有（tools/layout_test.py，第五十八轮加的静默截断/空态守卫）：
    # 下列三条 layout 变异由界面窗 93d280 提供并直验（红在预期断言上）。
    "layout":    ([sys.executable, "tools/layout_test.py"], 2400),
    # focus 由本窗持有（tools/focus_test.py，第十一轮「焦点保全」守卫）：
    "focus":     ([sys.executable, "tools/focus_test.py"], 900),
}

# ── 变异表 ────────────────────────────────────────────────────────────────
# name    : 变异名（--only 用）
# suite   : 跑哪个套件
# file    : 改哪个生产文件（相对仓库根）
# old/new : 必须**恰好命中一次**的原文串与替换串（命中数不为 1 ⇒ 变异失效 ⇒ 判红）
# expect  : 预期变红的那条断言的名字（套件输出里必须出现）
# slow    : 默认不跑（--slow 才跑）
MUTATIONS = [
    dict(name="heading", suite="dom", file="js/app.js", slow=False,
         old="<h1 class=\"page-title\">${svgFor('star-f')} 收藏",
         new="<div class=\"page-title\">${svgFor('star-f')} 收藏",
         expect="every view renders at least one heading",
         why="一屏标题全没了 ⇒ 标题层级守卫不得仍判绿（第十轮修的那条）"),
    dict(name="legacy", suite="dom", file="js/app.js", slow=False,
         old="localStorage.setItem(KEY, raw); localStorage.removeItem(k);",
         new="localStorage.setItem(KEY, raw); /* 变异：旧键不删 */",
         expect="the legacy key is removed after migration",
         why="迁移后不删旧键 ⇒ 迁移守卫必须红（第九轮）"),
    dict(name="streak_aria", suite="smoke", file="js/app.js", slow=False,
         old="$('#visitPill').setAttribute('aria-label', '最近 30 天访问 ' + n + ' 次');",
         new="/* 变异：aria-label 不再随数字同步 */",
         expect="grading a card bumps today's activity counter",
         why="顶栏徽标的 aria-label 不跟着数字走 ⇒ 必须红（第九轮）"),
    dict(name="quit", suite="smoke", file="js/app.js", slow=False,
         old="$('#fcQuit').onclick = quitSession;",
         new="$('#fcQuit').onclick = function(){}; /* 变异：退出按钮失灵 */",
         expect="quit back to setup",
         why="闪卡「退出」按钮失灵 ⇒ 必须红（第九轮；红须表现为断言红而非抛栈）"),
    dict(name="nobump", suite="roundtrip", file="js/app.js", slow=False,
         old="  bumpActivity(); save(); updateVisitPill();",
         new="  /* 变异：答题不记当日活跃 */ save(); updateVisitPill();",
         expect="records today's activity",
         why="答题不写当日活跃 ⇒ 必须红（第九轮补遗）"),
    dict(name="novisit", suite="smoke", file="js/app.js", slow=False,
         old="bumpVisit();",
         new="/* 变异：打开/刷新页面不记一次访问 */",
         expect="a page load counts as one more visit",
         why="刷新页面不计入访问次数 ⇒ 顶栏「最近 30 天访问次数」永远不涨，必须红"),
    dict(name="arrow", suite="extra", file="js/app.js", slow=True,
         # 锚点随 191c5b5 页码分家更新：browse.page++ → pageSet(pageNow() + 1)。
         # （改分页实现时须同步此处——锚点是生产代码原文串，0 命中即守卫失效）
         old="if (e.key === 'ArrowRight') { pageSet(pageNow() + 1); rerenderIfBrowse(); }",
         new="if (e.key === 'ArrowRight') { /* 变异：→ 不翻页 */ }",
         expect="ArrowRight pages forward",
         why="→ 键不翻页 ⇒ 必须红（第九轮）"),
    # ── layout 侧三条（界面窗 93d280 第五十八轮，直验过：红在预期断言上）──
    dict(name="clip_v", suite="layout", file="css/style.css", slow=False,
         old=".wcard .wc-ex-en{font-size:12.3px;line-height:1.6;color:var(--text-3);"
             "font-style:italic;display:-webkit-box;-webkit-line-clamp:2;"
             "-webkit-box-orient:vertical;overflow:hidden}",
         new=".wcard .wc-ex-en{font-size:12.3px;line-height:1.6;color:var(--text-3);"
             "font-style:italic;display:-webkit-box;-webkit-line-clamp:none;"
             "max-height:20px;overflow:hidden}",
         expect="截断扫描 320px #browse：无静默截断",
         why="英文例句去掉行数限制、改固定高度 ⇒ 纵向被静默裁掉，必须红（第五十八轮）"),
    dict(name="clip_h", suite="layout", file="css/style.css", slow=False,
         old=".sr-item .m{display:block;color:var(--text-2);font-size:13px;"
             "line-height:1.55;margin-top:2px;overflow-wrap:anywhere}",
         new=".sr-item .m{display:block;color:var(--text-2);font-size:13px;"
             "line-height:1.55;margin-top:2px;overflow-wrap:anywhere;"
             "overflow:hidden;text-overflow:clip !important;"
             "white-space:nowrap !important;max-width:40px !important}",
         expect="截断扫描 320px 搜索浮层：无静默截断",
         why="搜索结果释义去掉省略号并压窄 ⇒ 横向被静默截断，必须红（第五十八轮）"),
    dict(name="empty_none", suite="layout", file="css/style.css", slow=False,
         old=".empty-state{padding:52px 20px;text-align:center;color:var(--text-3)}",
         new=".empty-state{padding:52px 20px;text-align:center;color:var(--text-3);"
             "display:none !important}",
         expect="量到空态元素（判据未空转）",
         why="空态整体消失 ⇒ 空态守卫不得无声消失，必须红（第五十八轮修的那处）"),
    # ── 焦点保全三条（工装·第十一轮：界面窗 93d280 报出、本窗直验并修复）──
    dict(name="focus_prompt", suite="focus", file="js/app.js", slow=False,
         old="  if (!fbSnap && mode !== 'spell') {\n"
             "    const p = $('#qPrompt');\n"
             "    if (p) { try { p.focus(); } catch (e) { /* 忽略 */ } }\n"
             "  }",
         new="  /* 变异：新题渲染后不把焦点交回题干 */",
         expect="下一题后焦点落在新题干（不是 body）",
         why="新题渲染后焦点掉回 body ⇒ 读屏用户听不到新题，必须红（第十一轮）"),
    dict(name="focus_fb", suite="focus", file="js/app.js", slow=False,
         # 锚点＝第六十轮修过之后的焦点交接调用（浏览器禁用焦点元素的失焦是
         # 异步的，焦点交接改成 rAF + timeout 两次交接；这里掐掉这两次调用）
         old="  requestAnimationFrame(handoffToNext);\n"
             "  setTimeout(handoffToNext, 80);",
         new="  /* 变异：反馈渲染后不把焦点交回「下一题」 */",
         expect="作答后焦点落在「下一题」按钮（不是 body）",
         why="作答后焦点掉回 body ⇒ 键盘用户失去位置，必须红（第十一轮）"),
    dict(name="focus_card", suite="focus", file="js/app.js", slow=False,
         old="  refocus($('#flipCard'));",
         new="  /* 变异：闪卡评分后不把焦点交回新卡 */",
         expect="闪卡评分后焦点落回新卡片（不是 body）",
         why="闪卡评分后焦点掉回 body ⇒ 必须红（第十一轮）"),
]


def ok(name, cond, extra=""):
    global CHECKS
    CHECKS += 1
    print(("  ✓ " if cond else "  ✗ ") + name + (f"  [{extra}]" if extra else ""))
    if not cond:
        FAIL.append(name + " " + extra)


def copy_head(dst):
    """取一份 HEAD 的干净副本（含 .git 之外的仓库内容）。"""
    p1 = subprocess.Popen(["git", "-C", ROOT, "archive", "HEAD"],
                          stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["tar", "-x", "-C", dst], stdin=p1.stdout)
    p1.stdout.close()
    p2.communicate()
    p1.wait()
    return p1.returncode == 0 and p2.returncode == 0


def run_suite(work, suite):
    """在副本里跑一个套件，返回 (返回码, 输出)。"""
    cmd, timeout = SUITES[suite]
    env = dict(os.environ)
    # 默认 chromium 路径只在这台机器上**真实存在**时才透传：写死的是当初
    # Linux 容器里的路径，别的机器上 setdefault 一个不存在的路径会让
    # executable_path 指向空气 ⇒ 本来能跑的套件被误判成基线红（Windows 上
    # layout 三条变异因此被整体跳过）。没有命中 ⇒ 不设，让套件走自己的兜底。
    if not env.get("WL_CHROMIUM"):
        default_chrome = "/home/ubuntu/.cache/ms-playwright/chromium-1155/chrome-linux/chrome"
        if os.path.exists(default_chrome):
            env["WL_CHROMIUM"] = default_chrome
    # 子进程的输出是 UTF-8（套件里全是中文），父进程按系统 locale 解码会在
    # Windows 的 GBK 下直接抛 UnicodeDecodeError → 返回码被读成 1 →
    # 基线被判红、全部变异被跳过（表现为「16/17 项红」，实为本机跑不起来）。
    # 这里两端都钉死 UTF-8：子进程用 PYTHONUTF8/PYTHONIOENCODING 输出 UTF-8，
    # 父进程按 UTF-8 解码（errors=replace 兜底，不认识的字节不致命）。
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        r = subprocess.run(cmd, cwd=work, env=env, capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        return 124, out + "\n[变异套件跑满 %ds 被杀]" % timeout


def apply_mutation(work, mut):
    """把变异打进副本里的生产文件。返回 (命中次数, 说明)。"""
    p = os.path.join(work, mut["file"])
    with open(p, encoding="utf-8") as f:
        s = f.read()
    n = s.count(mut["old"])
    if n != 1:
        return n, "变异锚点在 %s 里命中 %d 次（须恰好 1 次）" % (mut["file"], n)
    with open(p, "w", encoding="utf-8") as f:
        f.write(s.replace(mut["old"], mut["new"]))
    return 1, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="只跑某个变异")
    ap.add_argument("--slow", action="store_true", help="连慢套件一起跑")
    ap.add_argument("--list", action="store_true", help="列出变异表")
    ap.add_argument("--keep", action="store_true", help="保留临时副本")
    ap.add_argument("--allow-uncovered", action="store_true",
                    help="放行「守卫尚未落库」的变异例（默认判红）")
    args = ap.parse_args()

    if args.list:
        for m in MUTATIONS:
            print("%-12s suite=%-9s %s" % (m["name"], m["suite"], m["why"]))
        return 0

    muts = [m for m in MUTATIONS
            if (args.only is None or m["name"] == args.only)
            and (args.slow or not m["slow"])]
    if not muts:
        print("没有匹配的变异"); return 2

    tmp = tempfile.mkdtemp(prefix="wl_mutation_")
    work = os.path.join(tmp, "head")
    os.makedirs(work)
    print("== 取 HEAD 干净副本 ==")
    ok("副本已生成", copy_head(work), work)

    # 基线：每个用到的套件先在**未变异**的副本上跑一次，必须绿
    baselines = {}
    for suite in sorted({m["suite"] for m in muts}):
        print("== 基线（未变异）：%s ==" % suite)
        t0 = time.time()
        rc, out = run_suite(work, suite)
        green = (rc == 0)
        baselines[suite] = (green, out)
        ok("基线 %s 是绿的（红红必须是变异造成的）" % suite, green,
           "rc=%d %s" % (rc, out.strip().splitlines()[-1][:70] if out.strip() else ""))
        print("   （%.0fs）" % (time.time() - t0))

    uncovered = []
    # 逐个变异
    for m in muts:
        print("== 变异 %s：%s ==" % (m["name"], m["why"]))
        base_green, base_out = baselines.get(m["suite"], (False, ""))
        if not base_green:
            ok("变异 %s：基线不绿，本例跳过（不能把基线的红算到变异头上）" % m["name"], False,
               "套件 %s 基线红" % m["suite"])
            continue
        # 「守卫未落库」与「守卫假绿」要分得开：基线输出里**根本没有这条断言名**
        # ⇒ 该守卫在 HEAD 里还不存在（多为他窗在途未提交）⇒ 本例算「未覆盖」，
        # 不是「抓不住」；若基线里有这条断言名、而变异后仍然绿 ⇒ 那才是真·假绿。
        if m["expect"] not in base_out:
            uncovered.append(m["name"])
            print("  ○ 变异 %s：基线输出里没有「%s」这条断言 ⇒ 该守卫尚未落库（HEAD 里不存在），"
                  "本例记为**未覆盖**（不计入失败；用 --allow-uncovered 可放行）"
                  % (m["name"], m["expect"]))
            continue
        # 复原文件（上一个变异可能改过同一个文件）
        src = os.path.join(ROOT, m["file"])
        dst = os.path.join(work, m["file"])
        with open(src, encoding="utf-8") as f:
            pristine = f.read()
        with open(dst, "w", encoding="utf-8") as f:
            f.write(pristine)
        n, why = apply_mutation(work, m)
        if n != 1:
            ok("变异 %s 成功打进生产代码" % m["name"], False, why)
            continue
        t0 = time.time()
        rc, out = run_suite(work, m["suite"])
        turned_red = (rc != 0)
        on_target = (m["expect"] in out)
        ok("变异 %s 让 %s 变红" % (m["name"], m["suite"]), turned_red, "rc=%d" % rc)
        ok("变异 %s 红在预期的那条断言上（%s）" % (m["name"], m["expect"]),
           on_target,
           "" if on_target else "输出里找不到该断言名；尾部：" +
           (out.strip().splitlines()[-1][:90] if out.strip() else ""))
        print("   （%.0fs）" % (time.time() - t0))
        # 复原
        with open(dst, "w", encoding="utf-8") as f:
            f.write(pristine)

    if args.keep:
        print("临时副本保留在", work)
    else:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if uncovered:
        print("未覆盖（守卫尚未落库）：%s" % "、".join(uncovered))
    if FAIL:
        print(f"RESULT: {len(FAIL)} of {CHECKS} checks FAILED")
        for f in FAIL:
            print("  - " + f)
        return 1
    if uncovered and not args.allow_uncovered:
        print(f"RESULT: {CHECKS} checks passed, but {len(uncovered)} mutation(s) UNCOVERED"
              "（守卫未落库；加 --allow-uncovered 放行）")
        return 1
    print(f"RESULT: ALL TESTS PASSED ({CHECKS} checks)")
    return 0


if __name__ == "__main__":
    # 本进程控制台输出钉 UTF-8（Windows GBK 控制台对 ✓/✗ 直接崩）；
    # 被测套件子进程两端的编码已在 run_suite 里钉死。
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    sys.exit(main())
