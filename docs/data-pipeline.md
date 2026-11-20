# 数据与生成流水线

本文是词条、例句、核心层和分类维护的现行规则。历史决策过程见 [CHANGELOG](../CHANGELOG.md)，文件职责总表见[项目结构](project-structure.md)。

## 数据流向

```text
原始抽取数据 ─┐
人工整理七段 ─┼─> curate.py ─> words.json + cats.json ─> make_data.py ─> js/data.js
逐词裁定台账 ─┘

examples_parts/ ─> merge_examples.py ─> examples.json ─> make_examples.py ─> js/examples.js
```

| 环节 | 文件与说明 |
|---|---|
| 原始抽取 | `data/words800.json`：源站编号 1–800，缺第 736 号，共 799 条；`data/categorized.json`：344 条。原始结果保持不变 |
| 人工整理 | `data/curation.json` 七段：`remove` / `fix` / `recat` / `add` / `core` / `noncore` / `sentiment` |
| 核心层真源 | `data/core_decisions.json`，逐词 verdict 与理由；`_gen_core.py` 负责落到 `core` / `noncore` 段 |
| 色彩真源 | `data/sentiment_decisions.json`，逐词感情色彩与语体色彩；`_gen_sentiment.py` 负责落段 |
| 整理结果 | `data/words.json`、`data/cats.json`，均为生成物 |
| 前端词表 | `js/data.js`：`window.WL_WORDS` / `window.WL_CATS`，生成物 |
| 例句来源 | `data/examples_parts/part_*.json` 分批手写文件 |
| 例句结果 | `data/examples.json`：按词形索引，每词 3 条 `{en, zh}`，生成物 |
| 前端例句 | `js/examples.js`：`window.WL_EXAMPLES`，生成物 |
| 分层提案 | `data/core_proposals.json`：`core_audit.py` 的生成物，仅供复核，不等于定稿 |
| 提案信号 | `data/freq_refs.json`：AWL 词族、学术骨架、连接语块和通用高频参考 |

**只改真源，不手改生成物。** 对生成物直接修补会在下次流水线运行时被覆盖，也会造成不同产物之间互相矛盾。

## 七段完整性与严格读取

`tools/_strict_json.py` 的 `require_curation_segments` 在写盘前检查：

- 七段必须全部存在；
- 段类型和段内元素类型必须正确；
- JSON 重复键、段名疑似拼错等问题必须明确报告。

“段为空”表示本轮确实没有覆盖；“段不存在”表示口径不明，二者不能混用。缺段不能由 `.get(段, 默认值)` 静默兜底，否则可能生成一份结构合法、内容却错误的词表。

失败运行应在写盘前退出，产物保持不动。写盘采用临时文件加原子替换，避免半截 JSON 覆盖可用产物。

## 各段的编辑入口

| 目标 | 应改位置 | 不应直接改 |
|---|---|---|
| 增补词 | `tools/_gen_additions.py` 的 T 表 | `curation.json` 的 `add` 段、下游 `words.json` |
| 词性修正 | `tools/_gen_recat.py` 的源表 | `curation.json` 的 `recat` 段 |
| 核心层 | `data/core_decisions.json` | `core` / `noncore` 段 |
| 感情 / 语体色彩 | `data/sentiment_decisions.json` | `sentiment` 段 |
| 源词释义修正 | `curation.json` 的 `fix` 段 | 下游生成物 |
| 例句 | `data/examples_parts/part_*.json` 对应分批文件 | `examples.json`、`js/examples.js` |

`_gen_additions.py`、`_gen_recat.py`、`_gen_core.py` 和 `_gen_sentiment.py` 会整体重写各自负责的段落。

> **一次性脚本不是维护入口**：`tools/_gen_ledger*.py`、`tools/_ledger_r66.py` 等只用于特定轮次建账。不要重跑它们来“刷新”现行台账；调整核心层裁定时直接编辑 `data/core_decisions.json`，再跑 `_gen_core.py`。

## 完整生成顺序

修改词表后的九步链如下（`curate.py` 有意执行两次，让色彩生成器先校验现行词形，再把色彩落回最终产物）：

```bash
python3 tools/_gen_additions.py
python3 tools/_gen_recat.py
python3 tools/_gen_core.py
python3 tools/curate.py
python3 tools/_gen_sentiment.py
python3 tools/curate.py
python3 tools/make_data.py
python3 tools/merge_examples.py
python3 tools/make_examples.py
```

按实际改动运行对应生成器即可，但涉及多段时必须保持依赖顺序。不要为例行内容修改运行 `extract.py`；原始抽取器是上游重建工具，不是每次生成链的一部分。

### 核心层提案需要额外重烘焙

`data/core_proposals.json` **不在九步链内**。词表、释义或词性变化后补跑：

```bash
python3 tools/core_audit.py
```

并把生成物与对应真源一起提交。`pipeline_test.py` 会检查不同 `PYTHONHASHSEED` 下产物逐字节一致，并与已提交文件零漂移。

### T 表顺序会决定编号

`_gen_additions.py` 中 T 表条目的顺序决定新增词编号。`curate.py` 按 `add` 段顺序接续分配 `num`，因此：

- 修改词条内容时保持原有行位置；
- 新词追加到表尾，不为“排序好看”移动旧行；
- 不对最终词表重新编号。

## 关键内容与分类口径

### 增补与分类覆盖

当前词库由原始词取舍与后续学术写作高频词增补共同组成。增补词同样逐词审核词性、核心层和色彩，不采用“增补即入核”的自动规则。

当前分类口径：

- 形容词、动词、名词、副词、连词进入词性索引；
- 形容词、名词、动词另标感情色彩：积极 / 消极 / 争议性 / 中性；
- 全库每词都有语体色彩：学术术语 / 书面语 / 口语 / 中性；
- 余下单词介词与介词性固定短语在前端展示为“介词”，内部 `pos=null`，不进入五类实词索引。

具体规模以 [README 当前概览](../README.md) 与 [CHANGELOG 当前状态](../CHANGELOG.md#当前状态（速览）) 为准；修改词表后必须实跑统计，不能从旧词数推导。

### “介词”与 `pos=null`

“`pos=null`”不表示这些词在语言上没有词性，而是本库不为它们设置五类实义词性标签。该族已收窄为**纯介词性**：篇章副词与从属连词各有实义词性，应进入词性索引。

单词介词包括：`via`、`onto`、`despite`、`regarding`、`versus`、`given`、`barring`、`during`、`following`、`like`、`considering`。后六者的归类依据本库例句中的介词性主用法与逐轮裁定。

末词为介词的支配性介词短语包括：

```text
due to, owing to, prior to, subject to, according to, thanks to,
because of, as a result of, apart from, relative to, in lieu of,
in terms of, with respect to, compared with, in light of,
on the basis of, by means of, with regard to, in addition to,
instead of, rather than, other than, in contrast to, in spite of,
on behalf of, for the sake of, at the expense of, by virtue of,
by reference to, with reference to, in the wake of, on account of,
by reason of, in favor of, with the exception of, with a view to,
with the aim of, in order to, so as to, in accordance with,
in conjunction with, in the context of, in relation to,
in connection with, aside from, in place of, for the purpose of,
for the purposes of, in pursuit of, in the absence of,
as for, as to, as opposed to
```

`on the one hand` 是副词，`such as`、`for fear that`、`to the end that`、`not only` 等按现行裁定进入连词索引，不进入 null 族。

`tools/pos_consistency_audit.py` 的 A 段机械检查 null 族，E 段反查“词典上是单词介词、本库却标实义词性”的漂移。`besides`、`notwithstanding` 等兼类词按本库主用法和释义交代判断，不做简单词典标签替换。

### 语体色彩

- **学术术语**：某学科或专业领域的专门技术词，如 `covariate`、`endogeneity`、`ethnography`；
- **书面语**：正式文体标志，如 `moreover`、`in the event that`、`thereby`；
- **中性**：通用学术词与无特殊语体标志的词，如 `study`、`practice`、`framework`、`methodology`；
- **口语**：明确具有口语色彩的少数词。

“学术上常用”不等于“学术术语”，“适合论文”也不等于“书面语”。两类已经拆开，不再混装。

### 核心层

核心层采用“仅硬证据入核”，目标约为全库的 45–50%。证据包括：

- 机械 strict 命中；
- 学术论证 / 篇章核心连接词的显式闭集；
- 报告动词组；
- 可报出词头族名的 AWL 词族成立成员；
- 高置信论证功能词（H 档）。

通用高频但不承载论证功能、证据偏软的 M 档词不因“看起来常用”入核。`but`、`because`、`so`、`since`、`and`、`also` 等口语基础连接词有显式排除规则。

每词的最终结论和理由以 `data/core_decisions.json` 为准。机械提案只是复核输入，不得绕过台账直接改写核心层。

### 拼写、义项与格式

- 全库统一美式拼写，如 `catalog`、`favor`、`fulfill`、`skepticism`、`analog`；Longman 与 Cambridge 外链可按需要映射到英式 headword。
- `senses` 的**每个数组元素对应一个义项**，词条详情按 1 / 2 / 3 分行编号。
- 元素内的“；”和“，”用于并列同义说法，或短语内的成分与限定；不要把同一义项机械拆成多个数组元素。
- 打印清单与导出时，多个义项再以“；”相接。
- `sth` / `sb` 使用规范写法。

### 词条编号：不得重排

原有词条沿用源站编号，新词接续删除后的最大源站编号，从 800 起分配。源站 800 号 `amplitude` 已删除，其编号由首个增补词 `analyze` 补位。

编号**不连续是正常结果**：删词留号，源站自身也缺 #736。词库页因此显示“原号”，不写“序号”。后续新增词继续接续当前最大编号，不能填补旧洞或按字母重排。

学习进度按 `num` 存在 `localStorage`，核心层台账和部分修正也以编号对位。重排编号会使用户进度集体错位，且难以恢复。

### 例句

- 每词 3 条 `{en, zh}`，英文原句配中文对照；
- 语域取学术 / 中性英文，多义词尽量覆盖不同义项；
- `examples.json` 按**词形字符串**索引，与词条编号解耦；
- 修改分批来源后必须重新合并、校验并生成 `js/examples.js`；
- 自动测试全绿后仍需人工审读中文残留英文、目标词使用和中文硬伤，详见[测试与巡检](testing.md#自动检查的盲区与人工审读)。

### 词典外链

每词保留 Longman、Merriam-Webster、Cambridge 三个词典外链。修改链接生成规则时同时回归多词短语、美式 / 英式拼写与特殊字符。

## 修改后的检查与文档同步

1. 运行真源对应的生成链，确认没有只落一半产物。
2. 运行 `pipeline_test.py`、`content_test.py`、相关专项测试和 `dom_smoke_test.js`；测试职责见[测试与巡检](testing.md)。
3. 对生成物做零漂移检查，不能用“重新生成后看起来差不多”代替。
4. 词数、核心数、分类数、例句数等从当前产物实测，不在文档里心算派生。
5. 同步 README 当前概览、CHANGELOG 当前状态与页面静态文案；逐轮过程只追加到 CHANGELOG。
6. 暂存前检查工作区，避免把其他窗口的生成物或在途内容一起卷入，详见[协作与文档维护](contributing.md)。

内容与词典链接版权归原作者 Ji-Huan Guan（CC BY）。
