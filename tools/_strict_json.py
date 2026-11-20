#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""严格 JSON 读取：重复键报错 ＋ 段结构闸（第八轮新增）。

一、重复键：同一个对象里出现**重复键**时必须报错，不能静默取最后一个。

标准库 json.load 对重复键的默认行为是「后写的覆盖先写的」，全程无任何提示。
本仓库的 curation.json（fix 段为手工维护）、core_decisions.json（逐词台账）
与 examples_parts/*.json（手写分批）都是**人写的 JSON**，重复键完全可能发生；
一旦发生，下一个 _gen_*.py 重跑就会把整个文件改写掉，那一条记录**无声消失**，
没有任何闸门会拦（此前 core_audit.py 已因此清过一次重复键，见 bba0034）。

用法： from _strict_json import load_json
       data = load_json('data/curation.json')
（脚本以 `python3 tools/xxx.py` 运行，脚本所在目录在 sys.path 上，故可直接 import）
"""
import difflib
import json
import sys

# 控制台输出钉 UTF-8（Windows GBK 控制台上中文报错会变 mojibake，见本目录 _console_utf8.py）
try:
    from _console_utf8 import force_utf8_console
    force_utf8_console()
except ImportError:
    pass   # 被人单独拷走用时没有助手模块，退回系统默认（消息仍可读，只是可能乱码）


def _reject_duplicate_keys(pairs):
    """object_pairs_hook：同一层出现重复键即抛错。"""
    seen = set()
    for k, _v in pairs:
        if k in seen:
            raise ValueError('duplicate key %r' % k)
        seen.add(k)
    return dict(pairs)


def load_json(path, **kw):
    """读 JSON；遇到重复键立刻以友好报错退出（退出码 1，绝不写盘）。

    三类失败必须分开报，否则会把人引向错误的排查方向（实测踩过）：
      * 文件不存在 → 「路径不对 / 上游步骤没跑」，不是 JSON 的问题；
      * 语法错误（多一个逗号、括号没配对）→ 报语法错误，**不能**说成重复键
        （JSONDecodeError 是 ValueError 的子类，早先的 except ValueError
         会把语法错误也套上「重复键」的外壳，害人去查一个根本不存在的重复键）；
      * 重复键 → 报重复键。
    """
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f, object_pairs_hook=_reject_duplicate_keys, **kw)
    except FileNotFoundError:
        sys.exit('FAILED: %s: 文件不存在。\n'
                 '        请确认在仓库根目录运行（脚本读的是仓库内的相对路径），'
                 '或先跑生成该文件的上游步骤。' % path)
    except IsADirectoryError:
        sys.exit('FAILED: %s: 这是一个目录，不是 JSON 文件。' % path)
    except json.JSONDecodeError as e:
        sys.exit('FAILED: %s: JSON 语法错误：%s\n'
                 '        这不是重复键（重复键另有提示），请检查逗号/引号/括号是否配对。'
                 % (path, e))
    except ValueError as e:
        sys.exit('FAILED: %s: %s\n'
                 '        JSON 里出现了重复键：标准库会静默用后一个覆盖前一个，'
                 '请先消歧再跑流水线。' % (path, e))


# ------------------------------------------------------------------
# 二、段完整性闸（第八轮新增）：curation.json 是**人写**的 JSON，段名打错、
# 整段丢失、段类型写错都可能发生。各工具此前一律用 .get(段, 默认值) 兜底，
# 于是缺段会**静默**换一套口径、产出完全不同的词表（隔离树实测，退出码全是 0）：
#     丢 recat 段    → 分类 2158 → 1896（262 词悄悄没了词性/感情色彩标注）
#     丢 core 段     → 核心层 1060 → 968（92 个显式提入的词悄悄降级）
#     丢 noncore 段  → 核心层 1060 → 2045（985 个显式排除的词悄悄回核）
# 「段不存在」与「段为空」必须区分：空数组＝确实没有覆盖，缺段＝口径不明。
# 各生成器都会写出全部七段（_gen_core 必写 core/noncore、_gen_sentiment 必写 sentiment），所以缺段一定是
# 人为事故（手改 JSON 时打错段名、重写脚本时漏掉一段），报错远好过静默改口径。
CURATION_SEGMENTS = {
    'remove':  (list, '删词表（词形列表）'),
    'fix':     (dict, '改名/改释义/改注解（键＝原词形）'),
    'recat':   (dict, '词性/感情色彩（键＝词形）'),
    'add':     (list, '增补词（词条对象列表）'),
    'core':    (list, '显式提入核心层（词形列表）'),
    'noncore': (list, '显式排除出核心层（词形列表）'),
    'sentiment': (dict, '感情色彩/语体色彩逐词裁定（键＝词形，值＝{"sub":…,"reg":…}）'),
}
# 非段键：_comment 是自由注释、version 是清单版本号，都不算「无法识别的段」
CURATION_META_KEYS = ('_comment', 'version')


def require_curation_segments(cur, required, where='data/curation.json'):
    """段完整性闸：缺段 / 段类型不对 ⇒ 立刻以友好报错退出（退出码 1，绝不写盘）。

    `required`＝本脚本真正要读的段名（各脚本读的段不同，不必一刀切；
    整条九步生成链里 curation.json 永远带齐七段）。
    返回无法识别的段名列表——未知段只**警告**不拦（可能真是新加的段，由人判断）。
    """
    if not isinstance(cur, dict):
        sys.exit('FAILED: %s: 顶层必须是对象（段名→内容的映射），实际是 %s。'
                 % (where, type(cur).__name__))
    missing = [k for k in required if k not in cur]
    wrong = []
    for k in required:
        if k in cur and not isinstance(cur[k], CURATION_SEGMENTS[k][0]):
            wrong.append('%s（应是 %s，实际 %s）'
                         % (k, CURATION_SEGMENTS[k][0].__name__, type(cur[k]).__name__))
    if missing or wrong:
        detail = []
        if missing:
            detail.append('缺少段: %s' % '、'.join(missing))
        if wrong:
            detail.append('段类型不对: %s' % '；'.join(wrong))
        sys.exit('FAILED: %s %s\n'
                 '        curation.json 是人写的 JSON：段名打错或整段丢失时，工具会**静默**换一套\n'
                 '        口径、产出完全不同的词表（实测：丢 recat 段→分类 2158 变 1896；丢 noncore 段→\n'
                 '        核心层 1060 变 2045，两次退出码都是 0）。\n'
                 '        若确实不要某一段，请写成空数组/空对象，而不是把它删掉。\n'
                 '        段名对照: %s'
                 % (where, '；'.join(detail),
                    '、'.join('%s＝%s' % (k, d) for k, (_t, d) in CURATION_SEGMENTS.items())))
    unknown = [k for k in cur if k not in CURATION_SEGMENTS and k not in CURATION_META_KEYS]
    for u in unknown:
        hint = difflib.get_close_matches(u, list(CURATION_SEGMENTS), n=1, cutoff=0.6)
        print('WARN: %s 里有无法识别的段 %r%s（该段不会被任何工具读取；'
              '若不是新加的段，多半是拼错了）'
              % (where, u, ('，是否想写 %r？' % hint[0]) if hint else ''),
              file=sys.stderr)
    return unknown
