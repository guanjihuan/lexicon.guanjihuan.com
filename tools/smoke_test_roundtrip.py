#!/usr/bin/env python3
"""Backup export/import round-trip & state-entry hardening regression.

Standalone suite (deliberately NOT part of smoke_test*.py / dom_smoke_test.js —
those are owned by the frontend session; baseline counts must stay stable).

Covers:
  A. Round-trip fidelity: seed a rich state -> export backup file -> mutate
     state away from it -> import the file -> re-export -> byte-compare the
     two JSON payloads.
  B. Explicit-null entries for days/quizHist in localStorage or an imported
     backup must not crash views (sanitizeState must drop them so DEFAULTS
     take over).
  C. Scalar-garbage spot checks on the load path (goal/rate/progress/days/fav).

Seeding mechanism note: the app saves in-memory state on `beforeunload`, so a
plain localStorage.setItem + reload gets clobbered by the OLD state at unload
time. Seed instead via a one-shot sessionStorage marker that an init script
applies BEFORE app.js runs (init script executes after the unload write).

Usage: python3 tools/smoke_test_roundtrip.py [--base URL]   (WL_CHROMIUM or playwright chromium)
"""
import argparse, json, os, sys, threading, functools, http.server, socketserver, shutil, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAIL = []
CHECKS = 0   # 断言数动态统计：结果行不再写死总数（历轮「测试勿写死」规矩同族）
BASE = None

def ok(name, cond, extra=""):
    global CHECKS
    CHECKS += 1
    print(("  ✓ " if cond else "  ✗ ") + name + (f"  [{extra}]" if extra else ""))
    if not cond: FAIL.append(name + " " + extra)

SEED = {
    "settings": {"theme": "dark", "goal": 42, "rate": 1.25, "fcLimit": 20,
                 "frontShowHint": True, "autoSpeak": False, "autoWrongFav": True, "showKeyHint": False},
    "progress": {"1": {"lv": 3, "due": 1, "seen": 7, "correct": 5, "wrong": 2, "last": 2},
                 "2": {"lv": 5, "due": 0, "seen": 11, "correct": 10, "wrong": 1, "last": 3},
                 "3": {"lv": 1, "due": 9, "seen": 2, "correct": 1, "wrong": 1, "last": 4}},
    "fav": [3, 1],
    "quizHist": [{"t": 1, "mode": "mix", "scope": "all", "score": 8, "total": 10, "skipped": 1},
                 {"t": 2, "mode": "en2zh", "scope": "core", "score": 5, "total": 5}],
    "days": {"2026-11-14": 7, "2026-11-15": 3},
    "created": 1700000000000,
}

def get_state(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('wl_state_v1') || 'null')")

def seed_state(page, obj):
    """Stage obj to be applied to localStorage before app.js on the NEXT navigation."""
    page.evaluate("s => sessionStorage.setItem('__wl_seed', s)", json.dumps(obj))

def goto_fresh(page):
    """Full reload so the init script + app boot see the staged seed.
    goto to an unambiguous different URL (BASE + '?r=N#home') — hash-only
    changes are same-document navigations and may not rerun init scripts."""
    goto_fresh.n = getattr(goto_fresh, "n", 0) + 1
    page.goto(f"{BASE}?r={goto_fresh.n}#home", wait_until="load")
    page.wait_for_timeout(350)

def export_backup(page, tmpdir, tag):
    """Capture the exported backup payload from the page itself.

    The download-file path (expect_download + save_as) breaks under the Ubuntu
    snap chromium wrapper: the browser writes the artifact into its private
    /tmp namespace, so the file the driver wants to copy is already gone when
    save_as() runs (ENOENT).  Reading the Blob the app hands to
    URL.createObjectURL is browser-agnostic and still exercises the real
    click path (anchor + download attribute).
    """
    page.wait_for_selector("#expBtn")
    page.evaluate("""() => {
      if (!window.__wlCreateObjectURL) {
        const orig = URL.createObjectURL.bind(URL);
        window.__wlCreateObjectURL = orig;
        URL.createObjectURL = (b) => { window.__wlExportBlob = b; return orig(b); };
      }
      window.__wlExportBlob = null;
    }""")
    page.click("#expBtn")
    page.wait_for_function("() => !!window.__wlExportBlob", timeout=15000)
    text = page.evaluate("async () => await window.__wlExportBlob.text()")
    p = os.path.join(tmpdir, f"backup-{tag}.json")
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return json.loads(text)

def import_backup(page, path):
    """Feed the backup through the file input as an in-memory buffer.

    set_input_files(path) hands the browser a filesystem path; under the snap
    chromium wrapper the browser lives in a private mount namespace and cannot
    read that path (the file input silently stays empty -> import never runs).
    A buffer travels with the protocol call, so no shared path is involved.
    """
    page.wait_for_selector("#impFile", state="attached")  # hidden input: attached, not visible
    with open(path, "rb") as f:
        buf = f.read()
    page.set_input_files("#impFile", files=[{"name": os.path.basename(path),
                                             "mimeType": "application/json",
                                             "buffer": buf}])
    page.wait_for_timeout(500)  # import handler saves with 120ms debounce

def main():
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None)
    args = ap.parse_args()

    tmpdir = tempfile.mkdtemp(prefix="wl_roundtrip_")   # 每次独立目录：并发跑不互相覆盖

    close_srv = None
    BASE = args.base
    if not BASE:
        os.chdir(ROOT)
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
        socketserver.TCPServer.allow_reuse_address = True
        # threaded: browser fetches data.js/examples.js in parallel (see smoke_test.py note)
        srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
        BASE = f"http://127.0.0.1:{srv.server_address[1]}/"
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        close_srv = srv.shutdown
        time.sleep(0.3)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = os.environ.get("WL_CHROMIUM")
        try:
            browser = pw.chromium.launch(headless=True, **({"executable_path": exe} if exe else {}))
        except Exception:
            browser = pw.chromium.launch(headless=True, channel="chromium")
        ctx = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        ctx.add_init_script("""
          try {
            const seed = sessionStorage.getItem('__wl_seed');
            if (seed) { localStorage.setItem('wl_state_v1', seed); sessionStorage.removeItem('__wl_seed'); }
          } catch (e) {}
        """)
        page = ctx.new_page()
        page.set_default_navigation_timeout(90000)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        # ============ A. export -> import -> re-export fidelity ============
        print("== A. round-trip ==")
        page.goto(BASE, wait_until="load")  # establish BASE origin so sessionStorage marker works
        seed_state(page, SEED)
        goto_fresh(page)
        page.goto(BASE + "#settings")
        page.wait_for_timeout(300)
        exp1 = export_backup(page, tmpdir, "1")
        ok("export carries seeded progress", set(exp1.get("progress", {})) == {"1", "2", "3"}, str(sorted(exp1.get("progress", {}))))
        ok("export carries fav/quizHist/days/settings",
           exp1.get("fav") == [3, 1] and len(exp1.get("quizHist", [])) == 2
           and exp1.get("days", {}).get("2026-11-14") == 7 and exp1.get("settings", {}).get("goal") == 42)

        # mutate live state away from the backup, then import
        mutated = json.loads(json.dumps(SEED))
        mutated["progress"].pop("1"); mutated["fav"] = []; mutated["quizHist"] = []
        mutated["days"] = {}; mutated["settings"]["goal"] = 9
        seed_state(page, mutated)
        goto_fresh(page)
        mid = get_state(page)
        ok("mutation took hold before import", mid and mid["settings"]["goal"] == 9 and mid["fav"] == [],
           f"goal={mid and mid['settings']['goal']}")
        page.goto(BASE + "#settings")
        page.wait_for_timeout(300)
        import_backup(page, os.path.join(tmpdir, "backup-1.json"))
        st = get_state(page)
        ok("import restored progress/fav/goal",
           st and set(st["progress"]) == {"1", "2", "3"} and st["fav"] == [3, 1] and st["settings"]["goal"] == 42,
           f"goal={st and st['settings']['goal']}")
        exp2 = export_backup(page, tmpdir, "2")
        ok("re-export byte-identical to original export",
           json.dumps(exp1, sort_keys=True) == json.dumps(exp2, sort_keys=True),
           f"diff keys: {[k for k in set(exp1) | set(exp2) if exp1.get(k) != exp2.get(k)]}")

        errors.clear()
        goto_fresh(page)
        ok("home renders after round-trip with no JS errors", not errors, "; ".join(errors[:2]))

        # ============ B. explicit-null entries must not crash ============
        print("== B. explicit nulls ==")
        NULLY = json.loads(json.dumps(SEED))
        NULLY["days"] = None
        NULLY["quizHist"] = None
        seed_state(page, NULLY)
        errors.clear()
        goto_fresh(page)
        ok("boot survives days/quizHist = null", not errors, "; ".join(errors[:2]))
        page.goto(BASE + "#study", wait_until="load")   # 合并页：切到测验模式再等开始钮
        page.click("#studyModeSeg button[data-m='quiz']")
        page.wait_for_timeout(300)
        ok("quiz view opens after null-state boot", bool(page.query_selector("#startQuiz")), "no start button found")
        if page.query_selector("#startQuiz"):
            errors.clear()
            page.click("#startQuiz")
            page.wait_for_timeout(800)
            # 此前这条只断言「没有 JS 错」——连题都没答，名字里写的
            # 「bumpActivity live」没有任何证据支撑（典型的「名字说一套、断言做一套」）。
            # 改成真走一轮答题：① 题目与选项渲染出来；② 作答后反馈卡出现；
            # ③ 当日活跃计数真的 +1（days 里出现今天的键、值 ≥ 1）——
            #    这一条同时验了「days:null 被 sanitize 掉之后，答题路径仍能写回 days」。
            _opts = page.query_selector_all(".quiz-opt")
            ok("quiz question renders after null-state boot", len(_opts) >= 2, "%d options" % len(_opts))
            if _opts:
                page.click(".quiz-opt")
                page.wait_for_timeout(400)
                ok("quiz feedback shows after answering", bool(page.query_selector("#qFb.show")), "")
                page.wait_for_timeout(600)   # save() 是 120ms 防抖，等它落盘
                _today = page.evaluate(
                    "() => { const d = new Date();"
                    " return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0')"
                    " + '-' + String(d.getDate()).padStart(2,'0'); }")
                _days = (get_state(page) or {}).get("days") or {}
                ok("answering after a null-state boot records today's activity (bumpActivity live)",
                   isinstance(_days, dict) and isinstance(_days.get(_today), int) and _days[_today] >= 1,
                   "days=%s today=%s" % (_days, _today))
            ok("quiz answer cycle runs (bumpActivity live)", not errors, "; ".join(errors[:2]))
        errors.clear()
        page.goto(BASE + "#stats")
        page.wait_for_timeout(300)
        # 「stats view renders」此前只验「没有 JS 错」——统计页就算一片空白也判过。
        # 加一条「真的渲染出了卡片」：.stats-grid 里必须有卡片。
        _scards = page.query_selector_all(".stats-grid .card")
        ok("stats view renders after null-state boot",
           (not errors) and len(_scards) >= 1, "%d cards; %s" % (len(_scards), "; ".join(errors[:2])))
        # the same payload through the IMPORT path
        nullpath = os.path.join(tmpdir, "backup-null.json")
        with open(nullpath, "w", encoding="utf-8") as f:
            json.dump(NULLY, f)
        page.goto(BASE + "#settings")
        page.wait_for_timeout(300)
        errors.clear()
        import_backup(page, nullpath)
        ok("import of null-days/quizHist backup succeeds (toast, no crash)", not errors, "; ".join(errors[:2]))
        st = get_state(page)  # import handler saves (debounced, waited out in import_backup)
        ok("import persists sanitized state (nulls dropped to defaults)",
           st and isinstance(st.get("days"), dict) and isinstance(st.get("quizHist"), list),
           f"days={st and type(st.get('days')).__name__} quizHist={st and type(st.get('quizHist')).__name__}")
        errors.clear()
        goto_fresh(page)
        ok("reload after null-import: no JS errors", not errors, "; ".join(errors[:2]))

        # ============ C. scalar-garbage tolerance on the load path ============
        # Assertions are UI-observable: boot sanitizes in memory but does NOT
        # rewrite localStorage unless pruneState sees dead word nums, so reading
        # raw storage would show the un-clamped payload (test artifact, not defect).
        print("== C. garbage values ==")
        def views_ok(hashes):
            # 只验「没有 JS 错」是不够的：视图可以一片空白而毫无报错。
            # 故每到一屏都要确认主区域真的渲染出了东西（.stats-grid 的卡片 / 空态文案）。
            for h in hashes:
                page.goto(BASE + h)
                page.wait_for_timeout(300)
                if errors:
                    return False
                if h == "#stats":
                    if len(page.query_selector_all(".stats-grid .card")) < 1:
                        return False
                else:
                    if not page.query_selector("#main *"):
                        return False
            return not errors
        def fav_count_ok(n):
            page.goto(BASE + "#fav")
            page.wait_for_timeout(300)
            return (not errors) and (f"已收藏 {n} 词" in page.inner_text(".page-title"))
        def settings_shows(goal=None, rate=None):
            page.goto(BASE + "#settings")
            page.wait_for_timeout(300)
            if errors: return False
            if goal is not None and page.input_value("#goalInput") != str(goal): return False
            if rate is not None and page.inner_text("#rateVal") != f"{rate:.2f}": return False
            return True
        cases = [
            ("goal string -> default 30 shown in UI", lambda p: p["settings"].update(goal="many"), lambda: settings_shows(goal=30)),
            ("rate string -> default 0.95 shown in UI", lambda p: p["settings"].update(rate="fast"), lambda: settings_shows(rate=0.95)),
            ("goal null -> default not boundary", lambda p: p["settings"].update(goal=None), lambda: settings_shows(goal=30)),
            ("rate null -> default not boundary", lambda p: p["settings"].update(rate=None), lambda: settings_shows(rate=0.95)),
            ("goal empty string -> default", lambda p: p["settings"].update(goal=""), lambda: settings_shows(goal=30)),
            ("numeric string still honored", lambda p: p["settings"].update(goal="55", rate="1.10"), lambda: settings_shows(goal=55, rate=1.10)),
            ("progress entry scalar -> stats survives", lambda p: p["progress"].update({"1": 5}), lambda: views_ok(["#stats"])),
            ("days entry string -> stats survives", lambda p: p["days"].update({"2026-11-14": "x"}), lambda: views_ok(["#stats"])),
            ("fav dead nums -> fav page counts 2", lambda p: p.update(fav=[1, 999999, "2"]), lambda: fav_count_ok(2)),
        ]
        for name, patch, check in cases:
            payload = json.loads(json.dumps(SEED)); patch(payload)
            seed_state(page, payload)
            errors.clear()
            goto_fresh(page)
            ok(name, (not errors) and check(), "; ".join(errors[:1]))

        browser.close()
    if close_srv:
        close_srv()
    shutil.rmtree(tmpdir, ignore_errors=True)

    print()
    if FAIL:
        print(f"RESULT: {len(FAIL)} of {CHECKS} checks FAILED")
        for f in FAIL: print("  - " + f)
        sys.exit(1)
    print(f"RESULT: ALL TESTS PASSED ({CHECKS} checks)")

# 控制台输出钉 UTF-8（Windows GBK 控制台对 ✓/✗ 直接崩，见 _console_utf8.py）
from _console_utf8 import force_utf8_console  # noqa: E402

force_utf8_console()

if __name__ == "__main__":
    main()
