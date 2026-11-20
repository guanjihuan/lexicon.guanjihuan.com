# 全库审读台账（8 切片全部完成·已核实·已落笔）

状态：全部条目已落笔修正并过回归（2026-11-18）。本文件为审读留痕与移交说明。

来源：语义审读代理 8 切片（每片约 240 词，覆盖全库 1938 词 × 3 例句）+ 人工核实（对回 words.json/examples.json）。
findings_0/1/2/3/5/6.json 曾落盘后被并发窗清理，本台账为合并终版；findings_4/7.json 保留在目录。

落笔范围（数据域·全库校对轮）：
- `tools/_gen_additions.py` T 表行内改 15 词：direction/range/post hoc/critique/export/assuming/
  finite/hypothesize/abstraction/key/surely/introduction/observational/in all/that being so/precursor/episodic
- `data/curation.json` fix 段 7 词：insofar as/prove/harbor/respect/stringent/regime/accordingly
- 例句源 `data/examples_parts/part_*.json`：en/zh 修正 44 处 + 美式拼写归一 36 处
- 产物重烘：words.json / cats.json / js/data.js / examples.json / js/examples.js / core_proposals.json
- 七步链重跑幂等零漂移；content_test 25 项、pos_audit、dom_smoke 数据域断言全绿

## 切片 0
1. accordingly senses 缺「因此」连接义 → fix 段补第二义项
2. extraordinary zh「发现了非凡的成果」→「作出了一个非凡的发现」
3. illuminating zh「发人深省而又极详尽」→「以极富启发性的细节」
4. extraneous zh「与早期草稿无关的引述」→「提及早期草稿的多余引述」
5. instructive zh「战役」→「活动」（学术语境 campaign 非军事）
6. vital zh「种群」→「全体居民」（无生物学语境）
7. witness zh「出庭作证」→「到场作证」（委员会语境非法庭）

## 切片 1
8. spark zh「导火线」（积极语境不当）→「契机」
9. insofar as senses「据…所知」非其义项 → fix 段改「就…而言；在…的范围内；到…的程度」
10. conservation zh「能量守恒」→「节约能源」（energy conservation 法律语境）
11. prove senses 缺及物「证明」义 → fix 段补「证明，证实（prove that…）」
12. harbor senses 缺「心怀（怨恨等）」义 → fix 段补第三义项
13. exaggeration zh「毫无」→「几乎没有」（little 程度）
14. characterize en 一般现在时 + over the past two decades → 现在完成时

## 切片 2
15. respect senses[1]「涉及；关于」非动词义 → fix 段改「（名词）方面（in this respect 在这方面）」
16. stringent senses「严重的」非其义项 → fix 段改「严格的；严厉的；苛刻的」
17. direction senses「部门」非其义项 → T 表改「方向；指导；管理；趋势」
18. range senses 缺「山脉」义 → T 表补「山脉（mountain range）」
19. regime senses 括注「regime shift 制度转变」误导 → fix 段拆义项改「（气候/生态）状态转变」

## 切片 3
20. value en「give intrinsic value to」搭配矛盾 → treats…as having intrinsic value + zh
21. key senses「键盘的」错义 → T 表删（keyboard 才是键盘）
22. significant zh「研究报道」→「该研究报告称」
23. typical en typical×2 循环 → advanced mathematical problems + zh
24. surely senses「稳妥地」非独立义项 → T 表改「想必」
25. although zh 让步方向反 →「不过测量结果非常精确」
26. hypothesize senses「（名词用法）」错标 → T 表改纯动词释义
27. comprehend zh「统计算法」→「统计方法」
28. abstraction senses「提炼（动词用法）」标注欠准 → T 表改「提炼、抽取（动作义）」
（apparently「据说」保留：转述义在 senses 内；so/yet pos 双标词受单值口径限制，不改）

## 切片 4
29. introduction senses 缺「引进，采用」义 → T 表补
30. discourse zh 漏译 in（AI in education）→「教育领域人工智能」
31. spectrum zh 结构混乱 →「由各种可能解释构成的连续体中的一端」
32. specificity zh「是否同样适用」→「是否具有特异性」
33. observational senses 缺「观察的，观察力的」义 → T 表补
34. versus en 插 only 破坏平行 →「covers repairs versus replacement of defective parts」
35. point en「point in his criticism」→「point to」
36. inclusion zh grant panels 漏译 →「科研资助评审小组」
37. response zh「预测答对」生硬 →「能否预测作答是否正确」
38. respondent zh「令人改观」生硬 →「带来了深刻转变」
39. disproportionate zh「失衡待遇」→「不成比例的差别对待」
（dataset en[2] Training models require——复数主语解读自然，不改）

## 切片 5
40. control en 例句用名词（对照组）与 pos=动词 不符 → 换动词用例 controls for confounders + zh
41. critique senses 括注动词式 → T 表改「a critique of a theory」
42. effect size en more important 缺比较对象 → 补 than they are
43. post hoc 3 例全定语与 pos=副词 → senses 行内注「作状语；亦可作定语」
44. pooled en in each site → at each site
45. ethics en require that + can → be allowed to
46. conference zh「赢得了…批评」→「获得了」
47. inter alia zh 夹注生硬 →「除其他事项外，还包括…」
48. in that zh「更为优越，在于它…」欧化 →「因为它区分了」

## 切片 6
49. export senses 缺「导出」义 → T 表补
50. completely en weakened → undermined
51. totally/affiliate en long term → long-term
52. rigorously zh 漏译「严格」→ 补
53. altogether zh「总的来说」→「总共」
54. as well as en narrow 与 zh「扎实」矛盾 → deep
55. classify en high income → high-income
56. concur zh 漏译「一致」→ 补
57. incur zh「在截止期前撤回」译反 →「逾期撤回」
58. stipulate zh「法定期限」增译 →「最短通知期的规定」
59. depth zh「信度」→「效度」（validity 术语）
60. momentum en Conservation of momentum 术语误用 → Maintaining momentum

## 切片 7
61. to be sure zh 三句「确切地说」→「诚然」（让步话语标记，非 to be precise）
62. in sum zh「评审核」错词 →「该综述」
63. in all senses「总的来说」非其义项（属 all in all）→ T 表改「总共；合计」
64. sooner or later en 过去时 gave up 与将来推断矛盾 →「will sooner or later fail」
65. by all means en[1] 句尾「务必」不自然 → 句首条件式 + zh
66. that being so senses「话虽如此」错义 → T 表改「既然如此；有鉴于此」
67. that being so zh[0] 让步译反 →「正因如此」
68. in no way en[0]「There is in no way evidence」不成句 → 倒装「In no way is there evidence」
69. in place of en[0] substitute A in place of B 冗余 → used
70. prolong en prolonged the start 搭配不当 →「prolonged the preparation period」+ zh
71. precursor senses 缺「（化学）前体」→ T 表补
72. episodic senses 缺「（记忆）情景的」→ T 表补
（in that case en[0] 已然事实后接 in that case——「在那种情况下」解读可通，不改；
 aside from en[2] 后置辖域歧义——zh 与 senses 一致，可解析，不改）

**后续轮次补落（本台账未记，已由后轮修妥）**：`findings_4/7.json` 留档里两条
本台账未列的发现——`verification` zh[2]「文献核查」→「文件核查」（document 误译）、
`for the most part` zh[2]「多数情况下」→「大体上」——均已在**第六十八轮**
落笔（见 `PENDING_r68.md`「中文译文硬伤 21 处」及其「for the most part … 第八轮
台账声称已落、实则未落的修订」条）。回源核实：现行 `data/examples.json` 两处
译文均已改妥。

## 机械扫描锁定
73. finite senses「有限的量」名词式尾巴 → T 表改
74. 全库英式拼写归一 36 处（programme/analyse/centre/recognised/behaviour/organisations/favour 系）
75. long term / high income 缺连字符 4 处 → 补

## 全局扫描（复核后不改动）
- 外链英式 slug = BRITISH_ALIAS 有意映射，非缺陷
- so/yet 双词性、apparently 转述义、zh 专名（DNA/PRISMA）、a dozen 意译——保留
- r66 批 121 词机械卫生全查零发现；词形相近 5 对均正当派生/异义

## 环境事件（移交说明）
- 并发窗（内容窗）第六十六轮 121 词曾 stash 后 pop 恢复；其 pop 曾短暂覆盖我的 parts 修正，
  复核确认现全部健在。
- 并发窗（词性校勘窗）已提交 421117f（irrespective/not only/given/barring 四词改判，null 55→57）。
- **HEAD 真回归（移交）**：e1499fd（词性校勘收尾）把 js/app.js 带入含 2 处 `quizNotice ?` 渲染的版本
  （e1499fd^ 是 1 处），dom_smoke 源码级断言「the range notice is rendered in one place only」红。
  位置：js/app.js:1657 与 js/app.js:2116。属界面/校勘窗域，本窗未代改。
- README/CHANGELOG 的 1938/899/5814 口径行待内容窗随提交落笔。
- 上一提交轮（09ec63d）漏重烘焙 core_proposals.json，本轮已对齐。
