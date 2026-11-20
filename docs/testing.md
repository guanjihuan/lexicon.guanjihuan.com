# 测试与巡检

测试按“零依赖 DOM、浏览器端到端、视觉与无障碍、数据与流水线、变异验证”分层。不要为了凑一个固定的“套件总数”而重复运行职责相同的脚本。

## 准备环境

所有命令均从仓库根目录执行。

- DOM 冒烟只需要 Node.js；
- Python 测试需要 Python 3；
- 浏览器测试需要 Playwright 与可用的 Chromium / Chrome；

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

Windows 环境可将命令中的 `python3` 换成本机可用的 `py` 或 `python`，以实际安装为准。

## 快速回归

文档改动通常只需检查链接和 diff；运行逻辑改动至少执行零依赖 DOM 冒烟：

```bash
node tools/dom_smoke_test.js
```

无需为了文档改动虚报浏览器测试已运行。测试报告应写明实际运行了哪些命令。

## 测试矩阵

| 文件 | 职责 |
|---|---|
| `tools/dom_smoke_test.js` | 零依赖 DOM 与状态机回归，无浏览器也可运行 |
| `tools/smoke_test.py` | 主要端到端动线 |
| `tools/smoke_test_extra.py` | 快捷键、收藏、测验、打印等扩展动线 |
| `tools/smoke_test_roundtrip.py` | 导出 → 导入往返、损坏状态净化与学习数据保全 |
| `tools/tts_policy_test.py` | 发音口径：无英语音色不乱读、听力题作答后不自动读 |
| `tools/a11y_test.py` | 标题、live 区、可访问名、ARIA 引用、键盘焦点、触控与减少动态效果等 |
| `tools/contrast_test.py` | 手挑代表目标，在明暗主题、悬停、窄屏与打印态量测对比度 |
| `tools/contrast_sweep.py` | 真实应用全量文字与控件对比度，覆盖视图、浮层和交互态 |
| `tools/layout_test.py` | 版面几何、空态、静默截断、关键内容可见性与窄屏长单词整词一行 |
| `tools/focus_test.py` | 测验与翻卡重渲染后的焦点落点 |
| `tools/responsive_audit.py` | 多视口横向溢出、元素越界与触控目标巡检 |
| `tools/pipeline_test.py` | 写盘前闸门、原子写、九步链幂等、生成物零漂移；在临时副本运行 |
| `tools/content_test.py` | 释义、例句体例与挖空回退清单 |
| `tools/content_mutation.py` | 验证内容判据“改坏必红”且红在预期断言 |
| `tools/sentiment_test.py` | 感情 / 语体色彩覆盖、取值与台账落段闸门 |
| `tools/audit_all.py` | 跨文件一致性巡检：词集对齐、字段取值域、核心层台账与词表一致、词形大小写、zh 拉丁残留；发现问题非零退出 |
| `tools/mutation_test.py` | 跨套件变异与假绿扫描，先验 HEAD 基线再定向破坏 |

`tools/fixtures/contrast.html` 是对比度测试夹具，不是产品页面。

断言数与词数均以当前实跑输出为准，不在本文钉死总数。新增测试时更新职责表和对应命令，不沿用旧轮次数字。

## 浏览器端到端与界面巡检

```bash
python3 tools/smoke_test.py
python3 tools/smoke_test_extra.py
python3 tools/smoke_test_roundtrip.py
python3 tools/tts_policy_test.py
python3 tools/a11y_test.py
python3 tools/contrast_test.py
python3 tools/contrast_sweep.py
python3 tools/layout_test.py
python3 tools/focus_test.py
python3 tools/responsive_audit.py
```

根据改动面选择套件，不必把每次小编辑都包装成“全量回归”。修改全局状态、导航或事件委托时应扩大回归范围；修改对比度时同时考虑静态、悬停、窄屏、打印与相关交互态。

### 浏览器路径

Playwright 自带 Chromium 与本机环境不匹配时，可用 `WL_CHROMIUM` 指向真实存在的浏览器可执行文件。

Git Bash 示例：

```bash
WL_CHROMIUM=/path/to/your/chrome python3 tools/smoke_test.py
```

Windows PowerShell 示例：

```powershell
$env:WL_CHROMIUM = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
py tools/smoke_test.py
```

路径不存在时，脚本会忽略它并回退到 Playwright Chromium 或可用 channel。历史脚本中的 Linux 固定路径不应被当成 Windows 基线失败的依据；新套件应检查路径是否存在，并提供 channel 兜底。

Linux 上不要用 `/usr/bin/chromium-browser` 的 snap 版本跑点按类套件：它可能不触发 `requestAnimationFrame`，导致 Playwright 在“等待元素可见、启用且稳定”处持续等待。

### 控制台编码

仓库测试工装已在父子进程两侧固定 UTF-8。历史上 Windows GBK 解码造成的批量失败是假红，已修复；现在不要再用“Windows 基线本来就红”解释新的 `✗`，应按真实回归逐项定位。

## 数据、流水线与内容守卫

完整生成顺序见[数据与生成流水线](data-pipeline.md)。生成后按改动面运行：

```bash
python3 tools/pipeline_test.py
python3 tools/content_test.py
python3 tools/content_mutation.py
python3 tools/sentiment_test.py
python3 tools/pos_consistency_audit.py
python3 tools/audit_all.py
node tools/dom_smoke_test.js
```

- `pipeline_test.py` 在临时副本中验证写盘闸、原子替换、九步链幂等和生成物零漂移，不应改动工作树。
- `pos_consistency_audit.py` 是只读审计器，负责介词 null 族、对称构造、台账理由、形态和“单词介词却标实义词性”等检查。
- `audit_all.py` 是只读跨文件一致性巡检，发现问题**非零退出**（可接进常规回归）。它的判据**一律复用生产代码**：`reg` 取值域取自 `_gen_sentiment.py` 的 `REG_VALS`，“例句是否用了目标词”取自 `merge_examples.py` 的 `contains_word()`——不得在巡检脚本里另写一套简化判据（此前即因此产生 270 条假阳性）。
- 修改核心层参考或词表后，还应确认 `data/core_proposals.json` 已重烘焙且零漂移。

## 变异测试与基线纪律

```bash
# 默认变异表
python3 tools/mutation_test.py

# 连慢套件 smoke_test_extra 一起跑（约十分钟，以本机实测为准）
python3 tools/mutation_test.py --slow

# 仅在确认“守卫尚未落库”属于过渡期时，放行未覆盖例
python3 tools/mutation_test.py --allow-uncovered
```

`--allow-uncovered` 不能把已经覆盖却变异后仍通过的假绿变成合法结果；默认流程仍应把未覆盖当作需要处理的信号。

变异测试使用 `git archive HEAD` 的干净副本：先证明未变异 HEAD 基线可用，再打入恰好命中一处的变异，最后检查测试是否变红且红在预期断言。工作区有他人未提交改动时，不要把工作区问题误判为 HEAD 基线问题，也不要通过还原他人文件来制造干净环境。

结果要区分：

- **基线失败**：先修基线或确认 HEAD 本身问题；
- **变异未命中**：锚点失效，不等于守卫有效；
- **未覆盖**：基线输出中没有目标断言，可能是守卫尚未落库；
- **假绿**：基线存在该断言，变异后仍然通过，属于真实测试缺口。

## 自动检查的盲区与人工审读

`content_test.py` 全绿不等于内容无需复核。机械规则可能漏过：

1. 中文释义或中文例句中残留不应出现的英文；
2. 例句没有真正使用目标词，或只命中了形态相似的字符串；
3. 中文存在漏译、串义、主客体错位、术语不一致或明显语病。

增补批次与大规模例句修改应补人工审读，并将发现的新类型固化为机械判据。自动守卫与人工审读是互补关系，不能相互替代。

## 结果记录

在提交信息或 CHANGELOG 中写明：实际命令、通过 / 失败、失败摘要、未运行项及原因。不要把“静态检查未发现明显问题”写成“测试全部通过”。
