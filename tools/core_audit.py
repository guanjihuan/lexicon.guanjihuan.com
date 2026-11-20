#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core_audit.py —— 学术核心高频分层的机械比对器(册卅三轮引入,只读分析、不改数据)。

读 data/words.json + data/freq_refs.json,按词族前缀/不规则形展开比对,
产出提案表 data/core_proposals.json(逐词:信号 + 提案)。
提案只是机械信号,**最终归属一律以 data/core_decisions.json 逐词复核定稿**,
由 tools/_gen_core.py 翻译成 curation.json 的 core/noncore 段。
重跑本脚本会整体覆盖 core_proposals.json;请勿手改提案文件。

用法: python3 tools/core_audit.py
"""
import json, os, re, sys

# 控制台输出钉 UTF-8（Windows GBK 控制台上中文报错会变 mojibake，见 _console_utf8.py）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _console_utf8 import force_utf8_console  # noqa: E402
force_utf8_console()

# 严格 JSON 读取：重复键必须报错（标准库会静默覆盖，人写的 JSON 易踩）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _strict_json import load_json, require_curation_segments  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORDS_F = os.path.join(ROOT, "data", "words.json")
REFS_F = os.path.join(ROOT, "data", "freq_refs.json")
OUT_F = os.path.join(ROOT, "data", "core_proposals.json")
CURATION_F = os.path.join(ROOT, "data", "curation.json")

# 不规则派生形 → 词族 head(前缀展开覆盖不到的)
IRREGULAR = {
    "analyses": "analyse", "analysis": "analyse",
    "hypotheses": "hypothesis", "theses": "thesis", "crises": "crisis",
    "criteria": "criterion", "phenomena": "phenomenon", "media": "medium",
    "indices": "index", "matrices": "matrix", "appendices": "appendix",
    "formulas": "formula", "stimuli": "stimulus", "syntheses": "synthesis",
    "bases": "basis", "axes": "axis", "data": "datum", "formats": "format",
    "indexes": "index", "schemata": "schema", "automata": "automaton",
}
# 常见派生后缀:剥掉后再试前缀匹配(如 constraints→constraint)
SUFFIXES = ("ations", "ities", "ments", "ness", "ions", "ion", "ies",
            "ied", "ing", "ers", "ist", "ism", "ed", "es", "al", "ly", "s")


def norm(w):
    return w.strip().lower()


def strip_hyphen(w):
    return w.replace("-", " ").strip()


def fam_match(word, heads, ordered=None):
    """词族匹配:精确 / 不规则 / 前缀(head 是 word 前缀,视为同族派生形)。
    返回命中的 head 或 None。前缀匹配要求 head 长度>=4,且 word 更长时
    超出部分不超过 6 个字符(防 particle 误配 part 之外的长尾假阳)。

    `heads` 必须是集合(供 O(1) 成员判定),`ordered` 是同一批 head 的**定序列表**
    (长度降序、同长按字典序)。前缀匹配一律按 ordered 走:集合的迭代顺序随
    PYTHONHASHSEED 变,同一次运行的两次重跑会把同一个词配到不同的 head
    (standardize → stand / standard、rationale → ratio / rational),
    于是提案文件的字节在两次重跑之间不一致 —— 生成物不可复现,且归属可能配错。"""
    w = norm(word)
    if w in heads:
        return w
    if w in IRREGULAR and IRREGULAR[w] in heads:
        return IRREGULAR[w]
    base = strip_hyphen(w)
    if base in heads:
        return base
    for s in SUFFIXES:
        if len(w) > len(s) + 3 and w.endswith(s):
            stem = w[: -len(s)]
            if stem in heads:
                return stem
            if stem + "e" in heads:
                return stem + "e"
    for h in (ordered if ordered is not None
              else sorted(heads, key=lambda x: (-len(x), x))):
        if len(h) >= 4 and w.startswith(h) and 0 < len(w) - len(h) <= 6:
            return h
        if len(h) >= 4 and h.startswith(w) and 0 < len(h) - len(w) <= 4 and False:
            return h  # word 是 head 前缀:过泛,禁用
    return None


def main():
    # argv[1] 可选:替代词表快照路径(HEAD 沙箱调参用;正式跑一律吃工作区)
    wf = sys.argv[1] if len(sys.argv) > 1 else WORDS_F
    alt = len(sys.argv) > 1
    # 早先的 bug:无论用哪份词表,提案都写死 OUT_F(=data/core_proposals.json)——
    # 拿一份 10 词的沙箱快照调参,就把仓库里那份已提交产物覆盖成了 10 行
    # (README 写的是「只读分析」,实际上它是个写手)。
    # 现在:给了替代词表 ⇒ 提案写到**该快照旁边**的 core_proposals.snapshot.json,
    # 仓库里已提交的产物一个字节都不动。
    out_f = (os.path.join(os.path.dirname(os.path.abspath(wf)),
                          "core_proposals.snapshot.json") if alt else OUT_F)
    words = load_json(wf)
    refs = load_json(REFS_F)
    cur = load_json(CURATION_F)
    # 段完整性闸（第八轮）：add 段缺失时 added 集合为空，提案里逐词的 origin
    # 会被判成 src800 —— 提案表因此与现行词表脱节却毫无提示。缺段即报错。
    require_curation_segments(cur, ('add',))
    added = {a["word"].strip().lower() for a in cur.get("add", [])}
    awl = {norm(h) for h in refs["awl_heads"] if not h.startswith("_")}
    skel = {norm(h) for h in refs["academic_skeleton"] if not h.startswith("_")}
    # general_highfreq(通用高频学术承载层)并入骨架信号,单独记 gh 标志
    gh = {norm(h) for h in refs.get("general_highfreq", []) if not h.startswith("_")}
    skel |= gh
    chunks = {norm(c) for c in refs["chunks"] if not c.startswith("_")}
    # 前缀匹配用的定序 head 列表（长度降序 → 更具体的词族优先）：
    # standardize 配 standard（而非偶然同前缀的 stand）、rationale 配 rational。
    awl_ordered = sorted(awl, key=lambda h: (-len(h), h))
    skel_ordered = sorted(skel, key=lambda h: (-len(h), h))

    rows, agg = [], {}
    for w in words:
        lw = norm(w["word"])
        is_chunk = " " in lw or lw in chunks
        chunk_hit = lw in chunks
        awl_head = fam_match(lw, awl, awl_ordered)
        skel_head = fam_match(lw, skel, skel_ordered)
        hit = chunk_hit or awl_head or skel_head
        if is_chunk and not chunk_hit:
            hit = fam_match(strip_hyphen(lw), awl, awl_ordered) or fam_match(strip_hyphen(lw), skel, skel_ordered) or hit
        current_core = bool(w.get("core"))
        origin = "added" if (lw in added or w["num"] > 800) else "src800"
        proposal = "core" if hit else "noncore"
        if proposal == "core" and not current_core:
            flag = "promote?"
        elif proposal == "noncore" and current_core:
            flag = "demote?"
        else:
            flag = "agree"
        # 高频通用词在学术文本功能载荷低的,机械无法判,交给复核:
        # 无任何命中又无人工增补背景的词 → noncore 提案;命中的 → core 提案。
        rows.append({
            "word": w["word"], "num": w["num"], "pos": w.get("pos"),
            "sense": (w.get("senses") or [""])[0], "origin": origin,
            "current_core": current_core, "chunk": bool(chunk_hit),
            "awl": awl_head, "skel": skel_head,
            "proposal": proposal, "flag": flag,
        })
        agg[(proposal, flag)] = agg.get((proposal, flag), 0) + 1

    prop_core = sum(1 for r in rows if r["proposal"] == "core")
    summary = {
        "total": len(rows),
        "proposal_core": prop_core,
        "proposal_core_pct": round(100.0 * prop_core / len(rows), 1),
        "current_core": sum(1 for r in rows if r["current_core"]),
        "promote_candidates": agg.get(("core", "promote?"), 0),
        "demote_candidates": agg.get(("noncore", "demote?"), 0),
        "agree_core": agg.get(("core", "agree"), 0),
        "agree_noncore": agg.get(("noncore", "agree"), 0),
        "generated_by": "tools/core_audit.py (机械信号;定稿看 core_decisions.json)",
    }
    # 原子写（与其余写手同规）：写一半崩溃不留半截提案文件。
    # 该文件是「机械提案」生成物，崩了就当没有，下次重跑即可。
    tmp = out_f + '.tmp'
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"_summary": summary, "rows": rows}, f, ensure_ascii=False, indent=1)
    os.replace(tmp, out_f)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print("written:", out_f if alt else os.path.relpath(out_f, ROOT))
    if alt:
        print("note: 用了替代词表快照，已提交的 data/core_proposals.json 未被改动")


if __name__ == "__main__":
    main()
