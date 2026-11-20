#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""内容域守卫的变异验证：改坏一处 ⇒ 必须红在预期那条断言上。

用法： python3 tools/content_mutation.py

做法（工装窗「改坏必红」的四步法）：
  ① 从仓库复制三份产物到临时目录（绝不碰工作树）
  ② 先跑一次 tools/content_test.py，确认基线绿
  ③ 注入一处定向破坏，再跑一次
  ④ 断言：退出码非 0，且**红掉的断言集合恰好等于**预期集合
     （既不能漏判，也不能误伤——红在别的条上同样算失败）

覆盖：本套件的每一条机械判据各有一处定向变异。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = ["data/examples.json", "data/words.json", "data/curation.json"]
# 挖空回退清单：内容域守卫的第 ⑩ 条要读它（见 content_test.py），
# 变异验证也得把它带进临时副本，否则那条检查在副本里是空转的。
AUDIT_REL = "tools/_audit/cloze_ineligible_84.json"
DATA.append(AUDIT_REL)
DELETE = object()  # 变异算子用：本轮换算子删除整个文件，而不是写 null JSON


def snapshot(root):
    out = {}
    for rel in DATA:
        with open(os.path.join(root, rel), encoding="utf-8") as f:
            out[rel] = json.load(f)
    return out


def run_guard(root):
    # 子进程 stdio 钉 UTF-8、父进程管道按 UTF-8 解码（errors=replace）。
    # 此前两侧都不指定：content_test.py 成功行打 ✓（U+2713，不在 GBK 内），
    # Windows 上子进程直接 UnicodeEncodeError 崩掉；即便子进程活下来，
    # 父进程按系统 locale（GBK）解码管道，读到 UTF-8 字节时读线程崩、
    # stdout=None ⇒ 本函数 AttributeError（2026-11-19 实测两种崩法都出现过）。
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    p = subprocess.run([sys.executable, os.path.join(HERE, "content_test.py"),
                        "--root", root], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    failed = set()
    for line in p.stdout.splitlines():
        line = line.strip()
        if line.startswith("- "):
            failed.add(line[2:].strip())   # 失败清单只印断言名，详情在上方
    return p.returncode, failed, (p.stdout or "") + (p.stderr or "")


# ---------- 变异算子：每个都改一处，且知道预期红在哪几条 ----------

def m_examples_count(s):
    ex = s["data/examples.json"]
    w = sorted(ex)[0]
    ex[w] = ex[w][:2]
    return {"每词恰 3 条例句"}


def m_empty_zh(s):
    ex = s["data/examples.json"]
    ex[sorted(ex)[0]][0]["zh"] = ""
    return {"每条例句 en/zh 均非空", "zh 以终止标点收尾"}


def m_drop_word(s):
    ex = s["data/examples.json"]
    del ex[sorted(ex)[0]]
    return {"词表与例句的词表键集一致"}


def m_lead_space(s):
    ex = s["data/examples.json"]
    ex[sorted(ex)[0]][0]["zh"] = " " + ex[sorted(ex)[0]][0]["zh"]
    return {"zh 无首尾空白"}


def m_no_zh_end(s):
    ex = s["data/examples.json"]
    e = ex[sorted(ex)[0]][0]
    e["zh"] = e["zh"].rstrip("。！？…」』）")
    return {"zh 以终止标点收尾"}


def m_no_en_end(s):
    ex = s["data/examples.json"]
    e = ex[sorted(ex)[0]][0]
    e["en"] = e["en"].rstrip(".!?")
    return {"en 以终止标点收尾"}


def m_zh_lead_punct(s):
    ex = s["data/examples.json"]
    e = ex[sorted(ex)[0]][0]
    e["zh"] = "，" + e["zh"]
    return {"zh 句首无标点"}


def m_zh_half_comma(s):
    ex = s["data/examples.json"]
    e = ex[sorted(ex)[0]][0]
    e["zh"] = e["zh"][:-1] + "," + e["zh"][-1]
    return {"zh 无半角 , ; :"}


def m_zh_double_space(s):
    ex = s["data/examples.json"]
    e = ex[sorted(ex)[0]][0]
    e["zh"] = e["zh"][:-1] + "  " + e["zh"][-1]
    return {"zh 无连续空格"}


def m_zh_quote(s):
    ex = s["data/examples.json"]
    e = ex[sorted(ex)[0]][0]
    e["zh"] = e["zh"][:-1] + '"' + e["zh"][-1]
    return {"zh 无半角引号"}


def m_zh_placeholder(s):
    ex = s["data/examples.json"]
    e = ex[sorted(ex)[0]][0]
    e["zh"] = e["zh"][:-1] + "TODO" + e["zh"][-1]
    return {"zh 无占位符残留"}


def m_zh_latin_residue(s):
    """在 zh 里塞一个**非专名**的英文词 ⇒ 必须红在「zh 无普通英文词残留」。
    用 material 而非 TODO：TODO 属占位符，由另一条断言单独负责。"""
    ex = s["data/examples.json"]
    e = ex[sorted(ex)[0]][0]
    e["zh"] = e["zh"][:-1] + "material" + e["zh"][-1]
    return {"zh 无普通英文词残留（专名缩写豁免）"}


def m_zh_keep_latin_exempt(s):
    """塞一个**专名缩写**（CONSORT）⇒ 必须**不红**（豁免判据不得误伤）。"""
    ex = s["data/examples.json"]
    e = ex[sorted(ex)[0]][0]
    e["zh"] = e["zh"][:-1] + "CONSORT" + e["zh"][-1]
    return set()   # 期望：仍然全绿


def m_zh_unbalanced(s):
    ex = s["data/examples.json"]
    w = sorted(ex)[0]
    for e in ex[w]:
        if "（" in e["zh"]:
            e["zh"] = e["zh"].replace("（", "（", 1).replace("）", "", 1)
            return {"zh 括号配对（）（「」《》）"}
    e = ex[w][0]
    e["zh"] = e["zh"][:-1] + "（x" + e["zh"][-1]
    return {"zh 括号配对（）（「」《》）"}


def m_same_word_zh(s):
    ex = s["data/examples.json"]
    w = sorted(ex)[0]
    ex[w][1]["zh"] = ex[w][0]["zh"]
    return {"同词 3 条 zh 互不相同", "全库 zh 句子互不重复"}


def m_same_word_en(s):
    ex = s["data/examples.json"]
    w = sorted(ex)[0]
    ex[w][1]["en"] = ex[w][0]["en"]
    return {"同词 3 条 en 互不相同", "全库 en 句子互不重复"}


def m_dup_zh(s):
    ex = s["data/examples.json"]
    ws = sorted(ex)
    ex[ws[1]][0]["zh"] = ex[ws[0]][0]["zh"]
    return {"全库 zh 句子互不重复"}


def m_dup_en(s):
    ex = s["data/examples.json"]
    ws = sorted(ex)
    ex[ws[1]][0]["en"] = ex[ws[0]][0]["en"]
    return {"全库 en 句子互不重复"}


def m_pct_mismatch(s):
    ex = s["data/examples.json"]
    for w in sorted(ex):
        for e in ex[w]:
            ens = re.findall(r"(\d+(?:\.\d+)?)\s*%", e["en"])
            if len(ens) == 1 and e["zh"].count("%") == 1 and ens[0] in e["zh"]:
                e["zh"] = e["zh"].replace(ens[0] + "%", "99%")
                return {"en 的百分数数值在 zh 中出现"}
    raise RuntimeError("找不到可用于百分数变异的例句")


def m_pct_substring(s):
    """5% → 15%：旧子串判断会假绿，完整数值 token 必须抓出。"""
    ex = s["data/examples.json"]
    for w in sorted(ex):
        for e in ex[w]:
            ens = re.findall(r"(\d+(?:\.\d+)?)\s*%", e["en"])
            if len(ens) != 1:
                continue
            value = ens[0]
            zh, n = re.subn(r"(?<![\d.])" + re.escape(value) + r"(?=\s*%)",
                            "1" + value, e["zh"], count=1)
            if n:
                e["zh"] = zh
                return {"en 的百分数数值在 zh 中出现"}
    raise RuntimeError("找不到可用于百分数子串变异的例句")


def m_year_mismatch(s):
    ex = s["data/examples.json"]
    for w in sorted(ex):
        for e in ex[w]:
            ys = re.findall(r"\b(1[89]\d{2}|20\d{2})\b", e["en"])
            if len(set(ys)) == 1 and ys[0] in e["zh"] and e["zh"].count(ys[0]) == 1:
                other = "1987" if ys[0] != "1987" else "1976"
                if other in e["en"]:
                    continue
                e["zh"] = e["zh"].replace(ys[0], other)
                return {"en 的四位年份在 zh 中出现"}
    raise RuntimeError("找不到可用于年份变异的例句")


def m_year_substring(s):
    """2020 → 12020：四位年份也不能靠子串命中。"""
    ex = s["data/examples.json"]
    for w in sorted(ex):
        for e in ex[w]:
            ys = re.findall(r"\b(1[89]\d{2}|20\d{2})\b", e["en"])
            if len(set(ys)) == 1 and ys[0] in e["zh"]:
                e["zh"] = e["zh"].replace(ys[0], "1" + ys[0], 1)
                return {"en 的四位年份在 zh 中出现"}
    raise RuntimeError("找不到可用于年份子串变异的例句")


def m_forbidden(s):
    ex = s["data/examples.json"]
    e = ex[sorted(ex)[0]][0]
    e["zh"] = e["zh"][:-1] + "先导测试" + e["zh"][-1]
    return {"禁译表零命中"}


def m_british(s):
    # 复现 r60 批的漏网：en 侧混入英式拼写（characterised），守卫必须红。
    ex = s["data/examples.json"]
    ex[sorted(ex)[0]][0]["en"] = (
        "The mechanism remains poorly characterised in the literature.")
    return {"en 无英式拼写（美式统一）"}


def m_british_false_amE(s):
    # 假绿反例：analyses 是美式合法词形（analysis 复数），守卫若把子串
    # analyse 一刀切就会误伤——变异注入 analyses 必须仍然绿（红=判据过严）。
    ex = s["data/examples.json"]
    ex[sorted(ex)[0]][0]["en"] = (
        "The journal requires reproducibility of computational analyses.")
    return set()


def m_senses_empty(s):
    w = s["data/words.json"]
    w[0]["senses"] = []
    return {"每词 senses 非空"}


def m_senses_dup(s):
    w = s["data/words.json"]
    for x in w:
        if len(x.get("senses") or []) >= 2:
            x["senses"] = [x["senses"][0], x["senses"][0]]
            return {"同词 senses 互不相同"}
    raise RuntimeError("找不到 senses 至少两条的词")


def m_senses_space(s):
    w = s["data/words.json"]
    w[0]["senses"] = [" " + w[0]["senses"][0]]
    return {"senses 无首尾空白与连续空格"}


def m_version_zero(s):
    s["data/curation.json"]["version"] = 0
    return {"curation version 为正整数"}


def m_add_senses_empty(s):
    c = s["data/curation.json"]
    c["add"][0]["senses"] = []
    return {"curation 的 add 每条必有非空 senses"}


def m_fix_senses_empty(s):
    c = s["data/curation.json"]
    for k, v in c["fix"].items():
        if "senses" in v:
            v["senses"] = []
            break
    return {"curation 的 fix/recat 若带 senses 则非空"}


def m_senses_paren_space(s):
    w = s["data/words.json"]
    for x in w:
        if any("（" in t for t in (x.get("senses") or [])):
            x["senses"] = [t.replace("（", "（ ", 1) for t in x["senses"]]
            return {"senses 全角括号内无半角空格"}
    raise RuntimeError("找不到含全角括号的释义")


def m_zh_paren_space(s):
    ex = s["data/examples.json"]
    for word, arr in ex.items():
        for e in arr:
            if "（" in e["zh"]:
                e["zh"] = e["zh"].replace("（", "（ ", 1)
                return {"zh 全角括号内无半角空格"}
    raise RuntimeError("找不到含全角括号的 zh 例句")


def m_en_unbalanced(s):
    ex = s["data/examples.json"]
    for word, arr in ex.items():
        for e in arr:
            if "(" not in e["en"]:
                # 只塞进左括号（不带右括号）⇒ 括号失配
                e["en"] = e["en"].replace(".", " (example.", 1)
                return {"en 括号与引号配对"}
    raise RuntimeError("找不到可加括号的 en 例句")


def m_cloze_audit_drop(s):
    a = s[AUDIT_REL]
    if not a["words"]:
        raise RuntimeError("回退清单是空的")
    a["words"] = a["words"][1:]          # 抹掉一个已登记词 ⇒ 该词变成未登记
    return {"挖空回退清单覆盖全部无原形词"}


def m_cloze_audit_missing(s):
    s[AUDIT_REL] = DELETE
    return {"挖空回退清单文件存在"}


MUTATIONS = [
    ("例句数不足", m_examples_count),
    ("zh 置空", m_empty_zh),
    ("例句表少一个词", m_drop_word),
    ("zh 首部多空格", m_lead_space),
    ("zh 去掉句末标点", m_no_zh_end),
    ("en 去掉句末标点", m_no_en_end),
    ("zh 句首多逗号", m_zh_lead_punct),
    ("zh 混入半角逗号", m_zh_half_comma),
    ("zh 混入连续空格", m_zh_double_space),
    ("zh 混入半角引号", m_zh_quote),
    ("zh 混入占位符", m_zh_placeholder),
    ("zh 混入普通英文", m_zh_latin_residue),
    ("zh 混入专名缩写不误伤", m_zh_keep_latin_exempt),
    ("zh 括号失配", m_zh_unbalanced),
    ("同词两条 zh 雷同", m_same_word_zh),
    ("同词两条 en 雷同", m_same_word_en),
    ("跨词 zh 雷同", m_dup_zh),
    ("跨词 en 雷同", m_dup_en),
    ("百分数数值对不上", m_pct_mismatch),
    ("百分数子串假绿", m_pct_substring),
    ("年份对不上", m_year_mismatch),
    ("年份子串假绿", m_year_substring),
    ("禁译回潮", m_forbidden),
    ("en 混入英式拼写", m_british),
    ("analyses 误伤反例", m_british_false_amE),
    ("某词 senses 清空", m_senses_empty),
    ("某词 senses 自雷同", m_senses_dup),
    ("senses 首部多空格", m_senses_space),
    ("curation version 归零", m_version_zero),
    ("add 条目 senses 清空", m_add_senses_empty),
    ("fix 条目 senses 清空", m_fix_senses_empty),
    ("senses 括号内多空格", m_senses_paren_space),
    ("zh 括号内多空格", m_zh_paren_space),
    ("en 括号失配", m_en_unbalanced),
    ("回退清单少一词", m_cloze_audit_drop),
    ("回退清单整份缺失", m_cloze_audit_missing),
]


def main():
    tmp = tempfile.mkdtemp(prefix="wl-content-mut-")
    try:
        for rel in DATA:
            dst = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(ROOT, rel), dst)

        rc, failed, out = run_guard(tmp)
        if rc != 0:
            print("✗ 基线不绿，终止：\n" + out)
            return 1
        print("✓ 基线绿（%s）" % out.strip().splitlines()[-1])

        pristine = snapshot(tmp)
        bad = 0
        for name, fn in MUTATIONS:
            for rel, payload in pristine.items():
                with open(os.path.join(tmp, rel), "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
            snap = snapshot(tmp)
            try:
                expected = fn(snap)
            except RuntimeError as exc:
                print("  ✗ %-22s 变异算子失败：%s" % (name, exc))
                bad += 1
                continue
            for rel, payload in snap.items():
                path = os.path.join(tmp, rel)
                if payload is DELETE:
                    if os.path.exists(path):
                        os.remove(path)
                else:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(payload, f, ensure_ascii=False, indent=2)
            rc, failed, out = run_guard(tmp)
            if not expected:
                # 负向对照（防误伤）：注入的是美式合法词形，要求守卫**仍绿**。
                if rc == 0:
                    print("  ✓ %-22s 守卫未误伤（仍绿）" % name)
                else:
                    print("  ✗ %-22s 预期仍绿，实际红 %s（rc=%s）"
                          % (name, "、".join(sorted(failed)) or "无", rc))
                    bad += 1
            elif rc != 0 and failed == set(expected):
                print("  ✓ %-22s 红在 %s" % (name, "、".join(sorted(failed))))
            else:
                print("  ✗ %-22s 预期红 %s，实际红 %s（rc=%s）"
                      % (name, "、".join(sorted(expected)),
                         "、".join(sorted(failed)) or "无", rc))
                bad += 1
        print()
        if bad:
            print("RESULT: %d FAILURES" % bad)
            return 1
        print("RESULT: ALL TESTS PASSED (%d mutations verified)" % len(MUTATIONS))
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    # 本进程控制台输出钉 UTF-8：✓/✗ 在 Windows GBK 控制台上会直接
    # UnicodeEncodeError（被测子进程两端的编码已在 run_guard 里钉死）。
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    sys.exit(main())
