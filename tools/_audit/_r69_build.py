# -*- coding: utf-8 -*-
"""冻结第六十九轮增补词表（word, pos, sub, gloss, core, reason）。一次性脚本。"""
import json

R = []


def W(w, pos, gloss, core=False, reason="", sub=None):
    R.append({"word": w, "pos": pos, "sub": sub, "gloss": gloss,
              "core": core, "reason": reason})


AWL = "AWL 词族命中，学术核心"
SKEL = "学术骨架词命中，学术论证高频"
REP = "报告动词组（that-引述高频），学术论证核心"
FUNC = "学术论证功能词，限定与评价承载论证功能"

# ── G1 r67 遗留 58 词（whilst 因全库统一美式拼写口径剔除）──────────────
g1 = [
    ("interestingly", "副词", "有趣的是；耐人寻味地（结果评论标记）", 0, FUNC),
    ("surprisingly", "副词", "出乎意料地；意外地（反预期标记）", 0, FUNC),
    ("remarkably", "副词", "显著地；异常地（程度评论标记）", 0, FUNC),
    ("strikingly", "副词", "醒目地；惊人地（差异评论，strikingly different）", 0, FUNC),
    ("tellingly", "副词", "说明问题地；有力地（tellingly, … 证据评论）", 0, FUNC),
    ("curiously", "副词", "奇怪的是（curiously enough 反预期标记）", 0, FUNC),
    ("wherein", "副词", "在其中；在…方面（正式书面，a situation wherein…）", 0, "正式书面限定副词，学术书面高频"),
    ("thereof", "副词", "由此；其（法律/正式书面，the result thereof）", 0, "正式书面限定副词，学术书面高频"),
    ("confer", "动词", "授予；带来（confer an advantage；confer with 协商）", 0, "学术论述常用动词"),
    ("afford", "动词", "提供；给予（afford an opportunity；买得起）", 0, "学术论述常用动词"),
    ("circumvent", "动词", "规避；绕过（circumvent the limitation）", 0, "学术论述常用动词"),
    ("curtail", "动词", "削减；限制（curtail spending / freedom）", 0, "政策论述常用动词"),
    ("curb", "动词", "抑制；约束（curb inflation / emissions）", 0, "政策论述常用动词"),
    ("thwart", "动词", "阻挠；使受挫（thwart the attempt）", 0, "学术论述常用动词"),
    ("hamper", "动词", "妨碍；阻碍（hamper progress）", 0, "学术论述常用动词"),
    ("halt", "动词", "使停止；终止（bring to a halt；calls to halt）", 0, "学术论述常用动词"),
    ("erode", "动词", "侵蚀；逐步削弱（erode confidence / margins）", 0, "趋势论述常用动词"),
    ("corrode", "动词", "腐蚀；（比喻）损害（corrode trust）", 0, "趋势论述常用动词"),
    ("accrue", "动词", "积累；产生（benefits accrue to…）", 0, "趋势论述常用动词"),
    ("uphold", "动词", "维持（原判）；支持；维护（uphold the decision / standards）", 0, "学术论述常用动词"),
    ("permeate", "动词", "渗透；弥漫（permeate every aspect of…）", 0, "学术论述常用动词"),
    ("pervade", "动词", "遍及；充斥（pervade the literature）", 0, "学术论述常用动词"),
    ("subsume", "动词", "纳入；归入（be subsumed under a category）", 0, "学术论述常用动词"),
    ("demarcate", "动词", "划界；区分（demarcate the boundary between…）", 0, "学术论述常用动词"),
    ("preempt", "动词", "预先制止；先发制人（preempt criticism）", 0, "学术论述常用动词"),
    ("facet", "名词", "方面；侧面（every facet of the problem）", 0, "学术论述常用名词"),
    ("hindrance", "名词", "妨碍；阻碍（a hindrance to progress）", 0, "学术论述常用名词"),
    ("boon", "名词", "裨益；福音（a boon to researchers）", 0, "学术论述常用名词"),
    ("property", "名词", "性质；属性（physical properties）；财产", 1, SKEL),
    ("landscape", "名词", "图景；格局（the research/policy landscape）；风景", 0, "学术论述常用名词"),
    ("terrain", "名词", "地形；（比喻）领域（familiar terrain）", 0, "学术论述常用名词"),
    ("strand", "名词", "（思路、论证的）一条线索（a strand of argument）；股、缕", 0, "学术论述常用名词"),
    ("thread", "名词", "线索；脉络（the thread of the argument）；线", 0, "学术论述常用名词"),
    ("asymmetry", "名词", "不对称（information asymmetry 信息不对称）", 0, "学术论述常用名词"),
    ("homogeneity", "名词", "同质性（test for homogeneity）", 0, "学术论述常用名词"),
    ("symmetry", "名词", "对称（性）（symmetry breaking 对称破缺）；匀称", 0, "学术论述常用名词"),
    ("mismatch", "名词", "错配；不匹配（skill mismatch）", 0, "学术论述常用名词"),
    ("inconsistency", "名词", "不一致；矛盾（internal inconsistency）", 0, "学术论述常用名词"),
    ("submission", "名词", "提交；投稿（manuscript submission；revisions on resubmission）", 0, "学术出版流程名词"),
    ("rebuttal", "名词", "反驳；答辩（peer-review rebuttal letter）", 0, "学术出版流程名词"),
    ("preprint", "名词", "预印本（post a preprint on arXiv）", 0, "学术出版流程名词"),
    ("erratum", "名词", "（出版物）勘误（复数 errata）", 0, "学术出版流程名词"),
    ("corrigendum", "名词", "（作者更正启事）勘误表（复数 corrigenda）", 0, "学术出版流程名词"),
    ("abrupt", "形容词", "突然的；陡然的（an abrupt change/transition）", 0, "趋势描述形容词，通用", "中性的"),
    ("abruptly", "副词", "突然地；陡然地（fall abruptly）", 0, "趋势描述副词，通用", None),
    ("gradual", "形容词", "逐渐的；渐进的（a gradual decline）", 0, "趋势描述形容词，通用", "中性的"),
    ("swift", "形容词", "迅速的；敏捷的（a swift recovery）", 0, "趋势描述形容词，通用", "积极的"),
    ("swiftly", "副词", "迅速地（respond swiftly）", 0, "趋势描述副词，通用", None),
    ("steep", "形容词", "陡的；（比喻）急剧的（a steep rise）；苛刻的（a steep price）", 0, "趋势描述形容词，通用", "中性的"),
    ("steeply", "副词", "陡峭地；急剧地（decline steeply）", 0, "趋势描述副词，通用", None),
    ("smooth", "形容词", "平滑的；顺利的（a smooth transition）", 0, "趋势描述形容词，通用", "中性的"),
    ("smoothly", "副词", "平滑地；顺利地（proceed smoothly）", 0, "趋势描述副词，通用", None),
    ("marked", "形容词", "显著的；明显的（a marked improvement）", 0, "趋势描述形容词，通用", "积极的"),
    ("persistent", "形容词", "持续存在的；顽固的（persistent inequality）", 0, "趋势描述形容词，通用", "中性的"),
    ("fleeting", "形容词", "转瞬即逝的（a fleeting glimpse）", 0, "趋势描述形容词，通用", "中性的"),
    ("enduring", "形容词", "持久的；经久不衰的（enduring influence）", 0, "趋势描述形容词，通用", "积极的"),
    ("lasting", "形容词", "持久的；长久的（a lasting impact）", 0, "趋势描述形容词，通用", "积极的"),
    ("invariant", "形容词", "不变的（量、性质）（scale-invariant；an invariant of the transformation）", 0, "量与性质描述形容词，窄域", "中性的"),
]
for row in g1:
    W(row[0], row[1], row[2], bool(row[3]), row[4], row[5] if len(row) > 5 else None)

# ── G2 论证/报告动词与名词 ───────────────────────────────────────
g2 = [
    ("argue", "动词", "主张，论证说（argue that… 主张…；argue for/against 支持/反对）", 1, REP),
    ("appraise", "动词", "评价；评估（appraise the evidence / appraise the significance of…）", 1, "评价动词，与 appraisal 同族"),
    ("appraisal", "名词", "评估；评价；鉴定（a critical appraisal of the method）", 0, "评价性名词，文献评述高频"),
    ("reiterate", "动词", "重申；反复说明（reiterate the importance of…）", 0, "讨论与结论段常用论证动词"),
    ("restate", "动词", "重述；重新表述（restate the hypothesis / restate the question）", 0, "论证结构动词，引言与结论高频"),
    ("reconsider", "动词", "重新考虑；重新审视（reconsider the design / reconsider our interpretation）", 0, "论证动作动词，讨论段高频"),
    ("situate", "动词", "把…置于（背景/框架）中（situate the study within…）", 0, "定位性陈述动词，引言高频"),
    ("delimit", "动词", "划定界限；界定范围（delimit the scope / delimit the research question）", 0, "界定研究边界的标准动词"),
    ("reconstruct", "动词", "重建；还原（reconstruct the process / reconstruct the history）", 0, "过程与机制论文常用动词"),
    ("overstate", "动词", "夸大；言过其实（overstate the findings / overstate the implications）", 0, "学术谦抑表达常用动词"),
    ("bolster", "动词", "支持；增强（bolster the argument / bolster the case）", 0, "论证支撑动词"),
    ("reframe", "动词", "重新表述；重构框架（reframe the question / reframe the analysis）", 0, "框架调整动词，理论贡献段高频"),
    ("rethink", "动词", "重新思考；重构思路（rethink the unit of analysis）", 0, "理论贡献段常用动词"),
    ("interrogate", "动词", "追问；细查（interrogate the data / interrogate an assumption）", 0, "方法论批评与质性研究常用动词"),
    ("objection", "名词", "反对意见；异议（raise objections to / a valid objection）", 1, AWL),
    ("counterexample", "名词", "反例（a counterexample to the claim）", 0, "反驳型论证的标准元件"),
    ("misconception", "名词", "误解；错误观念（students' misconceptions）", 0, "教育研究与理论纠偏段高频"),
    ("burden", "名词", "负担；举证责任（the burden of proof / the burden of explanation）", 0, "证据强度论述标准名词"),
    ("concordance", "名词", "一致；符合（concordance correlation；语料索引）", 0, "一致性分析名词"),
    ("modality", "名词", "方式；模态；表现形式（modalities of governance）", 0, "质性与传播研究固定名词"),
]
for w, p, g, c, r in g2:
    W(w, p, g, bool(c), r)

# ── G3 评价性形容词 ───────────────────────────────────────────────
g3 = [
    ("sound", "形容词", "可靠的；严谨的（sound reasoning；methodologically sound）", 1, SKEL),
    ("credible", "形容词", "可信的；有信誉的（credible evidence / credible mechanism）", 1, "评价证据可信度的核心形容词"),
    ("convincing", "形容词", "有说服力的；令人信服的（convincing evidence / a convincing argument）", 0, "评价论证力度的常用形容词"),
    ("germane", "形容词", "切题的；贴切的（germane to the question）", 0, "评价证据与论题相关性的精确用词"),
    ("epistemological", "形容词", "认识论的；知识论的（epistemological grounding）", 0, "理论型论文讨论段高频限定词"),
    ("ontological", "形容词", "本体论的；存在论的（ontological commitments）", 0, "理论定位高频限定词"),
    ("axiomatic", "形容词", "公理的；基于公理的（an axiomatic foundation）", 0, "形式化论证基础描述词"),
    ("abductive", "形容词", "溯因的；最佳解释推论的（abductive inference）", 0, "与 deductive/inductive 构成推理三分"),
    ("descriptive", "形容词", "描述性的；描述统计的（descriptive statistics）", 1, "描述性研究与因果推断的基本术语"),
    ("prescriptive", "形容词", "规定性的；规范的（a prescriptive claim）", 0, "与 descriptive 对举，方法论定位高频"),
    ("incisive", "形容词", "尖锐的；切入要害的（an incisive critique）", 0, "评价评论深度的标准学术词"),
    ("penetrating", "形容词", "有洞察力的；透彻的（a penetrating analysis）", 0, "评价分析深度的常用词"),
    ("scholarly", "形容词", "学术的；学术性的（scholarly debate / scholarly tradition）", 1, "修饰学术语域名词的高频词"),
    ("judicious", "形容词", "明智的；审慎的（a judicious use of sources）", 0, "评价文献取舍的常用正式词"),
    ("prudent", "形容词", "谨慎的；审慎的（prudent policy recommendations）", 0, "应用型论文评价建议稳妥性高频词"),
    ("astute", "形容词", "精明的；敏锐的（an astute reading of the evidence）", 0, "评价研究判断力的褒义学术词"),
    ("apt", "形容词", "恰当的；切题的（an apt description / an apt term）", 0, "评价术语贴切的简洁常用词"),
    ("appreciable", "形容词", "相当大的；可观的（an appreciable effect）", 0, "量化结果陈述区分可观测与可感知程度"),
    ("landmark", "形容词", "里程碑式的；划时代的（a landmark study / a landmark discovery）", 0, "文献综述评价原创性高频词"),
    ("invariably", "副词", "总是；始终如一地（invariably follows from…）", 0, "确定性副词族中空缺的一格"),
    ("narrow", "形容词", "狭窄的；局限的（a narrow scope / a narrow focus）", 1, SKEL),
]
for w, p, g, c, r in g3:
    W(w, p, g, bool(c), r, "中性的" if p == "形容词" else None)

# ── G4 冲突与限定形容词 ───────────────────────────────────────────
g4 = [
    ("inconsistent", "形容词", "不一致的；自相矛盾的（inconsistent with prior findings）", 0, "描述结果或理论冲突的常用形容词"),
    ("conflict", "名词", "冲突；抵触（a conflict between theory and evidence）", 1, AWL),
    ("conflicting", "形容词", "相互冲突的；抵触的（conflicting evidence）", 1, AWL),
    ("contested", "形容词", "有争议的；被争夺的（a contested concept）", 1, AWL),
    ("disputed", "形容词", "有争议的；受到质疑的（disputed findings）", 0, "评价他人结论的高频形容词"),
    ("contentious", "形容词", "有争议的；易引起争执的（a contentious issue）", 0, "争议性判断词"),
    ("inconclusive", "形容词", "不确定的；无定论的（inconclusive results）", 0, "元分析最常见的结论性限定语之一"),
    ("indirect", "形容词", "间接的（an indirect effect / indirect evidence）", 0, "因果推断论文的标准限定词"),
    ("unbiased", "形容词", "无偏的（an unbiased estimator）", 0, "统计学描述估计量性质的标准形容词"),
    ("nontrivial", "形容词", "不平凡的；显著的（a nontrivial effect）", 0, "效应与挑战程度的常用限定词"),
    ("desirable", "形容词", "可取的；合乎需要的（a desirable property）", 0, "评价设计特性与结论价值常用词"),
    ("secondary", "形容词", "次要的；辅助的（a secondary outcome）", 1, SKEL),
    ("unambiguous", "形容词", "明确的；不含糊的（unambiguous evidence）", 0, "作者对结果清晰性的自我评价常用词"),
    ("insufficient", "形容词", "不足的；不充分的（insufficient evidence / insufficient power）", 0, "样本量与证据力度论证的标准判断词"),
    ("multiple", "形容词", "多个的；多重的（multiple regression / multiple comparisons）", 0, "统计方法与设计描述的超高频词"),
]
for w, p, g, c, r in g4:
    W(w, p, g, bool(c), r, "中性的" if p == "形容词" else None)

# ── G5 学术元名词 ─────────────────────────────────────────────────
g5 = [
    ("study", "名词", "研究；研究论文（a longitudinal study；the study reports）", 1, SKEL),
    ("paper", "名词", "论文；（学术）文章", 0, "英文学术语域自称与指称论文的第一高频词"),
    ("discussion", "名词", "讨论；（论文的）讨论部分", 1, SKEL),
    ("review", "名词", "综述；评述；评审（a systematic review；peer review）", 1, AWL),
    ("practice", "名词", "实践；惯例（best practice；clinical practice）", 1, SKEL),
    ("statistics", "名词", "统计学；统计数据（the statistics reported here）", 1, AWL),
    ("input", "名词", "输入；投入（model inputs；policy inputs）", 1, AWL),
    ("task", "名词", "任务；研究任务（the task was to…）", 1, SKEL),
    ("standpoint", "名词", "立场；观点（尤指分析或解释的出发点）", 0, "方法论与理论论文的框架词"),
    ("lens", "名词", "透镜；视角（through the lens of）", 0, "跨学科论文的固定喻用框架"),
    ("barrier", "名词", "障碍；壁垒（barriers to adoption）", 0, "采纳意愿与技术转移研究高频构式"),
    ("continuum", "名词", "连续体；连续谱（a continuum of care）", 0, "社会科学分类论述常用词"),
    ("utility", "名词", "效用；效用（论）（utility function）", 1, AWL),
]
for w, p, g, c, r in g5:
    W(w, p, g, bool(c), r)

# ── G6 研究方法与统计 ─────────────────────────────────────────────
g6 = [
    ("match", "动词", "配对，使（两组）在可观测特征上可比（matched design 配对设计）", 0, "配对设计是控制混杂的通用手段"),
    ("nonresponse", "名词", "无应答；未回应（nonresponse rate 无应答率）", 0, "抽样调查最主要的选择偏倚来源之一"),
    ("census", "名词", "普查；全样本调查（census data 普查数据）", 0, "与抽样调查相对的全覆盖数据来源"),
    ("pilot", "名词", "试点；预试验（a pilot study 预试验研究）", 0, "预试验用于检验可行性与估算样本量"),
    ("quasi-experimental", "形容词", "准实验的（a quasi-experimental design）", 0, "无法随机分配时最常用的替代设计名"),
    ("CONSORT", "名词", "CONSORT 声明（随机对照试验报告规范）", 0, "RCT 投稿的事实标准报告清单"),
    ("STROBE", "名词", "STROBE 声明（观察性研究报告规范）", 0, "观察性研究论文的通用报告清单"),
    ("standard error", "名词", "标准误", 0, "与标准差、置信区间并列的三大报告量"),
    ("covariance", "名词", "协方差", 0, "相关分析、多元回归的基本量"),
    ("heteroskedasticity", "名词", "异方差性；异方差", 0, "OLS 假设检验与稳健标准误的核心诊断项"),
    ("autocorrelation", "名词", "自相关", 0, "时间序列与面板数据推断的前提条件"),
    ("missing data", "名词", "数据缺失；缺失值", 0, "缺失机制决定可用插补方法"),
    ("bootstrap", "动词", "以自助法重抽样（估计）", 0, "小样本下置信区间的标准做法"),
    ("permutation", "名词", "置换；置换检验（a permutation test）", 0, "无分布检验方法"),
    ("degrees of freedom", "名词", "自由度", 0, "几乎每个方差分析与回归结果都要报告"),
    ("chi-square", "名词", "卡方；卡方检验（χ²）", 0, "列联表分析最常用的检验"),
    ("Monte Carlo", "名词", "蒙特卡洛（模拟方法）", 0, "复杂分布下推断与贝叶斯后验近似的标准手段"),
    ("median", "名词", "中位数", 0, "描述统计的基本集中趋势量"),
    ("quartile", "名词", "四分位数", 0, "分布描述与箱线图报告的常规统计量"),
    ("percentile", "名词", "百分位数", 0, "参照值与评分分布分析的常用统计量"),
    ("recall", "名词", "召回率；查全率", 0, "分类与信息检索评价的核心指标"),
    ("confusion matrix", "名词", "混淆矩阵", 0, "分类器性能报告的默认呈现形式"),
    ("ground truth", "名词", "真值；真值标注", 0, "评价预测正确性的参照答案"),
    ("overfitting", "名词", "过拟合", 0, "模型泛化讨论中的核心问题"),
    ("regularization", "名词", "正则化；规则化", 0, "惩罚项方法的统称"),
    ("annotation", "名词", "标注；注释", 0, "NLP 语料建设与质性编码的核心活动"),
    ("coding", "名词", "编码（质性研究中的编码过程）", 0, "质性分析的骨架步骤"),
    ("transcription", "名词", "转录；文字转写", 0, "访谈与录音材料处理的第一步"),
    ("member checking", "名词", "成员核验（让受访者核对分析结果）", 0, "质性研究可信度最常被提及的检验手段"),
    ("audit trail", "名词", "审计轨迹；决策留痕记录", 0, "质性编码与伦理审查要求的过程可追溯性证据"),
    ("purposive", "形容词", "目的性（抽样的）（purposive sampling 目的性抽样）", 0, "质性研究最主要的抽样策略"),
    ("ethnography", "名词", "民族志（研究方法）", 0, "质性方法的三大支柱之一"),
    ("latent", "形容词", "潜在的；潜伏的（a latent variable 潜在变量）", 1, SKEL),
    ("screening", "名词", "筛查；筛选（受试者或文献筛选）", 0, "系统综述与临床试验流程图的固定环节"),
    ("surveillance", "名词", "监测；疾病监测（surveillance data）", 0, "流行病学与公共卫生的独立方法族"),
    ("scoping review", "名词", "范围综述", 0, "近十年快速扩张的证据综述类型"),
    ("peer review", "名词", "同行评议；同行评审", 0, "出版流程核心概念"),
    ("conflict of interest", "名词", "利益冲突", 0, "期刊投稿必填声明项"),
    ("open access", "名词", "开放获取（开放存取）", 0, "出版与文献计量论文的固定名词"),
    ("grant", "名词", "资助；课题经费（a grant proposal 基金申请书）", 1, SKEL),
]
for w, p, g, c, r in g6:
    W(w, p, g, bool(c), r, "中性的" if p == "形容词" else None)

# ── G7 跨学科领域通用词 ───────────────────────────────────────────
g7 = [
    ("platform", "名词", "平台；（计算/传播/研究）承载数据与服务的底层平台", 0, "数字化学科论文的必答题词"),
    ("architecture", "名词", "体系结构；架构", 0, "系统与软件类论文的固定术语"),
    ("repository", "名词", "存储库；资料库；数据仓储", 0, "开放数据与文献共享语境下的高频机构名"),
    ("interoperability", "名词", "互操作性", 0, "跨系统数据打通议题的核心术语"),
    ("metadata", "名词", "元数据", 0, "数据集与馆藏描述的基础词"),
    ("ontology", "名词", "本体（知识表示体系）", 0, "信息学与知识组织论文的核心术语"),
    ("privacy", "名词", "隐私（隐私保护）", 1, AWL),
    ("cybersecurity", "名词", "网络安全", 0, "系统与信息类论文的通用风险类别词"),
    ("intellectual property", "名词", "知识产权", 1, AWL),
    ("copyright", "名词", "版权", 0, "出版伦理与开放获取声明段落的高频词"),
    ("open science", "名词", "开放科学", 0, "近年跨所有学科的顶层政策概念"),
    ("open data", "名词", "开放数据", 0, "与开放科学配套出现的高频政策术语"),
    ("climate change", "名词", "气候变化", 0, "跨自然科学的公共议题术语"),
    ("land use", "名词", "土地利用", 0, "城市、地理、农业与生态论文的通用研究对象名"),
    ("public health", "名词", "公共卫生", 1, AWL),
    ("health inequality", "名词", "健康不平等", 0, "公共卫生与社会政策的常设议题"),
    ("life expectancy", "名词", "预期寿命", 0, "人口学与卫生经济学共同使用的核心指标名"),
    ("mental health", "名词", "心理健康", 1, AWL),
    ("risk factor", "名词", "风险因素", 0, "流行病学与临床研究的通用术语"),
    ("randomized controlled trial", "名词", "随机对照试验", 1, "健康与行为科学中最核心的证据类型名"),
    ("numeracy", "名词", "计算能力；数理素养", 0, "教育学与公共政策话语中的核心素养概念"),
    ("instruction", "名词", "教学；教学活动", 1, AWL),
    ("scholarship", "名词", "学术研究成果", 0, "综述与贡献陈述段的高频名词"),
    ("enrollment", "名词", "入组；招募入组；注册入学（enrollment rate）", 0, "临床试验与教育统计的流程指标词"),
    ("engagement", "名词", "参与度；投入", 0, "教育、健康传播与平台治理共用的结果变量词"),
    ("behavior", "名词", "行为", 1, SKEL),
    ("taxation", "名词", "税收；税制", 0, "财政与公共经济论文的固定制度名词"),
    ("cost-effectiveness", "名词", "成本效果（成本效益比）", 0, "卫生技术评估与公共项目评价的标准指标名"),
    ("disincentive", "名词", "抑制因素", 0, "与 incentive 对举的激励设计术语"),
    ("audit", "名词", "审计；核查", 0, "从财务审计到数据核查与机构问责，审计类评价多学科通用"),
    ("supply chain", "名词", "供应链", 0, "运营、贸易、环境与公共卫生论文的共用概念词"),
    ("entrepreneurship", "名词", "创业；企业家精神", 0, "创新与区域经济研究的核心主题词"),
    ("unemployment", "名词", "失业", 0, "经济与劳动研究的核心指标"),
    ("workforce", "名词", "劳动力；全体员工", 1, SKEL),
    ("inequality", "名词", "不平等", 1, SKEL),
    ("artificial intelligence", "名词", "人工智能", 0, "当代跨学科论文的头号通用领域词"),
    ("machine learning", "名词", "机器学习", 0, "所有应用学科引用方法的通用标签词"),
    ("fairness", "名词", "公平性", 0, "算法治理与公共服务分配研究的高频评价维度词"),
    ("framing", "名词", "框架化；框定（叙事/媒体框架）", 0, "框架分析是传播、气候与政策研究的标准方法名"),
    ("misinformation", "名词", "错误信息", 0, "信息环境研究的通用术语"),
    ("disinformation", "名词", "虚假信息（蓄意）", 0, "与 misinformation 并列区分意图"),
    ("statistical significance", "名词", "统计显著性", 0, "结果章的通用判定语"),
    ("systematic review", "名词", "系统综述", 1, AWL),
    ("mixed methods", "名词", "混合方法", 0, "方法章声明研究设计范式的固定名"),
    ("gender", "名词", "性别", 1, AWL),
    ("ethnicity", "名词", "族裔；民族", 1, AWL),
]
for w, p, g, c, r in g7:
    W(w, p, g, bool(c), r)

# ── G8 学术写作中已收但形态缺失的补齐 ─────────────────────────────
g8 = [
    ("review", "动词", "综述；评述（review the literature / review the evidence）", 1, AWL),
    ("practice", "动词", "练习；执业；实践（practise what one preaches）", 0, "与 practice 名词同族补齐"),
]
for w, p, g, c, r in g8:
    if not any(x["word"] == w and x["pos"] == p for x in R):
        W(w, p, g, bool(c), r)

# 去重（同名同词性只留第一条）
seen = set()
out = []
for x in R:
    k = (x["word"], x["pos"])
    if k in seen:
        continue
    seen.add(k)
    out.append(x)

json.dump(out, open('tools/_audit/_r69_a.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
ncore = sum(1 for x in out if x["core"])
print('total %d  core %d (%.1f%%)  noncore %d'
      % (len(out), ncore, 100.0 * ncore / len(out), len(out) - ncore))
