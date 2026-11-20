#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""词性标注一致性扫描器（只读、零写盘；退出码恒 0，审计建议不阻断）。

口径（册六十五轮裁定 2026-11-18）：
  A. null 族 = **介词及介词性固定语块**（纯介词性）。判据：单词介词，或多词且
     **末词为介词**的支配性介词短语。篇章副词（on the one hand）与从属连词
     （for fear that / to the end that / such as）不再进 null 族——它们各有实义词性，
     应进词性索引。此前的 null 族是「介词短语 ∪ 固定篇章语块」混合族，同一构造
     （on the one hand ↔ on the other hand）被劈成两半，是本轮要修的病根。
  B. 对称构造对必须同词性（对称＝同一语法构造的两面）。
  C. 台账理由（core_decisions.json）里点名的词性必须与所标词性一致
     （「连接词」在台账里是泛称，可指连词或篇章副词，故两可）。
  D. 形态后缀与词性大体一致（-ly→副词、-tion/-ment/-ness/-ity/-ance/-ence→名词、
     -ed/-ing→形容词/动词/名词性动名词），例外逐条列明。
  E. **反向检查**（册六十八轮补）：A 段只单向验「null 族是否介词性」，
     查不出「本该是介词却标了实义词性」的漂移。E 段把库里**词典上是单词介词、
     本库却标了实义词性**的词全部列出，并区分两类：
       · 合规——释义已注明兼类介词用法（主用法归实义词性，如 besides / notwithstanding）；
       · 待判读——释义只登记了介词性义项，却带实义词性标签（改判 null 的候选）。
     E 段只作提示，不阻断（与本工装「审计建议不阻断」的总口径一致）。

用法：python3 tools/pos_consistency_audit.py [data/words.json]
"""
import json
import os
import re
import sys

# 控制台输出钉 UTF-8（Windows GBK 控制台上中文报错会变 mojibake，见 _console_utf8.py）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _console_utf8 import force_utf8_console  # noqa: E402
force_utf8_console()

# 严格 JSON 读取（与全仓其余工具同规）：重复键必须报错，
# 否则这里会静默吃下 words.json 里的重复键、给出与实际词表不符的审计结论
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _strict_json import load_json  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# A. null 族的介词性判据
# ---------------------------------------------------------------------------
# 可作介词（或支配 NP 的介词性框架词）者。末词判据用这一张表；
# "as" 特意不在表内：「such as」的 as 是比较连词、不是介词，
# 放行它会让「篇章固定语块」重新混进 null 族。
PREP_TAIL = {
    "to", "of", "with", "from", "by", "on", "in", "for", "at", "than",
    "into", "onto", "upon", "over", "under", "through", "during", "without",
    "within", "off", "out", "against", "between", "about", "per", "like",
    "near", "till", "until", "worth", "besides", "beyond", "beneath",
    "throughout", "underneath", "alongside", "versus", "despite",
    "regarding", "concerning", "following", "via", "save", "despite",
}
# 单词介词（无末词可判，单独一张表）
PREP_SINGLE = {
    "via", "onto", "despite", "regarding", "versus", "concerning",
    "following", "besides", "like", "near", "unlike", "plus", "save",
    "worth", "per", "through", "throughout", "despite",
    # 册六十六轮：given / barring 入 null 的依据是**本库例句的介词性主用法**
    # （Given + NP 2/3、Barring + NP 3/3，= 介词短语），不是词形判据；
    # LDOCE/MW 亦标 preposition。as regards 不在此列：其主用法虽同形，
    # 但末词 regards 词形为动词，册六十五轮已裁定按篇章副词放行，勿回改。
    "given", "barring",
    # 册六十七轮（词汇增补·连词与连接语块批）：during / following 单词介词
    # （与 via/despite 同档；following 尾形 -ing 与 regarding 同族）
    "during", "following",
    # 册六十八轮：notwithstanding 词典上标 preposition（亦有副词用法），
    # 本库主用法＝副词、介词用法写进释义，故不进 null 族（E 段反向检查用）
    "notwithstanding",
    # 册六十九轮：considering 入 null 的依据同 given / like——本库例句 2/3 为
    # Considering + NP（介词性），连词职能由库内 considering that 承担；
    # MW / Collins 亦以 preposition 为首义项
    "considering",
}
# 册六十八轮：单词介词**按主用法归实义词性**者——词典上是介词，但本库词条
# 的首个义项是副词/连词等实义用法，介词用法只作兼类写进释义（besides
# 「而且；此外；除…之外（介词用法）」即此档）。它们**留在实义词性索引里**、
# 不进 null 族；列在 PREP_SINGLE 里只为 E 段反向检查时能认出「这是介词」，
# 别把它们当成漏网的 null 候选。notwithstanding 同档（副词主用法，介词用法入释义）。
# 释义里注明了介词用法 → 兼类已交代，E 段判为合规。
GLOSS_PREP_MARK = ("介词", "前置词")

# ---------------------------------------------------------------------------
# B. 对称构造对：两面必须是同一个词性
# ---------------------------------------------------------------------------
# 每对都是「同一语法构造的两面」或「同族同功能的一对」，
# 判不同的即缺陷（例：on the one hand 曾置 null 而 on the other hand 标副词）。
PAIRS = [
    ("on the one hand", "on the other hand"),
    ("for fear that", "lest"),
    ("to the end that", "in order that"),
    ("other than", "rather than"),
    ("other than", "instead of"),
    ("such as", "as well as"),
    ("such as", "as"),
    ("both", "not only"),   # 册六十六轮：关联结构 both…and ↔ not only…but also 前半须同词性
    ("then", "so"),
    ("then", "yet"),
    ("then", "even"),
    ("even so", "in any event"),
    ("even so", "at any rate"),
    ("considering that", "given that"),
    ("due to", "owing to"),
    ("because of", "thanks to"),
    ("with regard to", "with respect to"),
    ("by reference to", "with reference to"),
    ("in accordance with", "in conjunction with"),
    ("on the basis of", "on account of"),
    ("as long as", "so long as"),
    ("even if", "even though"),
    ("even when", "even though"),
    ("in order that", "so that"),
]

# ---------------------------------------------------------------------------
# B′. 有意不同词性的一对（不是缺陷，是区分点）——列此只为免得下轮被人「顺手对齐」
# ---------------------------------------------------------------------------
# 带介词的版本支配后接 NP（介词短语，null 族）；裸版本是篇章状语（副词）。
# 册四十二、卅八轮逐条核过例句后定下的区分，本轮沿用。
ASYMMETRIC = [
    ("as a result of", "as a result"),
    ("in addition to", "in addition"),
    ("in contrast to", "in contrast"),
    ("because of", "because"),
    ("in order to", "in order that"),
    ("so as to", "so that"),
]

# ---------------------------------------------------------------------------
# C. 台账理由里点名的词性 → 所标词性必须相符
# ---------------------------------------------------------------------------
REASON_POS = [
    ("名词", {"名词"}),
    ("动词", {"动词"}),
    ("形容词", {"形容词"}),
    ("副词", {"副词"}),
    ("连词", {"连词"}),
    # 台账里的「连接词」是泛称：篇章副词（at last / namely）也叫连接词
    ("连接词", {"连词", "副词"}),
    ("介词", {"介词"}),
]

# ---------------------------------------------------------------------------
# D. 形态 → 词性
# ---------------------------------------------------------------------------
# 例外逐条列明（词形看着像某类、实则不是），避免误报
LY_EXCEPT = {"apply", "likely", "comply", "imply", "anomaly",
             "monopoly", "scholarly"}  # 册六十六轮：-ly 结尾的名词（monopolies 复数），与 anomaly 同档；册六十九轮：scholarly 是 -ly 结尾的形容词（与 likely 同档）
NOMINAL_EXCEPT = {
    "comment", "witness", "cement", "complement", "implement", "harness",
    "augment", "document", "commence", "advance", "enhance", "hence",
}
PARTICIPLE_EXCEPT = {
    "notwithstanding",  # 副词（作介词，后接名词）
    "indeed",           # 副词
    "regarding",        # 介词
    "supposing", "assuming", "presuming", "barring",  # -ing 形连词
    # 册六十七轮（词汇增补·连词与连接语块批）：-ed/-ing 形连词（引导条件/让步从句，
    # 与 supposing 族同档）与 -ing 形介词 following（册六十七轮 null）
    "provided", "providing", "following", "during",
    # 册六十九轮：considering 改判 null（介词性主用法），-ing 形介词
    "considering",
}
NOMINAL_SUFFIX = re.compile(r"(tion|ment|ness|ity|ance|ence)$")
PARTICIPLE_SUFFIX = re.compile(r"(ed|ing)$")


def audit_null_family(words):
    """null 族是否仍是纯介词性。"""
    findings = []
    for w in words:
        if w.get("pos"):
            continue
        name = w["word"].strip()
        parts = name.split()
        if len(parts) == 1:
            if name.lower() not in PREP_SINGLE:
                findings.append((name, "单词非介词"))
        elif parts[-1].lower() not in PREP_TAIL:
            findings.append((name, "末词非介词（不是支配性介词短语）"))
    return findings


def audit_pairs(words):
    """对称构造对是否同词性。"""
    pos = {w["word"]: w.get("pos") for w in words}
    findings = []
    for a, b in PAIRS:
        if a not in pos or b not in pos:
            continue
        if pos[a] != pos[b]:
            findings.append((a, pos[a], b, pos[b]))
    return findings


def audit_reasons(words, decisions):
    """台账理由点名的词性与所标词性是否相符。"""
    findings = []
    for w in words:
        reason = (decisions.get(w["word"], {}) or {}).get("reason", "") or ""
        hits = set()
        for kw, allowed in REASON_POS:
            if kw in reason:
                hits |= allowed
        if not hits:
            continue
        p = w.get("pos")
        if hits == {"介词"}:
            ok = p is None
        elif "介词" in hits:
            continue  # 理由同时点了介词与别的类，措辞本身有歧义，交人工
        else:
            ok = p in hits
        if not ok:
            findings.append((w["word"], p, sorted(hits), reason))
    return findings


def audit_morphology(words):
    """形态后缀与词性是否大体一致。"""
    findings = []
    for w in words:
        name = w["word"]
        if " " in name:
            continue
        p = w.get("pos")
        low = name.lower()
        if low.endswith("ly") and p != "副词" and low not in LY_EXCEPT:
            findings.append((name, p, "-ly 词形应为副词"))
        elif (NOMINAL_SUFFIX.search(name) and p != "名词"
              and low not in NOMINAL_EXCEPT):
            findings.append((name, p, "-tion/-ment/-ness/-ity/-ance/-ence 词形应为名词"))
        elif (PARTICIPLE_SUFFIX.search(name) and p in ("副词", "连词", None)
              and low not in PARTICIPLE_EXCEPT):
            findings.append((name, p, "-ed/-ing 词形应为形容词/动词/动名词"))
    return findings


def audit_prep_words(words):
    """反向检查（E 段）：词典上是单词介词、库里却标了实义词性的词。

    A 段只单向验 null 族，查不出「本该是介词却标成别的词性」的漂移。
    这里把这类词全列出来并分流：
      · 合规——释义已注明兼类介词用法（主用法归实义词性，如 besides / notwithstanding）；
      · 待判读——释义没有介词用法说明（若义项本身就全是介词性，便是改判 null 的候选）。
    只作提示，不阻断。
    """
    ok, suspect = [], []
    for w in words:
        name = w["word"].strip()
        if " " in name:
            continue
        if name.lower() not in PREP_SINGLE:
            continue
        p = w.get("pos")
        if not p:
            continue                      # 已在 null 族，A 段已管
        senses = " ".join(w.get("senses", []))
        marked = any(mark in senses for mark in GLOSS_PREP_MARK)
        row = (name, p, senses[:46])
        (ok if marked else suspect).append(row)
    return ok, suspect


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "words.json")
    words = load_json(path)
    dec_path = os.path.join(ROOT, "data", "core_decisions.json")
    decisions = {}
    if os.path.exists(dec_path):
        decisions = load_json(dec_path).get("decisions", {})

    null_family = sorted(w["word"] for w in words if not w.get("pos"))

    a = audit_null_family(words)
    b = audit_pairs(words)
    c = audit_reasons(words, decisions)
    d = audit_morphology(words)
    e_ok, e_suspect = audit_prep_words(words)

    print("null 族（介词及介词性固定语块，%d 词）：" % len(null_family))
    print("  " + "、".join(null_family))

    print("\nA. null 族构成（应全为介词性；每词末词须是介词，单词须是介词）：")
    if a:
        for name, why in a:
            print("  ✗ %-24s %s" % (name, why))
    else:
        print("  ✓ 全部 %d 条均为介词性，无篇章语块混入" % len(null_family))

    print("\nB. 对称构造对（两面须同词性）：")
    if b:
        for x, px, y, py in b:
            print("  ✗ %-20s(%s)  vs  %-20s(%s)" % (x, px or "null", y, py or "null"))
    else:
        print("  ✓ %d 对全部一致" % len(PAIRS))

    print("\nB′. 有意不同词性的一对（介词短语支配后接 NP vs 篇章状语，非缺陷）：")
    for x, y in ASYMMETRIC:
        px = next((w.get("pos") for w in words if w["word"] == x), "?")
        py = next((w.get("pos") for w in words if w["word"] == y), "?")
        print("  · %-18s(%-4s)  vs  %-18s(%s)" % (x, px or "null", y, py or "null"))

    print("\nC. 台账理由点名的词性 vs 所标词性：")
    if c:
        for name, p, hits, reason in c:
            print("  ✗ %-24s pos=%-6s 理由点名=%-14s | %s" % (name, p or "null", hits, reason))
    else:
        print("  ✓ 无冲突")

    print("\nD. 形态后缀 vs 词性：")
    if d:
        for name, p, why in d:
            print("  ✗ %-24s pos=%-6s %s" % (name, p or "null", why))
    else:
        print("  ✓ 无冲突")

    print("\nE. 反向检查（词典上是单词介词、本库却标了实义词性者）：")
    for name, p, senses in e_ok:
        print("  · %-20s(%-4s) 合规：释义已注明兼类介词用法 | %s" % (name, p, senses))
    for name, p, senses in e_suspect:
        print("  ? %-20s(%-4s) 待判读：释义未注明介词用法 | %s" % (name, p, senses))
    if not e_ok and not e_suspect:
        print("  ✓ 无此类词（库里所有单词介词都在 null 族）")
    elif not e_suspect:
        print("  ✓ %d 词兼类已交代，无待判读项" % len(e_ok))

    print("\n合计：A %d / B %d / C %d / D %d；全库 %d 词，分类 %d，null %d（介词与介词短语）"
          % (len(a), len(b), len(c), len(d), len(words),
             sum(1 for w in words if w.get("pos")), len(null_family)))
    return 0


# 控制台输出钉 UTF-8（Windows GBK 控制台对 ✓/✗ 直接崩，见 _console_utf8.py）
from _console_utf8 import force_utf8_console  # noqa: E402

force_utf8_console()

if __name__ == "__main__":
    sys.exit(main())
