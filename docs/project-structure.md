# 项目结构

项目是无构建步骤、无外部运行时依赖的静态网站。仓库同时保存内容真源、生成产物、维护脚本和历史审计材料；这些文件的修改规则并不相同。

## 顶层导航

```text
word-learning/
├── index.html             # 页面骨架与静态元信息
├── icon.jpg               # 站点图标
├── css/
│   └── style.css          # 设计系统、响应式布局、明暗主题与打印样式
├── js/
│   ├── app.js             # 应用逻辑（原生 JavaScript）
│   ├── data.js            # 生成的词表数据，勿手改
│   └── examples.js        # 生成的例句数据，勿手改
├── data/                  # 内容真源、裁定台账、参考数据与生成产物
├── tools/                 # 生成器、回归测试、审计器与历史留档脚本
├── docs/                  # 当前有效的专题文档
├── README.md              # 项目入口与概览
└── CHANGELOG.md           # 逐轮历史记录，追加式维护
```

浏览器直接打开 `index.html` 即可运行；`data/` 与 `tools/` 不是页面运行时的网络依赖。

## 数据文件：先辨认真源与生成物

| 路径 | 角色 | 修改方式 |
|---|---|---|
| `data/words800.json` | 原始抽取结果，799 条 | 原始资料，勿手改 |
| `data/categorized.json` | 原始分类精选，344 条 | 原始资料，勿手改 |
| `data/curation.json` | 人工整理清单的落盘形态 | 各段按生成源或手工规则维护，见下表 |
| `data/core_decisions.json` | 核心层逐词裁定台账 | 唯一事实源；调整裁定时直接按规则编辑台账 |
| `data/sentiment_decisions.json` | 感情色彩与语体色彩逐词台账 | 唯一事实源 |
| `data/freq_refs.json` | AWL、学术骨架等离线参考信号 | 仅供核心层提案，不直接等于裁定 |
| `data/examples_parts/` | 例句分批手写来源（`part_*.json`） | 修改对应分批文件后重新合并 |
| `data/examples.json` | 合并后的完整例句库 | 生成物，勿手改 |
| `data/words.json` | 整理后的全词表 | 生成物，勿手改 |
| `data/cats.json` | 整理后的词性索引 | 生成物，勿手改 |
| `data/core_proposals.json` | 核心层机械提案 | `core_audit.py` 的生成物，仅供复核 |

### `curation.json` 七段的归属

| 段 | 维护入口 |
|---|---|
| `remove` | 按内容裁定维护 |
| `fix` | 手工维护的源词释义修正 |
| `recat` | `tools/_gen_recat.py` 内的源表 |
| `add` | `tools/_gen_additions.py` 内的 T 表 |
| `core` / `noncore` | `data/core_decisions.json` → `tools/_gen_core.py` |
| `sentiment` | `data/sentiment_decisions.json` → `tools/_gen_sentiment.py` |

生成器会整体覆盖目标段。不要直接手改由生成器拥有的段落，更不要手改下游 JSON 或 `js/*.js` 生成物。完整执行顺序见[数据与生成流水线](data-pipeline.md)。

## 工具文件：按职责识别

### 日常维护入口

| 文件 | 用途 |
|---|---|
| `tools/extract.py` | 从抓取的 HTML 重建原始抽取数据；非常规日常步骤 |
| `tools/curate.py` | 应用七段清单，生成 `words.json` 与 `cats.json` |
| `tools/_strict_json.py` | 严格 JSON 读取、重复键检测与七段完整性闸 |
| `tools/_gen_additions.py` | 增补词 T 表与 `add` 段生成器 |
| `tools/_gen_recat.py` | 词性源表与 `recat` 段生成器 |
| `tools/_gen_core.py` | 从核心层台账生成 `core` / `noncore` 段 |
| `tools/_gen_sentiment.py` | 从色彩台账生成 `sentiment` 段 |
| `tools/core_audit.py` | 生成核心层机械提案 |
| `tools/pos_consistency_audit.py` | 只读的词性一致性扫描 |
| `tools/audit_all.py` | 只读的跨文件一致性巡检；发现问题非零退出 |
| `tools/merge_examples.py` | 校验并合并例句分批文件 |
| `tools/make_data.py` | 生成 `js/data.js` |
| `tools/make_examples.py` | 生成 `js/examples.js` |

### 回归与巡检入口

当前测试清单以[测试与巡检](testing.md)为准。测试文件使用易识别的稳定名称：`*_test.py`、`dom_smoke_test.js`、`contrast_sweep.py` 与 `responsive_audit.py`。

### 审计、一次性生成与调试留档

- `tools/_audit/` 保存特定轮次的审计脚本、判据和留档。它们是历史证据，不是默认流水线；活工具（如跨文件一致性巡检）应放 `tools/` 顶层并入测试矩阵。
- `tools/_gen_ledger*.py`、`tools/_ledger_r66.py` 等是**特定轮次的一次性台账生成器**。不要为“刷新数据”重跑；核心层调整应编辑现行台账，再运行正式落段器。
- `tools/_round5.py` 是已退役的第五轮改动清单，保留备查，勿重跑。
- `tools/_r60_check.py` 是第六十轮例句批次的只读自检器，对 `data/examples_parts/part_*.json` 仍可复用。
- `_shot_*`、`_dbg_*`、`_ui_*` 等名称通常表示截图探针或调试脚本（如 `_ui_sweep.py` 全页截图巡检），不代表可以不经检查直接删除。清理前先查引用、工作区归属和是否仍有复现价值。
- `_upd_changelog_hdr.py` 是 CHANGELOG 头部三数与「已落」清单的同步工具：**先追加节正文，再跑它**，三数由它按现文件实算，不要手改头部数字。
- 下划线前缀不是“可删除”标记；它只说明脚本不是常规用户入口。

## 临时产物与本地交接

以下路径被 `.gitignore` 排除，不应作为正式资料入库：

- `tools/_tmp/`、`tools/_tmp_*/`、`tools/tools/`：临时副本与中间产物；
- `shots/`、`.shots/`、`tools/_shots/`、`tools/_audit/ui/`、`tools/_audit/ui-review-*/`：巡检截图；
- `tools/_audit/*.png`、`*.jpg`、`*.jpeg`：审计图片；
- `.playwright-mcp/`：浏览器工具本地产物；
- `HANDOFF-*.md`：特定会话的本地交接单，可能包含过时状态，不属于现行文档。

`.gitignore` 不会自动脱管已经跟踪的文件。清理已入库产物时需要显式处理索引，并在操作前检查是否属于其他窗口的在途工作。

这些目录的生命周期管理（轮次子目录、收尾即清、清理前确认并发窗口空闲）见[协作与文档维护](contributing.md#临时产物生命周期)。

## 安全整理规则

1. 先运行 `git status --short`，区分已跟踪修改、未跟踪文件和暂存内容。
2. 未跟踪不等于垃圾；多窗口共享工作树时，它可能是别人刚创建的文件。
3. 移动运行文件前同时搜索脚本引用、文档相对链接和测试路径。
4. 删除一次性脚本前确认其产出已经入库，且历史记录没有要求保留可复跑证据。
5. 不用“文件很久没改”作为删除依据；原始数据和历史台账本来就应长期稳定。
