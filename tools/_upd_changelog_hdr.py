# -*- coding: utf-8 -*-
"""更新 CHANGELOG.md 头部「记录进度」行的三数与「已落」清单。

用法：
  python3 tools/_upd_changelog_hdr.py                       # 只按现文件重算三数
  python3 tools/_upd_changelog_hdr.py "二百零六" "本节标题"  # 重算三数并把本节登记进「已落」清单

要点：
  ① 三数（`^## ` 行数 / 编号节数 / 最大编号）**从当前文件实算**，不靠累加，
     避免并发轮次各自累加导致对不上；中文节号由文件里实际出现的最大编号推出。
  ② 只重写头部那一行的三处数字与清单尾部，不重排整行、不动历史节正文。
  ③ 顺序：**先追加节正文，再跑本脚本**；脚本不增删正文节。
  ④ 插入点用固定锚点（「八十八」补录条 / 「最新一节见文末」），不依赖任何一节的具体措辞。
  ⑤ 幂等：节号与文件实际最大编号不符时直接报错退出，不会写坏头部。
"""
import io
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

P = 'CHANGELOG.md'

CN_DIGIT = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9}
CN_UNIT = {'十': 10, '百': 100, '千': 1000}


def cn2int(s):
    """中文节号 → 整数（支持到万位，例如 二百零五 → 205）。"""
    total, num = 0, 0
    for ch in s:
        if ch in CN_DIGIT:
            num = CN_DIGIT[ch]
        elif ch in CN_UNIT:
            total += (num or 1) * CN_UNIT[ch]
            num = 0
        elif ch == '万':
            total = (total + num) * 10000
            num = 0
        else:
            raise ValueError('无法解析的中文节号字符：%r' % ch)
    return total + num


def int2cn(n):
    """整数 → 中文节号（与文件里的写法一致，例如 205 → 二百零五）。"""
    assert 0 < n < 100000, '节号超出支持范围：%r' % n
    digits = '零一二三四五六七八九'
    if n < 10:
        return digits[n]
    if n < 20:
        return '十' + (digits[n % 10] if n % 10 else '')
    if n < 100:
        head, rest = divmod(n, 10)
        s = digits[head] + '十'
        return s + (digits[rest] if rest else '')
    if n < 1000:
        head, rest = divmod(n, 100)
        s = digits[head] + '百'
        if rest == 0:
            return s
        if rest < 10:
            return s + '零' + digits[rest]
        return s + int2cn(rest)
    head, rest = divmod(n, 1000)
    s = digits[head] + '千'
    if rest == 0:
        return s
    if rest < 100:
        return s + '零' + int2cn(rest)
    return s + int2cn(rest)


def survey(text):
    """实算三数：^## 行数、编号节数、最大编号（中文与整数）。"""
    heads = re.findall(r'^## (.+)$', text, re.M)
    numbered = []
    for h in heads:
        m = re.match(r'^([零一二三四五六七八九十百千]+)、', h)
        if m:
            numbered.append((m.group(1), cn2int(m.group(1))))
    max_cn, max_n = max(numbered, key=lambda x: x[1])
    return len(heads), len(numbered), max_cn, max_n


def main():
    text = io.open(P, encoding='utf-8').read()
    lines, sections, max_cn, max_n = survey(text)

    new_section = sys.argv[1] if len(sys.argv) > 1 else None
    new_title = sys.argv[2] if len(sys.argv) > 2 else ''

    # 三数一律按**现文件实算**；新节必须已经追加进正文（先落节、后跑本脚本），
    # 本脚本只负责把实算值写回头部并登记「已落」清单，不自行增删正文节。
    if new_section:
        want = cn2int(new_section)
        if want != max_n:
            raise SystemExit('新节号「%s」＝%d 与文件最大编号「%s」＝%d 不符'
                             '（先追加节正文再跑本脚本；新节号应为文件当前最大编号）'
                             % (new_section, want, max_cn, max_n))
        max_cn, max_n = new_section, want

    m = re.search(r'本文件共(\s*)(\d+)(\s*)节（可复测三数：`grep -c "\^## " CHANGELOG\.md` = (\d+) 行 / 编号节 (\d+) 节 / 最大编号「([^」]+)」', text)
    assert m, '未匹配到「记录进度」行'
    text = (text[:m.start()]
            + '本文件共%d 节（可复测三数：`grep -c "^## " CHANGELOG.md` = %d 行 / 编号节 %d 节 / 最大编号「%s」'
              % (lines, lines, sections, max_cn)
            + text[m.end():])

    if new_section:
        # 插在「八十八」补录条之前（该条是历史补录，永不改写），退路是清单结尾
        anchor = '；「八十八」＝'
        if text.count(anchor) != 1:
            anchor = '；最新一节见文末'
        assert text.count(anchor) == 1, '「已落」清单锚点不唯一或已变'
        entry = '；「%s」＝%s，已落）' % (new_section, new_title) if new_title else ''
        text = text.replace(anchor, entry + anchor)

    io.open(P, 'w', encoding='utf-8', newline='\n').write(text)
    print('三数 → 共 %d 节 / %d 行 / 编号节 %d 节 / 最大编号「%s」'
          % (lines, lines, sections, max_cn))
    if new_section:
        print('已登记「%s」' % new_section)


if __name__ == '__main__':
    main()
