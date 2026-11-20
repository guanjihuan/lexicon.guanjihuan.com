#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""流水线守卫回归（工装层）：产物闸门必须先于写盘，写盘必须原子。

本套件盯住四条真实缺口（每条都先用隔离树变异复现过，再由本套件钉住）：

  ① merge_examples 的 clean() 丢句闸原本排在 json.dump **之后**——工具一边报
     「FAILED 丢句…超阈即止」并退出码 1，一边已经把少句的产物写进仓库
     （实测 data/examples.json 的 mtime 在失败运行后仍被改写）。
  ② merge_examples 写 data/examples.json 不是原子写（写一半崩溃留半截产物）。
  ③ make_data.py / make_examples.py 写 js/data.js、js/examples.js 同样非原子。
  ④ _gen_core.py 的台账全覆盖闸：缺词时必须 fail，且**不得改动** curation.json。
  ⑤ extract.py 的原始抽取闸同样排在写盘之后：数量对不上时，两份「永不手改」的
     上游原始件（data/words800.json、data/categorized.json）已被坏数据覆盖。
     现在闸不过 → 原始件保持原样；写盘也改 tmp+os.replace。

跑法： python3 tools/pipeline_test.py
（在临时目录里复制一份仓库再动手，绝不碰工作树；不需要浏览器）
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAIL = []
PASSED = 0


def ok(name, cond, extra=""):
    global PASSED
    if cond:
        PASSED += 1
        print("  ✓ " + name + (("  [%s]" % extra) if extra else ""))
    else:
        FAIL.append(name + ((" " + str(extra)) if extra else ""))
        print("  ✗ " + name + (("  [%s]" % extra) if extra else ""))


def md5(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def run(cwd, script, env=None):
    """跑一个 tools/ 脚本，返回 (退出码, 输出)

    子进程 stdio 一律钉成 UTF-8（env 注入 PYTHONIOENCODING），父进程管道也按
    UTF-8 解码（encoding= 参数）。此前两侧都不指定：管道解码跟随系统 locale
    （Windows 上是 GBK），而子进程继承操作者 shell 的 PYTHONIOENCODING——
    操作者带 utf-8 环境跑本套件时，子进程写 UTF-8、父进程按 GBK 解码，
    读线程 UnicodeDecodeError 后 stdout=None ⇒ out='' ⇒ 15 条「报错文案须含
    中文措辞」的断言全部空判假红（被误记为 Windows 基线噪声；2026-11-19 复核
    实证：不带 PYTHONIOENCODING 时 15 项全绿）。两侧同钉 UTF-8 后与操作者
    环境无关。errors=replace：报错文案本身坏字节也不至于让整套假红。"""
    child_env = dict(os.environ if env is None else env)
    child_env.setdefault("PYTHONIOENCODING", "utf-8")
    p = subprocess.run([sys.executable, os.path.join("tools", script)], cwd=cwd,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=child_env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def run_args(cwd, script, *args):
    """跑一个 tools/ 脚本并带参数，返回 (退出码, 输出)（编码口径与 run 相同）"""
    child_env = dict(os.environ)
    child_env.setdefault("PYTHONIOENCODING", "utf-8")
    p = subprocess.run([sys.executable, os.path.join("tools", script)] + list(args),
                       cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=child_env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


class _Crash(Exception):
    """模拟写盘中途崩溃（磁盘满 / 进程被杀）"""


class _CrashWriter:
    """写一半就抛异常的代理文件对象（只代理 .tmp 目标）"""

    def __init__(self, f):
        self._f = f

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def write(self, s):
        self._f.write(s[:max(1, len(s) // 2)])
        self._f.flush()
        raise _Crash("模拟写盘中途崩溃")

    def __getattr__(self, k):
        return getattr(self._f, k)


def atomic_crash_probe(root, script, payload):
    """行为断言：写盘中途崩溃时，目标文件必须**一个字节都不变**。

    此前这类守卫是源码 grep（`"os.replace" in src and ".tmp" in src`）——源码里
    出现这两个词就算过，把写盘改成「先直接写目标、再 os.replace 另一个文件」
    照样绿。这里改成真的跑一次：让写手在写 .tmp 时抛异常，然后看目标文件
    是不是被写坏了。

    payload: 传给 dump_atomic 的数据（dict ⇒ json 写手，str ⇒ 文本写手）
    返回 (通过与否, 说明)
    """
    path = os.path.join(root, "tools", script)
    if not os.path.exists(path):
        return False, "找不到 %s" % script
    # 只抽出 dump_atomic 这一个函数来跑（AST 取函数体），不 import 整个模块：
    # 这几个写手没有 __main__ 守卫，import 即执行（merge_examples 甚至会在
    # 闸门不过时 sys.exit），会把探针搅乱。
    import ast
    try:
        tree = ast.parse(open(path, encoding="utf-8").read())
    except SyntaxError as e:
        return False, "%s 解析失败：%s" % (script, e)
    fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "dump_atomic":
            fn = node
            break
    if fn is None:
        return False, "%s 里没有 dump_atomic" % script
    ns = {"os": os, "json": json}
    try:
        exec(compile(ast.Module(body=[fn], type_ignores=[]), path, "exec"), ns)
    except Exception as e:
        return False, "%s 的 dump_atomic 编译失败：%r" % (script, e)
    dump = ns["dump_atomic"]

    target = os.path.join(root, "data", "_atomic_probe_target.json")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        f.write("OLD-CONTENT")
    before = md5(target)

    real_open = open

    def crashing_open(p, mode="r", *a, **kw):
        # 任何写模式的打开都在写一半时崩：原子写崩在 .tmp 上（目标不受影响），
        # 非原子写崩在目标上（目标被写坏）——两种都要能判出来。
        f = real_open(p, mode, *a, **kw)
        if "w" in mode:
            return _CrashWriter(f)
        return f

    crashed = False
    try:
        ns["open"] = crashing_open        # 函数体里的 open 先在 ns 里找
        dump(target, payload)
    except _Crash:
        crashed = True
    except BaseException as e:
        return False, "%s 抛的不是模拟崩溃：%r" % (script, e)
    finally:
        ns["open"] = real_open
        for junk in (target + ".tmp",):
            if os.path.exists(junk):
                os.remove(junk)

    if not crashed:
        return False, "%s 的写盘没被拦下来（测不到崩溃路径）" % script
    after = md5(target)
    os.remove(target)
    if after != before:
        return False, "崩溃后目标文件被写坏了（%s → %s）" % (before, after)
    return True, "崩溃后目标字节不变"


def _letters(i):
    """第 i 个纯字母词名（解析器的词名正则只认字母，混入数字会被整条丢掉）"""
    return 'w' + chr(97 + (i // 26) % 26) + chr(97 + i % 26)


def make_words_html(nums):
    parts = ['<div class="entry-content">']
    for n in nums:
        parts.append('<h2>%d. word%d</h2><p>这是第%d个释义。</p>' % (n, n, n))
    parts.append('</div>')
    return ''.join(parts)


def make_cats_html(nums):
    parts = ['<div class="entry-content"><p>一、形容词</p><p>（1）积极的</p>']
    for i, n in enumerate(nums):
        parts.append('<p>%d. %s 某个释义</p>' % (n, _letters(i)))
    parts.append('</div>')
    return ''.join(parts)


def copy_repo(dst):
    """复制一份仓库（不含 .git）到 dst"""
    for name in os.listdir(ROOT):
        if name == ".git" or name == "__pycache__":
            continue
        s = os.path.join(ROOT, name)
        d = os.path.join(dst, name)
        if os.path.isdir(s):
            shutil.copytree(s, d, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(s, d)


PRODUCTS = ["data/words.json", "data/cats.json", "js/data.js",
            "data/examples.json", "js/examples.js", "data/curation.json"]
# sentiment 生成器读取 words.json 校验词形，因此新增词场景必须先 curate 一次；
# 落段后再 curate 一次，把裁定应用回 words/cats，最后才生成前端 JS。
STEPS = ["_gen_additions.py", "_gen_recat.py", "_gen_core.py", "curate.py",
         "_gen_sentiment.py", "curate.py", "make_data.py",
         "merge_examples.py", "make_examples.py"]


def main():
    tmp = tempfile.mkdtemp(prefix="wl_pipeline_")
    try:
        copy_repo(tmp)
        base = {p: md5(os.path.join(tmp, p)) for p in PRODUCTS}

        print("== ① 丢句闸必须先于写盘 ==")
        part = os.path.join(tmp, "data", "examples_parts", "part_01.json")
        raw = json.load(open(part, encoding="utf-8"))
        word = next(iter(raw))
        raw[word].append({"en": "This injected sentence has an empty Chinese side.", "zh": "  "})
        with open(part, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=1)
        ex_path = os.path.join(tmp, "data", "examples.json")
        mt_before = os.stat(ex_path).st_mtime_ns
        rc, out = run(tmp, "merge_examples.py")
        ok("a dirty part makes merge_examples fail", rc != 0, "rc=%d" % rc)
        ok("the failure names the dropped sentence", "丢句" in out and word in out,
           out.strip().splitlines()[-1][:80] if out.strip() else "")
        ok("the failed run leaves data/examples.json byte-identical",
           md5(ex_path) == base["data/examples.json"])
        ok("the failed run does not even touch the artifact",
           os.stat(ex_path).st_mtime_ns == mt_before)

        print("== ② 三个写手走原子写（写一半崩溃 ⇒ 目标字节不变）==")
        # 此前这条是**源码 grep**（"os.replace" in src and ".tmp" in src）：源码里
        # 出现这两个词就算过——真把写盘改成「直接写目标」照样绿。现在改成行为断言：
        # 让写手在写 .tmp 时崩掉，检查目标文件是不是被写坏了。
        for script, payload in (("merge_examples.py", {"a": 1}),
                                ("make_data.py", "PROBE"),
                                ("make_examples.py", "PROBE")):
            passed, why = atomic_crash_probe(tmp, script, payload)
            ok("%s writes atomically (target survives a mid-write crash)" % script,
               passed, why)
        # 正常跑一遍（恢复 part_01），确认无 .tmp 残留、产物与基线一致
        raw[word] = raw[word][:-1]
        with open(part, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=1)
        rc, out = run(tmp, "merge_examples.py")
        ok("merge_examples succeeds on a clean tree", rc == 0, out.strip().splitlines()[-1][:60] if out.strip() else "")
        leftovers = [os.path.join(dp, f) for dp, _, fs in os.walk(tmp) for f in fs if f.endswith(".tmp")]
        ok("no .tmp residue is left behind", not leftovers, str(leftovers[:3]))

        print("== ③ 台账缺词闸：fail 且不改 curation.json ==")
        led_path = os.path.join(tmp, "data", "core_decisions.json")
        led = json.load(open(led_path, encoding="utf-8"))
        dropped = next(iter(led["decisions"]))
        del led["decisions"][dropped]
        with open(led_path, "w", encoding="utf-8") as f:
            json.dump(led, f, ensure_ascii=False, indent=1)
        cur_path = os.path.join(tmp, "data", "curation.json")
        rc, out = run(tmp, "_gen_core.py")
        ok("a gap in the core ledger makes _gen_core fail", rc != 0, "rc=%d" % rc)
        ok("the failure names the missing word", dropped in out, out.strip().splitlines()[-1][:80] if out.strip() else "")
        ok("the failed run leaves data/curation.json byte-identical",
           md5(cur_path) == base["data/curation.json"])
        # 复位台账
        shutil.copy2(os.path.join(ROOT, "data", "core_decisions.json"), led_path)

        print("== ④ 生成链幂等 + 生成物与已提交文件同步 ==")
        # 早先把「幂等」和「零漂移」混成一条断言：链跑两遍后只与**跑链之前**的
        # 快照比对 —— 于是「跑链之前」和「跑链之后」两种状态被混为一谈：
        #   ① 幂等（run1 == run2）从来没被真正测过；
        #   ② 一旦生成源改过而产物没重烘（正在途的常态），后面几段「失败运行
        #      不改动产物」的断言会拿**跑链前**的旧快照去比 → 假红
        #      （实测：改了 T 表没重烘时，⑥⑨ 的 byte-identical 断言全红，
        #        而失败的那次运行其实一个字节都没写）。
        # 现在拆成两条：幂等＝run1 vs run2（与快照无关，永远该绿）；
        # 同步＝run1 vs 已提交文件（改源忘烘产物时红，这是**真报警**）。
        def run_chain(tag):
            for step in STEPS:
                rc, out = run(tmp, step)
                if rc != 0:
                    FAIL.append("chain step %s failed (%s): %s" % (step, tag, out.strip()[:120]))
                    print("  ✗ chain step %s failed (%s)" % (step, tag))
                    return None
            return {p: md5(os.path.join(tmp, p)) for p in PRODUCTS}

        run1 = run_chain("run1")
        run2 = run_chain("run2")
        if run1 is not None and run2 is not None:
            ok("the generation chain is idempotent (run1 == run2)", run1 == run2,
               str([p for p in PRODUCTS if run1[p] != run2[p]]))
        if run1 is not None:
            drift = [p for p in PRODUCTS if run1[p] != base[p]]
            ok("the generated products are in sync with the committed ones", not drift,
               "run: python3 tools/curate.py && python3 tools/make_data.py then commit " + str(drift))
            # 之后所有「失败运行不改动产物」的断言，基线一律取**跑完链之后**的状态
            base = dict(run1)

        # ④b sentiment 真源必须真的进入生成链。只改台账、不改任何产物时，
        # 跑链必须把新裁定落到 curation → words/cats → JS；若 STEPS 漏掉
        # _gen_sentiment.py，下面的 affected 会全部保持原字节而立刻变红。
        print("== ④b sentiment 台账改动必须传播到全部相关产物 ==")
        sent_path = os.path.join(tmp, "data", "sentiment_decisions.json")
        sent_bak = sent_path + ".chainbak"
        shutil.copy2(sent_path, sent_bak)
        try:
            ledger = json.load(open(sent_path, encoding="utf-8"))
            word_rows = json.load(open(os.path.join(tmp, "data", "words.json"), encoding="utf-8"))
            classified = {w["word"] for w in word_rows if w.get("pos")}
            candidate = next(((w, d) for w, d in ledger["decisions"].items()
                              if d.get("reg") and w in classified), None)
            ok("the sentiment drift probe finds a classified register decision",
               candidate is not None)
            if candidate is not None:
                word, decision = candidate
                old_reg = decision["reg"]
                decision["reg"] = "中性" if old_reg != "中性" else "书面语"
                decision["reg_reason"] = "pipeline probe: register propagation"
                with open(sent_path, "w", encoding="utf-8") as f:
                    json.dump(ledger, f, ensure_ascii=False, indent=1)
                repaired = run_chain("sentiment-drift")
                affected = ["data/curation.json", "data/words.json",
                            "data/cats.json", "js/data.js"]
                ok("a sentiment-only source edit reaches curation, words, cats and JS",
                   repaired is not None and all(repaired[p] != base[p] for p in affected),
                   "word=%s %s→%s; unchanged=%s" %
                   (word, old_reg, decision["reg"],
                    [] if repaired is None else [p for p in affected if repaired[p] == base[p]]))
        finally:
            shutil.copy2(sent_bak, sent_path)
        restored = run_chain("sentiment-restore")
        ok("restoring the sentiment ledger restores every product byte-identically",
           restored == base,
           [] if restored is None else [p for p in PRODUCTS if restored[p] != base[p]])
        # 留一份「跑完链之后」的 curation.json 快照：后面几段要往里注入坏数据再复原，
        # 复原用的是**链后**状态，而不是仓库提交版（生成源改过时两者不同）
        cur_bak = os.path.join(tmp, "data", "curation.json.chainbak")
        shutil.copy2(os.path.join(tmp, "data", "curation.json"), cur_bak)

        # ⑤ extract.py 的原始抽取闸（另起一份副本：它会写 data/words800.json，
        #    在同一份副本里跑会污染上面第④步的比对基线）
        tmp2 = tempfile.mkdtemp(prefix="wl_extract_")
        try:
            copy_repo(tmp2)
            w_path = os.path.join(tmp2, "data", "words800.json")
            c_path = os.path.join(tmp2, "data", "categorized.json")
            w_base, c_base = md5(w_path), md5(c_path)
            w_mt = os.stat(w_path).st_mtime_ns
            bad1 = os.path.join(tmp2, "bad4418.html")
            bad2 = os.path.join(tmp2, "bad24732.html")
            with open(bad1, "w", encoding="utf-8") as f:
                f.write(make_words_html([1]))
            with open(bad2, "w", encoding="utf-8") as f:
                f.write(make_cats_html([1]))
            rc, out = run_args(tmp2, "extract.py", "--offline", bad1, bad2)
            ok("a short raw extract makes extract.py fail", rc != 0, "rc=%d" % rc)
            ok("the failure names the count mismatch", "799" in out,
               out.strip().splitlines()[-1][:80] if out.strip() else "")
            ok("the failed run leaves data/words800.json byte-identical",
               md5(w_path) == w_base)
            ok("the failed run does not even touch data/words800.json",
               os.stat(w_path).st_mtime_ns == w_mt)
            ok("the failed run leaves data/categorized.json byte-identical",
               md5(c_path) == c_base)

            # 数量对得上时应当正常落盘，且幂等、无 .tmp 残留
            good1 = os.path.join(tmp2, "good4418.html")
            good2 = os.path.join(tmp2, "good24732.html")
            with open(good1, "w", encoding="utf-8") as f:
                f.write(make_words_html([n for n in range(1, 801) if n != 736]))
            with open(good2, "w", encoding="utf-8") as f:
                f.write(make_cats_html(list(range(1, 345))))
            rc, out = run_args(tmp2, "extract.py", "--offline", good1, good2)
            ok("a complete raw extract succeeds", rc == 0,
               out.strip().splitlines()[-1][:60] if out.strip() else "")
            got_w = json.load(open(w_path, encoding="utf-8"))
            got_c = json.load(open(c_path, encoding="utf-8"))
            ok("the extract writes 799 raw words", len(got_w) == 799, str(len(got_w)))
            ok("the extract writes 344 raw cats", len(got_c) == 344, str(len(got_c)))
            w_after, c_after = md5(w_path), md5(c_path)
            rc, out = run_args(tmp2, "extract.py", "--offline", good1, good2)
            ok("the extract is idempotent", rc == 0 and md5(w_path) == w_after
               and md5(c_path) == c_after)
            leftovers = [os.path.join(dp, f) for dp, _, fs in os.walk(tmp2)
                         for f in fs if f.endswith(".tmp")]
            ok("the extract leaves no .tmp residue", not leftovers, str(leftovers[:3]))
            passed, why = atomic_crash_probe(tmp2, "extract.py", {"a": 1})
            ok("extract.py writes atomically (target survives a mid-write crash)",
               passed, why)
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)
        # ⑥ add 段空义项闸：curate.py 须给出**友好报错**而非裸 IndexError 栈，
        #    且失败时产物保持原样（add 段由 T 表生成，手工注入空义项是可发生的）
        print("== ⑥ add 段空义项闸 ==")
        cur_path = os.path.join(tmp, "data", "curation.json")
        cur = json.load(open(cur_path, encoding="utf-8"))
        bad_word = "zz_injected_empty_senses"
        cur["add"].append({"word": bad_word, "senses": [], "pos": "名词"})
        with open(cur_path, "w", encoding="utf-8") as f:
            json.dump(cur, f, ensure_ascii=False, indent=1)
        rc, out = run(tmp, "curate.py")
        ok("an add entry with empty senses makes curate fail", rc != 0, "rc=%d" % rc)
        ok("the failure is a friendly message, not a traceback",
           "Traceback" not in out and "IndexError" not in out,
           out.strip().splitlines()[-1][:80] if out.strip() else "")
        ok("the failure names the offending word", bad_word in out,
           out.strip().splitlines()[-1][:80] if out.strip() else "")
        ok("the failed run leaves data/words.json byte-identical",
           md5(os.path.join(tmp, "data", "words.json")) == base["data/words.json"])
        ok("the failed run leaves data/cats.json byte-identical",
           md5(os.path.join(tmp, "data", "cats.json")) == base["data/cats.json"])
        # 把注入的坏 add 条目撤掉（后面的段落各自用干净清单；用链后快照复原）
        shutil.copy2(cur_bak, cur_path)

        # ⑦ 坏缓存隔离：缓存位被坏 HTML（404 页 / 半截下载 / 站点改版）占住时，
        #    若原样留着，下次重跑会继续复用这份坏缓存 → 永远失败且看不出原因。
        print("== ⑦ 坏缓存隔离 ==")
        cdir = tempfile.mkdtemp(prefix="wl_cache_")
        try:
            w800 = os.path.join(tmp, "data", "words800.json")
            w800_md5 = md5(w800) if os.path.exists(w800) else None
            c1p, c2p = os.path.join(cdir, "page4418.html"), os.path.join(cdir, "page24732.html")
            with open(c1p, "w", encoding="utf-8") as f:
                f.write(make_words_html([1]))          # 数量不对的坏页
            with open(c2p, "w", encoding="utf-8") as f:
                f.write(make_cats_html([1]))
            rc, out = run_args(tmp, "extract.py", "--cache", c1p, c2p)
            ok("a poisoned cache makes extract fail", rc != 0, "rc=%d" % rc)
            ok("the poisoned cache is quarantined as .bad so the next run re-fetches",
               (not os.path.exists(c1p)) and os.path.exists(c1p + ".bad")
               and (not os.path.exists(c2p)) and os.path.exists(c2p + ".bad"),
               "c1=%s c2=%s" % (os.path.exists(c1p), os.path.exists(c2p)))
            ok("the quarantined cache is reported to the user",
               ".bad" in out, out.strip().splitlines()[-1][:80] if out.strip() else "")
            ok("the failed run leaves data/words800.json byte-identical",
               (w800_md5 is None) or md5(w800) == w800_md5)
            # 用户自备的 --offline 样本**不**该被隔离（可能是唯一一份）
            s1 = os.path.join(cdir, "user4418.html")
            with open(s1, "w", encoding="utf-8") as f:
                f.write(make_words_html([1]))
            rc2, _ = run_args(tmp, "extract.py", "--offline", s1, c2p)
            ok("a user-supplied --offline file is never quarantined",
               rc2 != 0 and os.path.exists(s1), "rc=%d exists=%s" % (rc2, os.path.exists(s1)))
        finally:
            shutil.rmtree(cdir, ignore_errors=True)
        # ⑧ core_proposals 生成物零漂移：core_audit.py 的产出**不在生成链里**，
        #    所以「改过词表却忘了重烘焙」没有任何东西会拦——提案文件默默与现行词表
        #    脱节（真发生过：册五十七 C1 拆义后 35 处 sense 文案过期、overall 词性
        #    副词→形容词、standardize 骨架标记，全是陈旧累积）。
        #    这里在副本里重跑 core_audit.py，把重生成结果与已提交的提案文件逐字节比对：
        #    不一致即 fail，并提示重跑 + 提交。
        print("== ⑧ core_proposals 生成物零漂移 ==")
        cp_path = os.path.join(tmp, "data", "core_proposals.json")
        cp_base = md5(cp_path) if os.path.exists(cp_path) else None
        rc, out = run(tmp, "core_audit.py", env=dict(os.environ, PYTHONHASHSEED="0"))
        ok("core_audit.py runs clean", rc == 0,
           out.strip().splitlines()[-1][:60] if out.strip() else "")
        md5_seed0 = md5(cp_path)
        # 第二个种子：若有人把 fam_match 改回「按集合迭代序」找前缀，
        # 两个种子的产物就会不同（standardize→stand/standard 漂移）——守卫当场变红。
        rc2, _ = run(tmp, "core_audit.py", env=dict(os.environ, PYTHONHASHSEED="12345"))
        ok("core_audit.py output does not depend on the hash seed",
           rc2 == 0 and md5(cp_path) == md5_seed0,
           "seed0=%s seed12345=%s" % (md5_seed0, md5(cp_path)))
        ok("the committed proposal file is in sync with the word list",
           cp_base is not None and md5(cp_path) == cp_base,
           "run: python3 tools/core_audit.py  then commit data/core_proposals.json")
        leftovers = [os.path.join(dp, f) for dp, _, fs in os.walk(tmp)
                     for f in fs if f.endswith(".tmp")]
        ok("core_audit leaves no .tmp residue", not leftovers, str(leftovers[:3]))

        # ⑨ 两道「人手写的 JSON 才会有」的闸：
        #    ⑨a 重复键：标准库 json.load 对重复键是「后写的静默覆盖前一个」。
        #        curation.json 的 fix 段、core_decisions.json 台账、
        #        examples_parts/*.json 都是人写的，重复键完全可能发生；一旦发生，
        #        下一次 _gen_*.py 重跑就把整个文件改写掉，那一条记录**无声消失**。
        #    ⑨b 重复例句：同一个词的 3 条例句写成同一句，此前所有闸门都放行，
        #        界面上就显示成一模一样的三条。
        print("== ⑨ 重复键闸与重复例句闸 ==")
        cur_path2 = os.path.join(tmp, "data", "curation.json")
        cur_text = open(cur_path2, encoding="utf-8").read()
        dup_text = cur_text.replace(
            '"fix": {\n', '"fix": {\n  "routine": {"senses": ["哨兵：重复键"]},\n', 1)
        with open(cur_path2, "w", encoding="utf-8") as f:
            f.write(dup_text)
        cur_mid = md5(cur_path2)          # 注入重复键之后的字节（脚本若动过就会变）
        rc, out = run(tmp, "_gen_recat.py")
        ok("a duplicated key in curation.json makes the reader fail", rc != 0, "rc=%d" % rc)
        ok("the failure names the duplicated key", "duplicate key" in out and "routine" in out,
           out.strip().splitlines()[-1][:80] if out.strip() else "")
        ok("the failed run leaves data/curation.json byte-identical",
           md5(cur_path2) == cur_mid)
        shutil.copy2(cur_bak, cur_path2)

        part_path2 = os.path.join(tmp, "data", "examples_parts", "part_01.json")
        praw = json.load(open(part_path2, encoding="utf-8"))
        w0 = next(iter(praw))
        one = praw[w0][0]
        praw[w0] = [one, one, one]
        with open(part_path2, "w", encoding="utf-8") as f:
            json.dump(praw, f, ensure_ascii=False, indent=1)
        ex_path2 = os.path.join(tmp, "data", "examples.json")
        rc, out = run(tmp, "merge_examples.py")
        ok("three identical sentences for one word make merge_examples fail", rc != 0, "rc=%d" % rc)
        ok("the failure names the duplicated sentence",
           "duplicate sentence" in out and w0 in out,
           out.strip().splitlines()[-1][:80] if out.strip() else "")
        ok("the failed run leaves data/examples.json byte-identical",
           md5(ex_path2) == base["data/examples.json"])

        # ⑩ 六道新闸（工装·第七轮新增，每条都先在隔离树里复现过旧行为）：
        #    ⑩a --offline 给了不存在的路径：**不许联网抓取**、不许把网页写进那个路径
        #         （早先的实现会照抓 739KB 落到用户路径上，抽取还「成功」，
        #           用户自备样本被覆盖，且坏内容留在路径上被下次重跑继续复用）；
        #    ⑩b core_audit.py 带替代词表快照时，**不许**覆盖已提交的 core_proposals.json
        #         （README 写的是「只读分析」，实际它是个写手）；
        #    ⑩c fix 段的 senses 写成字符串时必须报错（早先被逐字符拆成 ['释','义']，
        #         还能通过「有释义」的闸门写进产物）；
        #    ⑩d recat 段里出现**增补词**必须报错并指向 T 表（早先：生成器放行 →
        #         应用器报「recat key not found」的死路）；
        #    ⑩e JSON 语法错误必须报成语法错误，不能套上「重复键」的外壳
        #         （JSONDecodeError 是 ValueError 的子类，早先的 except ValueError
        #           把两类错误混为一谈，害人去查一个不存在的重复键）；
        #    ⑩f 输入文件缺失必须是人话报错，不是裸 FileNotFoundError 栈。
        print("== ⑩ 新闸六则 ==")
        sdir = tempfile.mkdtemp(prefix="wl_round7_")
        try:
            # ⑩a --offline 指向不存在的文件
            w800_p = os.path.join(tmp, "data", "words800.json")
            w800_md5_now = md5(w800_p)
            miss1 = os.path.join(sdir, "no_such_4418.html")
            miss2 = os.path.join(sdir, "no_such_24732.html")
            rc, out = run_args(tmp, "extract.py", "--offline", miss1, miss2)
            ok("--offline with a missing file fails instead of fetching the web",
               rc != 0 and not os.path.exists(miss1) and not os.path.exists(miss2),
               "rc=%d exists=%s" % (rc, os.path.exists(miss1)))
            ok("the --offline failure says it does not go online",
               "--offline" in out, out.strip().splitlines()[-1][:80] if out.strip() else "")
            ok("the failed --offline run leaves data/words800.json byte-identical",
               md5(w800_p) == w800_md5_now)

            # ⑩b core_audit.py 带替代词表 ⇒ 已提交的提案文件一个字节都不动
            cp_p = os.path.join(tmp, "data", "core_proposals.json")
            cp_md5_now = md5(cp_p) if os.path.exists(cp_p) else None
            alt_p = os.path.join(sdir, "alt_words.json")
            with open(alt_p, "w", encoding="utf-8") as f:
                json.dump([{"num": 1, "word": "unprecedented", "senses": ["史无前例的"]}],
                          f, ensure_ascii=False)
            rc, out = run_args(tmp, "core_audit.py", alt_p)
            ok("core_audit.py with an alternate snapshot leaves the committed proposals alone",
               rc == 0 and md5(cp_p) == cp_md5_now, "rc=%d" % rc)
            ok("the alternate run says the committed proposals were not touched",
               "未被改动" in out, out.strip().splitlines()[-1][:80] if out.strip() else "")

            # ⑩c fix 段的 senses 是字符串 ⇒ 必须报错，且失败不写盘
            cur3 = json.load(open(cur_bak, encoding="utf-8"))
            cur3["fix"]["routine"] = {"senses": "单个字符串"}
            with open(cur_path2, "w", encoding="utf-8") as f:
                json.dump(cur3, f, ensure_ascii=False, indent=1)
            rc, out = run(tmp, "curate.py")
            ok("a fix entry whose senses is a plain string makes curate fail", rc != 0, "rc=%d" % rc)
            ok("the failure is friendly and names the offending word",
               "routine" in out and "Traceback" not in out,
               out.strip().splitlines()[-1][:80] if out.strip() else "")
            ok("the failed run leaves data/words.json byte-identical",
               md5(os.path.join(tmp, "data", "words.json")) == base["data/words.json"])

            # ⑩d recat 段里放一个增补词 ⇒ _gen_recat.py 必须报错并指向 T 表
            recat_p = os.path.join(tmp, "tools", "_gen_recat.py")
            recat_src = open(recat_p, encoding="utf-8").read()
            add_word = "analyze"       # 增补段里的词（add 段，非源站 800 词）
            patched = recat_src.replace("T = [\n", 'T = [\n("%s","动词",None),\n' % add_word, 1)
            with open(recat_p, "w", encoding="utf-8") as f:
                f.write(patched)
            shutil.copy2(cur_bak, cur_path2)
            cur_md5_before = md5(cur_path2)
            rc, out = run(tmp, "_gen_recat.py")
            ok("a recat key that is an added word is rejected", rc != 0, "rc=%d" % rc)
            ok("the rejection points at the T table in _gen_additions.py",
               add_word in out and ("_gen_additions" in out or "T 表" in out),
               out.strip().splitlines()[-1][:80] if out.strip() else "")
            ok("the rejected run leaves data/curation.json byte-identical",
               md5(cur_path2) == cur_md5_before)
            with open(recat_p, "w", encoding="utf-8") as f:
                f.write(recat_src)

            # ⑩e JSON 语法错误 ⇒ 报语法错误，不报重复键
            shutil.copy2(cur_bak, cur_path2)
            text = open(cur_path2, encoding="utf-8").read()
            with open(cur_path2, "w", encoding="utf-8") as f:
                f.write(text.replace('"fix": {', '"fix": {,,', 1))
            rc, out = run(tmp, "_gen_recat.py")
            ok("a JSON syntax error is reported as a syntax error, not as a duplicate key",
               rc != 0 and "语法错误" in out and "JSON 里出现了重复键" not in out,
               out.strip().splitlines()[-1][:80] if out.strip() else "")
            shutil.copy2(cur_bak, cur_path2)

            # ⑩f 输入文件缺失 ⇒ 人话报错，不是裸 FileNotFoundError 栈
            words_p = os.path.join(tmp, "data", "words.json")
            os.rename(words_p, words_p + ".hidden")
            rc, out = run(tmp, "make_data.py")
            ok("a missing input file is reported as a friendly message",
               rc != 0 and "Traceback" not in out and "不存在" in out,
               out.strip().splitlines()[-1][:80] if out.strip() else "")
            os.rename(words_p + ".hidden", words_p)

            # ⑪ 段完整性闸（第八轮新增，每条都先在隔离树里复现过旧行为）：
            #    curation.json 是**人写**的 JSON，段名打错、整段丢失、段类型写错
            #    都可能发生。此前各工具一律 .get(段, 默认值) 兜底，于是缺段会
            #    **静默**换一套口径、产出完全不同的词表，而退出码是 0：
            #        丢 recat 段   → 分类 2158→1896（262 词悄悄没了标注）
            #        丢 core 段    → 核心层 1060→968
            #        丢 noncore 段 → 核心层 1060→2045（985 个词悄悄回核）
            #    「段不存在」与「段为空」必须区分：空＝确实没有覆盖，缺＝口径不明。
            print("== ⑪ 段完整性闸 ==")
            cur_p = os.path.join(tmp, "data", "curation.json")
            w_p = os.path.join(tmp, "data", "words.json")
            c_p = os.path.join(tmp, "data", "cats.json")

            def with_curation(mutate, label):
                """注入一份改过段的 curation.json，跑 curate.py，返回 (rc, 输出)"""
                shutil.copy2(cur_bak, cur_p)
                cur_obj = json.load(open(cur_bak, encoding="utf-8"))
                mutate(cur_obj)
                with open(cur_p, "w", encoding="utf-8") as f:
                    json.dump(cur_obj, f, ensure_ascii=False, indent=1)
                return run(tmp, "curate.py")

            # ⑪a 缺 recat 段：必须 fail，且**不得**改写产物（旧版是 rc=0 静默改口径）
            rc, out = with_curation(lambda o: o.pop("recat"), "drop recat")
            ok("a missing recat segment makes curate fail instead of silently changing scope",
               rc != 0, "rc=%d" % rc)
            ok("the failure names the missing segment",
               "recat" in out and "缺少段" in out,
               out.strip().splitlines()[-1][:80] if out.strip() else "")
            ok("the failed run leaves data/words.json byte-identical",
               md5(w_p) == base["data/words.json"])
            ok("the failed run leaves data/cats.json byte-identical",
               md5(c_p) == base["data/cats.json"])

            # ⑪b 缺 noncore 段：旧版会把核心层从 1060 悄悄放成 2045
            rc, out = with_curation(lambda o: o.pop("noncore"), "drop noncore")
            ok("a missing noncore segment makes curate fail (core tier would drift 1060->2045)",
               rc != 0, "rc=%d" % rc)
            ok("the failed run leaves data/words.json byte-identical",
               md5(w_p) == base["data/words.json"])

            # ⑪c 段类型写错（fix 写成列表）⇒ 人话报错，不是裸 AttributeError 栈
            rc, out = with_curation(lambda o: o.update({"fix": ["routine"]}), "fix=list")
            ok("a segment of the wrong type makes curate fail with a friendly message",
               rc != 0 and "Traceback" not in out and "AttributeError" not in out
               and "段类型不对" in out,
               out.strip().splitlines()[-1][:80] if out.strip() else "")

            # ⑪d 段名打错（recat 写成 reccat，且正确段还在）⇒ 报警并给出近似拼写
            rc, out = with_curation(lambda o: o.update({"reccat": o.get("recat")}),
                                    "typo reccat")
            ok("an unrecognised segment is reported with a near-miss spelling hint",
               rc == 0 and "reccat" in out and "recat" in out,
               out.strip().splitlines()[-1][:80] if out.strip() else "")

            # ⑪e 段里的元素类型写错（core 段里塞了对象）⇒ 人话报错，不是裸 TypeError 栈
            rc, out = with_curation(lambda o: o["core"].append({"a": 1}), "core elem=dict")
            ok("a non-string element in a word-list segment is rejected with a friendly message",
               rc != 0 and "Traceback" not in out and "TypeError" not in out,
               out.strip().splitlines()[-1][:80] if out.strip() else "")
            shutil.copy2(cur_bak, cur_p)

            # ⑫ 原始抽取器不许整块吞掉词条（第八轮）：
            #     parse_words 遇到 <h3> 后面**不是** <p> 时（常常直接跟一个
            #     <ul> 义项列表），此前一律 i += 2 把紧随其后那块整块吞掉 ⇒
            #     该词条的全部义项就此消失，而且**不报任何错**（数量闸只看
            #     词条条数，看不见义项没了）。修法：只有下一块确实是 <p>、
            #     被当作小标题释义吃掉时才 +2，否则 +1。
            print("== ⑫ 原始抽取器不许吞块 ==")
            spec = importlib.util.spec_from_file_location(
                "wl_extract_mod", os.path.join(tmp, "tools", "extract.py"))
            ex_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ex_mod)

            def _doc(inner):
                return '<div class="entry-content"><h2>1. testword</h2>' + inner + '</div>'

            normal = ex_mod.parse_words(_doc(
                '<p>这是第一段释义。</p><h3>用法一</h3><p>小标题释义。</p>'
                '<ul><li>义项一</li><li>义项二</li></ul>'))[0]
            ok("the usual heading/paragraph/list layout still parses the same way",
               normal["senses"] == ["这是第一段释义。", "义项一", "义项二"]
               and normal["notes"] == ["用法一: 小标题释义。"],
               str(normal["senses"]))
            swallowed = ex_mod.parse_words(_doc(
                '<p>这是第一段释义。</p><h3>用法一</h3>'
                '<ul><li>义项三</li><li>义项四</li></ul>'))[0]
            ok("a list right after a heading is not swallowed whole",
               "义项三" in swallowed["senses"] and "义项四" in swallowed["senses"],
               str(swallowed["senses"]))
        finally:
            shutil.rmtree(sdir, ignore_errors=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAIL:
        print("RESULT: %d FAILURES" % len(FAIL))
        for f in FAIL:
            print("  -", f)
        sys.exit(1)
    print("RESULT: ALL TESTS PASSED (%d checks passed)" % PASSED)


if __name__ == "__main__":
    # 控制台自身也要 UTF-8：套件输出全是 ✓/✗/中文，Windows 默认 GBK 控制台
    # 会在第一条断言打印处 UnicodeEncodeError 崩掉（管道被测方两端的编码
    # 已在 run()/run_args() 钉死，这里只管本进程的控制台输出）。
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()
