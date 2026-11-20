#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""内容域守卫回归（词汇 / 释义 / 例句）：语料自身的机械判据。

本套件只读三份线上产物：
  data/examples.json   例句（en + zh 逐叶）
  data/words.json      词表（释义 senses / 词性 / catGloss）
  data/curation.json   策展真源（version / fix / recat / add）

它盯的全是**可重算的机械判据**，不含任何主观判断：
  ① 例句结构：每词恰 3 条、en/zh 非空、词表键集与例句键集一致
  ② zh 句面：首尾无空白、句末有终止标点、句首无标点、无半角 , ; :、
     无连续空格、无半角引号、无占位符（TODO/待补/XXX/…）、括号配对
  ③ 词内与全库唯一性：同词 3 条 zh 互不相同、同词 3 条 en 互不相同、
     全库 zh 句子互不重复、全库 en 句子互不重复
  ④ en↔zh 数值一致：en 里的百分数数值、四位年份必须能在对应 zh 里找到
  ⑤ 禁译表：历次校对归一掉的译法不得回潮
  ⑥ 释义域：senses 非空、条内互不相同、无首尾空白与连续空格
  ⑦ 策展真源：version 为正整数；fix / recat / add 每条 senses 非空
  ⑧ 全角括号内不留半角空格（释义与 zh 例句）——「（ She also teaches …）」这类
     夹在括号首尾的半角空格是纯排版脏点，中文排版里没有这种写法
  ⑨ en 句侧括号与引号配对（zh 侧已有配对检查，en 侧此前没人管）
  ⑩ 挖空回退清单覆盖：3 条例句都不含目标词原形的词，必须在
     tools/_audit/cloze_ineligible_84.json 的名单里——否则「例句挖空」题型
     出不了题（前端有回退守卫，但回退＝该词不出挖空题，名单能让人看见缺口）

每条判据都先用隔离副本做过**变异验证**（改坏一处 ⇒ 必须红在预期那一条），
脚本见 tools/content_mutation.py。

跑法： python3 tools/content_test.py [--root 仓库根目录]
（纯读，不需要浏览器，不碰工作树）
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAIL = []
PASSED = 0

# zh 句末终止标点（可带收尾的右引号/右括号）
ZH_END = re.compile(r"[。！？…]+[\"」』）》)\]]*$")
# en 句末终止标点（可带收尾的右引号/右括号）
EN_END = re.compile(r"[.!?]+[\"')]*$")
# 禁译表：历次校对中已归一掉的译法（下列写法全库应为 0 命中）
FORBIDDEN_ZH = [
    "先导测试",     # pilot testing ⇒ 预试 / 试点研究 / 试点
    "噪声数据集",   # noisy dataset ⇒ 含噪数据集
    "糊口农业",     # subsistence farming ⇒ 自给自足的农业
    "一手史料",     # primary source ⇒ 原始资料
]
# 英式拼写穷举表：全库统一美式拼写（README/数据流水线口径），en 例句侧应为 0 命中。
# 词形按「词头」收录（边界用 \b，带后缀也能命中：characterise 命中 characterised）。
# 三个前缀撞形词单列进 BRITISH_EN_RE（负向环视排除美式合法超串）：
#   analyse → analyses 是美式合法（analysis 复数），analysed/analysing 才算英式；
#   fulfil  → fulfill 是美式拼法本身，fulfil 只在 NOT 后接 l 时算英式；
#   programme → programmer 是美式合法名词，programme 只在 NOT 后接 r 时算英式。
# 词典外链 slug（catalogue/favour 等）不在本判据范围——只查例句 en。
BRITISH_EN = [
    "colour", "favour", "behaviour", "centre", "metre",
    "organise", "realise", "recognise", "emphasise", "utilis",
    "characterise", "summarise", "standardise", "specialise", "hypothesise",
    "catalogue", "dialogue", "labour", "neighbour", "honour", "humour",
    "defence", "licence", "practise",
    "modelling", "labelled", "cancelled", "skilful", "wilful",
]
BRITISH_EN_RE = re.compile(
    r"\banalyse(?!s)"        # analyses 是美式合法（analysis 复数）；analyse 本体才算英式
    r"|\banalys(?:ed|ing)\b"  # analysing/analysed 去掉了 e，与 analyse 撞不上——单列
    r"|\bfulfil(?!l)"        # fulfill 是美式拼法本身；fulfilment 才算英式
    r"|\bprogramme(?!r)"     # programmer 是美式合法名词；programme 本体才算英式
    r"|\bparalyse")
BRITISH_EN_RES = [re.compile(r"\b" + re.escape(t)) for t in BRITISH_EN]
PLACEHOLDERS = ["TODO", "FIXME", "XXX", "待补", "待定", "占位", "？？", "??"]
# 允许在中文译文里保留的拉丁缩写：报告规范 / 生物学术语等**专名**，
# 在中文语境里保留拉丁缩写是正确写法（该批词条的释义本身带中文说明）。
# 判据与 tools/_audit/audit_all.py 同源；普通英文词残留仍应判红。
ZH_KEEP_LATIN = {"DNA", "RNA", "PRISMA", "CONSORT", "STROBE"}


def ok(name, cond, extra=""):
    global PASSED
    if cond:
        PASSED += 1
        print("  ✓ " + name + (("  [%s]" % extra) if extra else ""))
    else:
        FAIL.append((name, extra))
        print("  ✗ " + name + (("  [%s]" % extra) if extra else ""))


def load(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8") as f:
        return json.load(f)


def main():
    global ROOT
    argv = sys.argv[1:]
    if "--root" in argv:
        ROOT = os.path.abspath(argv[argv.index("--root") + 1])
    print("内容域守卫：根目录 %s" % ROOT)

    ex = load(ROOT, "data/examples.json")
    words = load(ROOT, "data/words.json")
    cur = load(ROOT, "data/curation.json")

    pairs = []          # (word, index, en, zh)
    for w, arr in ex.items():
        if isinstance(arr, dict):          # 容错：兼容 {en,zh} 单叶形状
            arr = [arr]
        for i, e in enumerate(arr):
            pairs.append((w, i, e.get("en", ""), e.get("zh", "")))

    # ① 结构
    bad = [w for w, arr in ex.items() if len(arr) != 3]
    ok("每词恰 3 条例句", not bad, "%d 词条数异常" % len(bad))

    bad = [(w, i) for w, i, en, zh in pairs if not en.strip() or not zh.strip()]
    ok("每条例句 en/zh 均非空", not bad, "%d 处空句" % len(bad))

    ok("词表与例句的词表键集一致",
       set(x["word"] for x in words) == set(ex.keys()),
       "词表 %d / 例句 %d" % (len(words), len(ex)))

    # ② zh 句面
    bad = [(w, i) for w, i, en, zh in pairs if zh != zh.strip()]
    ok("zh 无首尾空白", not bad, "%d 处" % len(bad))

    bad = [(w, i) for w, i, en, zh in pairs if not ZH_END.search(zh)]
    ok("zh 以终止标点收尾", not bad, "%d 处" % len(bad))

    bad = [(w, i) for w, i, en, zh in pairs if not EN_END.search(en)]
    ok("en 以终止标点收尾", not bad, "%d 处" % len(bad))

    bad = [(w, i) for w, i, en, zh in pairs if zh and zh[0] in "，。；：、）】」』"]
    ok("zh 句首无标点", not bad, "%d 处" % len(bad))

    bad = [(w, i) for w, i, en, zh in pairs if re.search(r"[,;:]", zh)]
    ok("zh 无半角 , ; :", not bad, "%d 处" % len(bad))

    bad = [(w, i) for w, i, en, zh in pairs if "  " in zh]
    ok("zh 无连续空格", not bad, "%d 处" % len(bad))

    bad = [(w, i) for w, i, en, zh in pairs if '"' in zh or "'" in zh]
    ok("zh 无半角引号", not bad, "%d 处" % len(bad))

    bad = [(w, i) for w, i, en, zh in pairs
           if any(p in zh for p in PLACEHOLDERS)]
    ok("zh 无占位符残留", not bad, "%d 处" % len(bad))

    # zh 里残留**普通英文词**（专名缩写如 CONSORT/PRISMA/DNA 属豁免，见 ZH_KEEP_LATIN）。
    # 这项曾是 content_test 的盲区之一（zh 残留英文能全绿漏过），现由 audit_all 的
    # 判据提升为常规守卫。
    # 占位符（TODO/FIXME/XXX…）由上一条断言单独负责，此处**不重复计入**——
    # 否则一个占位符会同时触发两条断言，令变异验证的「红在预期那条」失配。
    bad = []
    for w, i, en, zh in pairs:
        if any(p in zh for p in PLACEHOLDERS):
            continue
        for m in re.finditer(r"[A-Za-z]{2,}", zh):
            if m.group(0) not in ZH_KEEP_LATIN:
                bad.append((w, i, m.group(0)))
    ok("zh 无普通英文词残留（专名缩写豁免）", not bad, "%d 处" % len(bad))

    def unbalanced(s):
        return (s.count("（") != s.count("）") or s.count("「") != s.count("」")
                or s.count("《") != s.count("》"))

    bad = [(w, i) for w, i, en, zh in pairs if unbalanced(zh)]
    ok("zh 括号配对（）（「」《》）", not bad, "%d 处" % len(bad))

    # ③ 唯一性
    bad = []
    for w, arr in ex.items():
        zhs = [e.get("zh", "") for e in arr]
        ens = [e.get("en", "") for e in arr]
        if len(set(zhs)) != len(zhs):
            bad.append(w)
    ok("同词 3 条 zh 互不相同", not bad, "%d 词" % len(bad))

    bad = []
    for w, arr in ex.items():
        ens = [e.get("en", "") for e in arr]
        if len(set(ens)) != len(ens):
            bad.append(w)
    ok("同词 3 条 en 互不相同", not bad, "%d 词" % len(bad))

    seen = {}
    dup = []
    for w, i, en, zh in pairs:
        if zh in seen:
            dup.append((seen[zh], w, i))
        else:
            seen[zh] = (w, i)
    ok("全库 zh 句子互不重复", not dup, "%d 处重复" % len(dup))

    seen = {}
    dup = []
    for w, i, en, zh in pairs:
        if en in seen:
            dup.append((seen[en], w, i))
        else:
            seen[en] = (w, i)
    ok("全库 en 句子互不重复", not dup, "%d 处重复" % len(dup))

    # ④ en↔zh 数值一致。必须匹配完整数值 token：
    # 子串判断会把 en=5% / zh=15% 误判为一致，年份也有同样的前缀/后缀漏洞。
    bad = []
    for w, i, en, zh in pairs:
        for m in re.finditer(r"(\d+(?:\.\d+)?)\s*%", en):
            value = re.escape(m.group(1))
            if not re.search(r"(?<![\d.])" + value + r"\s*%", zh):
                bad.append((w, i, m.group(1)))
    ok("en 的百分数数值在 zh 中出现", not bad, "%d 处" % len(bad))

    bad = []
    for w, i, en, zh in pairs:
        for m in re.finditer(r"\b(1[89]\d{2}|20\d{2})\b", en):
            if not re.search(r"(?<!\d)" + m.group(1) + r"(?!\d)", zh):
                bad.append((w, i, m.group(1)))
    ok("en 的四位年份在 zh 中出现", not bad, "%d 处" % len(bad))

    # ⑤ 禁译表
    bad = []
    for w, i, en, zh in pairs:
        for term in FORBIDDEN_ZH:
            if term in zh:
                bad.append((w, i, term))
    ok("禁译表零命中", not bad, "%d 处" % len(bad))

    # ⑤' 美式拼写：全库统一美式（r68 机械扫描是穷举一次，本判据把它固化成回归——
    # r60 批新增例句曾带入 characterised 漏网，见 CHANGELOG 一百九十三节）。
    # 只查 en 例句；词典外链 slug 与词表词形（catalog/favor 本身）不在此判据范围。
    bad = []
    for w, i, en, zh in pairs:
        for pat in BRITISH_EN_RES:
            m = pat.search(en)
            if m:
                bad.append((w, i, m.group(0)))
        m = BRITISH_EN_RE.search(en)
        if m:
            bad.append((w, i, m.group(0)))
    ok("en 无英式拼写（美式统一）", not bad, "%d 处" % len(bad))

    # ⑥ 释义域
    bad = []
    for x in words:
        senses = x.get("senses") or []
        if not senses or any(not s.strip() for s in senses):
            bad.append(x.get("word"))
    ok("每词 senses 非空", not bad, "%d 词" % len(bad))

    bad = [x.get("word") for x in words
           if len(set(x.get("senses") or [])) != len(x.get("senses") or [])]
    ok("同词 senses 互不相同", not bad, "%d 词" % len(bad))

    bad = []
    for x in words:
        for s in (x.get("senses") or []):
            if s != s.strip() or "  " in s:
                bad.append(x.get("word"))
                break
    ok("senses 无首尾空白与连续空格", not bad, "%d 词" % len(bad))

    # ⑦ 策展真源
    ok("curation version 为正整数",
       isinstance(cur.get("version"), int) and cur["version"] >= 1,
       str(cur.get("version")))

    bad = []
    for i, item in enumerate(cur.get("add") or []):
        senses = item.get("senses") if isinstance(item, dict) else None
        if not senses or any((not isinstance(s, str)) or not s.strip() for s in senses):
            bad.append("add#%d" % i)
    ok("curation 的 add 每条必有非空 senses", not bad, "%d 条" % len(bad))

    bad = []
    for section in ("fix", "recat"):
        for k, v in (cur.get(section) or {}).items():
            if not isinstance(v, dict) or "senses" not in v:
                continue        # recat 只改 pos/sub、fix 只改 notes/word 皆合法
            senses = v.get("senses")
            if not senses or any((not isinstance(s, str)) or not s.strip() for s in senses):
                bad.append(section + ":" + str(k))
    ok("curation 的 fix/recat 若带 senses 则非空", not bad, "%d 条" % len(bad))

    # ⑧ 全角括号内不留半角空格
    bad = []
    for x in words:
        for s in (x.get("senses") or []):
            if "（ " in s or " ）" in s:
                bad.append(x.get("word"))
                break
    ok("senses 全角括号内无半角空格", not bad, "%d 词" % len(bad))

    bad = [(w, i) for w, i, en, zh in pairs if "（ " in zh or " ）" in zh]
    ok("zh 全角括号内无半角空格", not bad, "%d 处" % len(bad))

    # ⑨ en 句侧括号与引号配对
    bad = []
    for w, i, en, zh in pairs:
        if en.count("(") != en.count(")") or en.count("“") != en.count("”") \
                or en.count('"') % 2:
            bad.append((w, i))
    ok("en 括号与引号配对", not bad, "%d 处" % len(bad))

    # ⑩ 挖空回退清单是正式回归的必需夹具：误删清单不能把检查静默降级成通过。
    audit_rel = os.path.join("tools", "_audit", "cloze_ineligible_84.json")
    audit_path = os.path.join(ROOT, audit_rel)
    audit_exists = os.path.exists(audit_path)
    ok("挖空回退清单文件存在", audit_exists, audit_rel)
    if audit_exists:
        with open(audit_path, encoding="utf-8") as f:
            allowed = set(x.get("word") for x in (json.load(f).get("words") or []))
        def has_surface(word, en):
            return re.search(r"(^|[^A-Za-z])" + re.escape(word) + r"(?![A-Za-z])",
                             en, re.I) is not None
        bad = []
        for w in words:
            word = w["word"]
            ens = [e.get("en", "") for e in ex.get(word, [])]
            if ens and not any(has_surface(word, en) for en in ens):
                if word not in allowed:
                    bad.append(word)
        ok("挖空回退清单覆盖全部无原形词", not bad, "%d 词未登记" % len(bad))

    print()
    if FAIL:
        print("RESULT: %d FAILURES" % len(FAIL))
        for f, _ in FAIL:
            print("  -", f)
        sys.exit(1)
    print("RESULT: ALL TESTS PASSED (%d checks passed)" % PASSED)


# 控制台输出钉 UTF-8（Windows GBK 控制台对 ✓/✗ 直接崩，见 _console_utf8.py）
from _console_utf8 import force_utf8_console  # noqa: E402

force_utf8_console()

if __name__ == "__main__":
    main()
