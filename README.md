# GUAN 学术英语词汇库 · Academic English Lexicon

一个纯前端的学术英语词汇学习网站，词库经人工增删与审校整理：
**当前词库 2222 词（核心高频 1060 个），其中 2158 词带词性分类、1698 词带感情色彩、2222 词带语体色彩**，每词配 3 条中英对照例句。
无需构建、无外部运行时依赖，可完全离线使用。

## 文档导航

| 需求 | 入口 |
|---|---|
| 启动网站与了解功能 | 本页；[详细使用指南](docs/user-guide.md) |
| 修改词条、例句、核心层或分类 | [数据与生成流水线](docs/data-pipeline.md) |
| 运行测试、浏览器巡检或变异验证 | [测试与巡检](docs/testing.md) |
| 查找文件、辨认真源与清理临时产物 | [项目结构](docs/project-structure.md) |
| 提交改动、更新文档与 CHANGELOG | [协作与文档维护](docs/contributing.md) |
| 查阅全部文档与同步清单 | [文档索引](docs/README.md) |
| 查阅逐轮决策和历史改动 | [CHANGELOG](CHANGELOG.md) |

## 快速开始

任选其一：

```bash
# 方式 1：直接用浏览器打开 index.html，file:// 即可完整运行

# 方式 2：在仓库根目录启动静态服务器
python3 -m http.server 8000
# 然后访问 http://localhost:8000
```

发音使用浏览器内置语音合成与系统语音包；没有英语音色时会提示安装，不使用其他语言音色兜底。

## 功能概览

| 模块 | 说明 |
|---|---|
| 🏠 首页 | 学习仪表盘、今日目标、复习预报、随机一词与最近测验 |
| 📖 词库 | 全量搜索、五组正交筛选、动态数量、学习状态筛选、排序、分页与打印；表格 / 卡片 / 按词性分组三种视图 |
| 🔍 全局搜索 | 按 `/` 唤起，按命中强度排序并显示命中处；结果可直通词库完整列表 |
| 🃏 学习 | 今日目标、按范围开卡（推荐范围自动预选）、莱特纳五盒间隔重复、快捷键与触屏手势；卡背直接展示完整词条和 3 条例句 |
| ✍️ 测验 | 看词选义、看义选词、拼写填空、听音辨词、例句挖空；支持混合出题与错题重测 |
| ⭐ 收藏 | 一键收藏，按收藏范围学习 / 测验，导出纯文本清单 |
| 📊 统计 | 掌握进度、记忆等级、120 天活跃热力图、词性与首字母分布、测验历史 |
| ⚙️ 设置 | 明暗主题、朗读语速、每日目标、JSON 导出 / 导入与重置 |
| 🔊 发音 | 点击才朗读，学习自动朗读默认关闭；无英语音色时不读英文并禁用听音辨词 |

筛选、卡片背面、搜索排序和快捷键的完整说明见[使用指南](docs/user-guide.md)。

## 本地数据与隐私

学习进度、收藏、设置和访问统计保存在浏览器 `localStorage`，主存档键为 `wl_state_v1`，不上传服务器。换机或换浏览器前，请在设置页导出 JSON 备份，再于目标环境导入。

顶栏徽标统计最近 30 天访问次数；首页“连续学习”统计连续学习天数，两者口径不同。

## 项目结构

```text
index.html              # 页面骨架
css/style.css           # 样式、主题、响应式布局与打印
js/app.js               # 原生 JavaScript 应用逻辑
js/data.js              # 生成的词表数据，勿手改
js/examples.js          # 生成的例句数据，勿手改
data/                   # 原始数据、内容真源、裁定台账与生成产物
tools/                  # 生成器、测试、审计器与历史留档脚本
docs/                   # 使用与维护专题文档
README.md               # 项目入口
CHANGELOG.md            # 逐轮历史记录
```

重点真源与生成物：

- 词条整理：`data/curation.json` 七段 → `data/words.json` / `data/cats.json` → `js/data.js`；
- 核心层：`data/core_decisions.json` 是唯一裁定台账；
- 感情与语体色彩：`data/sentiment_decisions.json` 是唯一裁定台账；
- 例句：`data/examples_parts/part_*.json` → `data/examples.json` → `js/examples.js`。

完整文件职责、一次性脚本说明与临时目录规则见[项目结构](docs/project-structure.md)。

## 维护入口

| 操作 | 主要入口 |
|---|---|
| 应用七段整理清单 | `python3 tools/curate.py` |
| 重新生成前端词表 | `python3 tools/make_data.py` |
| 合并并校验例句 | `python3 tools/merge_examples.py` |
| 重新生成前端例句 | `python3 tools/make_examples.py` |
| 核心层机械提案 | `python3 tools/core_audit.py` |
| 词性一致性扫描 | `python3 tools/pos_consistency_audit.py` |

修改词条时**不要直接编辑生成物**，也不要重排词条编号。`add`、`recat`、`core`、`noncore`、`sentiment` 各有上游真源；完整生成顺序、段归属和编号规则见[数据与生成流水线](docs/data-pipeline.md)。

## 快速验证

```bash
# 零依赖 DOM 与状态机回归
node tools/dom_smoke_test.js

# 流水线与内容守卫
python3 tools/pipeline_test.py
python3 tools/content_test.py
```

浏览器测试、无障碍、对比度、版面、焦点、多视口和变异测试的职责与命令见[测试与巡检](docs/testing.md)。断言数量以实跑输出为准；任何新出现的失败都应按真实问题定位，不能沿用历史上的 Windows 假红解释。

## 协作与变更记录

本仓库可能有多个窗口共享工作树。提交前必须检查 `git status --short`，只暂存自己的改动，**不要 `git add -A`**，也不要还原或删除他人的在途文件。

提交格式、共享文件处理、文档同步清单和 CHANGELOG 取号规则见[协作与文档维护](docs/contributing.md)。历史正文保持不改，新记录按追加式写入 [CHANGELOG](CHANGELOG.md)。

内容与词典链接版权归原作者 Ji-Huan Guan（CC BY）。
