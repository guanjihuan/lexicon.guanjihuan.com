# 感情色彩 · 语体色彩 判定口径（第七十轮）

本文件是这两维的**唯一判准**。子代理批量初判、属主终裁都以此为准。

## 一、适用范围

| 维度 | 标哪些词 | 不标哪些词 |
|---|---|---|
| 感情色彩 `sub` | 形容词（438）、名词（615）、动词（445） | 副词（362）、连词（85）、介词（64）——这三类不带评价义，标「未标注」 |
| 语体色彩 `reg` | 全库 2009 词 | 无（未标者一律「中性」） |

感情色彩四档取值（**勿改字面**，前���与数据里已有值一致）：

- `积极的` —— 褒义
- `消极的` —— 贬义
- `争议性的` —— 两极评价 / 带争议色彩 / 难以定论
- `中性的` —— 不带评价，或评价随语境漂移（默认值）

语体色彩三档取值：

- `书面语` —— 带书面语域印记：正式/文雅词、学术专用术语（术语也是语域印记）
- `口语` —— 带口语色彩
- `中性` —— 通用，无明显语域印记（默认值）

## 二、感情色彩判准

### 1. 看什么

看该词在**学术语域下的常用义**是否**稳定携带**褒义或贬义评价。

### 2. 四档怎么分

- **积极的**：词义本身就含褒义评价。
  例：`innovative` `beneficial` `enhance` `benefit` `rigorous` `advantageous` `merit`
- **消极的**：词义本身就含贬义评价。
  例：`harmful` `obstacle` `constraint` `hinder` `impede` `deficiency` `shortcoming`
- **争议性的**：评价两极、或学界/语境本身有争议、或词义自带"难定论"色彩。
  例：`controversial` `ambiguous` `equivocal` `dilemma` `trade-off` `paradox` `counterintuitive`
- **中性的**：不带评价，或评价随语境漂移。**这是正当结论，不是"没判"**。

### 3. 硬规则

1. **常用义优先**：按学术写作里的高频义判，不按边缘义项。
   例：`dramatic` 在学术里多指"显著的/急剧的"（可判中性或消极），不按"戏剧化的"判。
2. **不按搭配判**：只有当词本身（不论宾语）在该语域下默认带评价时才标。
   例：`risk` 学术写作里默认是风险来源 → 可标消极；但 `risk assessment` 整套流程是中性的。
3. **强度不改变档位**：轻微贬义（`negligible` `lengthy` `chronic` `marginal`）仍属消极；
   只有"无评价"才归中性。宁严勿宽，但不得把弱贬义误判成中性。
4. **中性 ≠ 未标**：形容词/名词/动词一律有值（未显式判定的取默认「中性的」）；
   只有副词/连词/介词是「未标注」。
5. **不得为凑数标**：把 1498 词里绝大多数判成中性是**预期结果**，不是失败。
6. **形容词当前标签不神圣**：本库旧标签（源站给的）对过半数形容词偏宽松，
   须独立重判。特别是下列旧「积极的」词要重新审：
   `important` `essential` `novel` `systematic` `comprehensive` `appropriate` `correct`
   `effective` `efficient` `exact` `accurate` `safe` `stable` `rigorous` `conclusive`
   `decisive` `novel` `productive` `profound`
   —— 判「中性」还是「积极」要给理由。

### 4. 三类典型错判

- **把"程度强"当"褒贬"**：`significant` `substantial` `considerable` `dramatic` = 程度副词式用法，不带评价 → 中性。
- **把"有用"当"褒"**：`effective` `efficient` `functional` —— 学术语境里是功能性描述，中性为佳。
- **把"难"当"贬"**：`difficult` `challenging` `daunting` —— 有阻力义即消极；但 `challenging` 单独用也常是褒义（"challenging topic"）→ 判争议性或中性并说明。

### 5. 输出格式

严格 JSON 数组，每项：

```json
{"word": "innovative", "sub": "积极的", "reason": "词义本身含创新褒义评价"}
```

`reason` 一句话，必须落到**该词的义项**上，不得写"属于积极类"这类空话。

## 三、语体色彩判准（第二稿：四档）

四档为 **学术术语 / 书面语 / 口语 / 中性**，每词只归一档。
归属优先级：学术术语 > 书面语 > 口语 > 中性。这里的「中性」表示
**没有需要特别提示的语域印记**，不是「不学术」。

### 1. 学术术语

指称某一学科或专业领域的**具体方法、技术、测量对象、数据结构、
报告规范或学科概念**。例如：`covariate`、`endogeneity`、
`heteroskedasticity`、`ethnography`、`placebo`、`meta-analysis`。

边界必须同时看两条：

1. 本库所列义项确实承载专门概念，不能只凭词形「看起来像术语」；
2. 不是把普通英语词在学术语境里的常规用法换一个学科名称就当术语。

因此，`methodology` `analysis` `approach` `framework` `principle`
`study` `paper` `practice` `input` `task` 都是**通用学术词**，归中性；
`ratio` `factor` `measure` `outcome` `variable` 也不能仅因统计学里有
专门用法就标成术语。反过来，`covariate` `imputation` `endogeneity`
`preregistration` 的专门义就是词条的主要学习内容，应标「学术术语」。

对兼类词（如 `empirical`、`clinical`、`categorical`），若拿不准，
遵循**宁漏勿滥**：标签只给能明确说明学科与专门概念的词。
本库现有口径中，`empirical` `experimental` `observational` `categorical`
都只是普通研究描述词，统一归中性；不能一个按研究设计术语、另一个按普通词。

### 2. 书面语

带正式、文雅或公文语域印记的词与固定用语，包括：

- 正式连接与篇章标记：`moreover` `furthermore` `nevertheless`
  `whereas` `accordingly` `thereby` `notwithstanding`；
- 正式固定用语：`in the event that` `by virtue of` `with reference to`
  `in lieu of` `prior to`；
- 正式/文雅词：`hitherto` `aforementioned` `elucidate` `commensurate`
  `stipulate` `utilize`。

判据不是「学术写作里能出现」，而是它相对于普通替代表达有更明显的
正式语域印记。`however` 等高频连接词可因书面篇章功能标书面语，
但不得据此把所有连接词都标成书面语。

### 3. 口语

带口头、随意或会话话语标记色彩的表达，如 `well`（引出话题）、
`anyway`、`by the way`、`on that note`、`tricky`。
本库是学术词表，这一档天然很小，**宁缺毋滥**。

不得仅凭「日常也使用」判口语：`fashion` 在本库对应
`in a similar fashion`，不是口语；`scope` 在本库只有「范围」等普通义，
也不是口语。`anyhow` 与 `anyway` 都常作会话中的转换/收束标记，
不应把 `anyhow` 错标为「书面语」。

### 4. 复核要求

- 逐词对照本库释义，不凭词形或词源联想；
- 改档时必须同步更新该档的裁定理由；
- 四个集合互斥，未标词统一回落「中性」；
- 反向检查中性词中的正式连接词和术语，也正向清理少数派里的普通词。
