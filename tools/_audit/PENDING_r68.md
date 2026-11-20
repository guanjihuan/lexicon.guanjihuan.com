# 第六十八轮·全库语义校对台账（8 切片 + 机械扫描 + 属主复核）

状态：全部条目已落笔修正并过回归（2026-11-19）。

## 来源与口径

- **语义审读**：8 切片代理（每片约 250 词，覆盖全库 2009 词 × 3 例句 + 释义 + 词性 + 感情色彩），
  切片 8 代理未产出，由属主自审补齐（245 词逐条读完）。代理只报不改，**每条由属主回源码核实后才落笔**。
- **机械扫描**（先行）：英式拼写穷举（对照表逐条 + 词边界守卫）、数字/否定/括号/标点/键集一致性、
  词形↔例句命中、zh 残留拉丁字母、词性↔释义括注一致性、核心层台账↔词表↔curation 段三方对账。
- **口径约束**：全库统一**美式**拼写；全库数字体例为确数转阿拉伯、「百分之X」→「X%」；
  释义分隔符「；」分不同义项、「，」分同义说法；`senses` 每个数组元素＝一个义项；
  增补词释义真源＝`tools/_gen_additions.py` T 表，原词释义真源＝`data/curation.json` fix 段；
  例句真源＝`data/examples_parts/part_*.json`（产物由 `merge_examples.py` 重烘）。

## 落笔范围

- **英式拼写归一 35 处**（20 个 part 源文件，README「全库统一美式拼写」硬口径）：
  labour→labor ×4、enrolment→enrollment ×5、catalogue→catalog ×3、favours/favoured→favors/favored ×3、
  emphasises/emphasised→emphasizes/emphasized ×2、anonymised→anonymized ×2、
  organised→organized、organisational→organizational、industrialised→industrialized、
  harmonisation→harmonization、reorganising→reorganizing、standardised→standardized、
  finalising→finalizing、judgement→judgment、licences→licenses、artefact→artifact、
  harbour→harbor、programmes→programs；
  体例归一 towards→toward ×3（余 23 处本已作 toward）、cancelled→canceled（美式）。
  写法：文本级替换，**不重新序列化 JSON**——各 part 文件缩进风格不一（紧凑单行 / indent=1），
  `json.dump` 重写会把整文件重排、产生几百行噪声 diff。
  计数口径：代理切片发现（`findings_slice1..7.json`，共 61 条）**按拼写词形归类**后
  汇总为此处的 35 处，不按词条名逐词列出——故切片里 25 条英式拼写发现（slice6/7）
  的词名（entirely、hierarchy、motivation 等）不在本节出现，但都在上述词形清单内。
  回源核实：现行 `data/examples.json` 中上述 21 组英式拼写**零残留**。
- **中文译文硬伤 21 处**：
  segment 管道→数据流程、select 结果→页面、publish 一家期刊→一种期刊、infinitely 解析→分析、
  reliably 通常→稳定地、uniformly 普遍→一致地、approximately 学生人口→全体学生、
  rigid 僵硬→僵化固执、illuminating 发人深省→极具启发性、intermediate 中级小组→中等水平的小组、
  unveil 一所中心→一座中心（+举行揭幕仪式）、parenthesis 一段括注→一处括注、
  recommendation 推荐…的建议→关于…的建议、exclusion 施予排除标准→设定排除标准、
  inferential 从原始数据之外→超出原始数据本身、verification 文献核查→文件核查、
  assertion（assertion of the research question → of its central claim，连带 zh）、
  insofar as 语义不成立的整句重写、ratio 师生比方向反（high → low student-to-teacher）、
  reputation 冠词缺失（with damaged reputation → with a damaged reputation）、
  for the most part 大体上（第八轮台账声称已落、实则未落的修订）。
- **切片 8 补审 3 处**：
  in the long run 例 2 前瞻框与过去式自相矛盾（improved → improves，连带 zh）；
  by all means 例 0/2 把「务必；尽可以」误译成「尽管」（那是 although 的义）。
- **释义修订 4 词**：
  when 删「然而」（那是 whereas/while 的义项，串义）——T 表；
  uncertainty「变数（数学义）」→「不确定度，不确定量（数学义）」（变数是 variable 的译法，
  库里 variable 译「变量」，此处串义）——T 表；
  point 补「道理，益处」义项（例句 2 用的是该义）——T 表；
  merit 补「优异；优良」义项（例句 1 的 merit award 用的是该义）——fix 段。
- 产物重烘：words.json / cats.json / examples.json / js/data.js / js/examples.js / core_proposals.json。
- 回归：content_test 29 项、content_mutation 29 项、pos_consistency_audit A/B/C′/D 四段、
  pipeline_test 69 项、dom_smoke_test 439 项，全绿；七步链幂等零漂移。

## 驳回的代理建议（与本库既定口径冲突，非缺陷）

- **词性类**：
  `due to` / `owing to` / `onto` / `aside from` / `in place of` / `rather than` 建议标「介词」——
  本库 null 族只收**纯介词性固定语块**、不入词性索引（README 已定），这批词的 null 正是现行口径。
  `so` / `therefore` / `hence` 建议改连词——本库因果副词一贯标副词（连词口径是 but/although/while 一类）。
  `not to mention` 建议改连词——与 r67 新增的 `let alone` 同族同判副词，库内已自洽。
  `irrespective` 建议改介词——r66 刚裁定为形容词（irrespective of 正式高频），台账已记明。
- **释义类**：`merit` 建议补义项——已按原词表词形走 fix 段落盘（见上）。

## 遗留（未改，供后续轮次判断）

- `to be sure` / `in sum` / `that being so` 的 zh 与第八轮台账建议措辞不完全一致，但语义正确，未改。
- `by all means` 例 1「请务必致函登记办公室」句尾用法略口语，en 亦同；属风格，未改。
- `in no way` 例 0「In no way is there evidence that…」为倒装正式句式，合学术英语，非缺陷。
- `aside from` 例 2 的辖域（撇开 / 除…外还）英文本身有歧义，zh 取其一；未改（改则须重写整句）。
- 84 词例句挖空回退清单见 `cloze_ineligible_84.json`（例句全为屈折形，出题自动回退，属设计内）。
