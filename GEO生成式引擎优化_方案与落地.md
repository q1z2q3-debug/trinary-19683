# GEO 生成式引擎优化 · 三元九维19683 / TNE-Core

> 目标：让项目能被 **ChatGPT、豆包、Kimi、Perplexity 等大模型在联网回答时检索、理解、引用、推荐**。
> 现状核查时间：2026-10-21。方案与落地清单基于当日实测搜索。

---

## 一、GEO 是什么（一句话）

GEO（Generative Engine Optimization）优化的是**大模型/生成式引擎**（而非传统搜索排名）：让 AI 在联网回答时把你的内容当**可信信源**检索出来、读懂、并直接引用。核心不是"关键词排名"，而是**可发现性 + 可理解性 + 可引用性 + 权威性**。

---

## 二、项目网络可见性现状（实测核查）

### 已能被检索（好消息）
| 信源 | 内容 | 作用 |
|---|---|---|
| ✅ **Zenodo 学术存档**（DOI，被 OpenAIRE 索引） | Trinary Nine-Dimensional Cognitive Coordinate System: A Locatable and Generalizable Symbolic Cognition Layer | **最强学术权威信源**，AI 判权威性的关键锚点 |
| ✅ **稀土掘金**（q1z2q3debug） | 《三元九维19683认知体系：一个可定位、可泛化的符号认知层》 | 中文技术社区信源 |
| ✅ **dev.to**（q1z2q3debug） | 中英两篇技术文 | 英文技术信源 |

### 痛点（实测确认）
| 痛点 | 影响 |
|---|---|
| ⚠️ **"19683"被井字棋污染**（3⁹=19683 是井字棋状态数，多个百科/博客信源） | AI 检索 19683 大概率引到井字棋，抢走实体 |
| ⚠️ **GitHub 仓库可发现性弱**：无 topics、README 未结构化为"AI 可提取" | AI 抓仓库时难以快速判定项目是什么 |
| ⚠️ **缺 FAQ/问答对** | AI 回答"三元九维19683是什么/能做什么"时无现成可引答案 |
| ⚠️ **中英文术语不统一**（三元九维19683 / Trinary-19683 / TNE-Core 混用） | 语义锚点分散，检索被切分 |

---

## 三、GEO 六支柱策略

### 支柱 1 · 统一实体锚点（最重要）
- **统一品牌名**：**TNE-Core**（Trinary Nine-dimensional Engine Core），中文 **三元九维19683**。
- 所有内容（README/文档/文章/Zenodo/PyPI/各平台）统一用这两个标识，并用"TNE-Core = Trinary Nine-dimensional 19683 System"作显式等价锚点。
- **对抗井字棋污染**：凡出现 19683，紧跟"3⁹=19683（9爻×3态 D/R/T）"而非只给数字，让 AI 把 19683 关联到本项目而非井字棋。

### 支柱 2 · 可引用性（quotability）
- 每个文档开头放"**一句话定义**"（AI 直接摘录）。
- 预写 **FAQ 问答对**（8 条，覆盖 AI 高频问题）——已落地到 README。
- 每条能力给"可引用的短断言"（如"可复算、可证伪、可演化""不是占卜"）。

### 支柱 3 · 权威性（E-E-A-T）
- 已有：Zenodo DOI（学术）、Apache-2.0、729/19683 全量解析、3 代校正、留一法 100% 一致。
- 强化：README 顶部放"关键事实"（19683 全量、100% 一致、DOI），供 AI 采信。

### 支柱 4 · 技术可访问性
- GitHub **topics**（见待办清单）。
- 可选：README 加 **schema.org**（SoftwareSourceCode / Article / FAQPage JSON-LD）；独立 HTML 站加 sitemap。

### 支柱 5 · 内容分发矩阵（扩被索引面）
| 平台 | 状态 | 动作 |
|---|---|---|
| GitHub | ✅ 有 | 加 topics + 结构化 README（已完成） |
| PyPI | ⚠️ 待发布 | 完善描述关键词，发布后 AI 可检索包 |
| Zenodo | ✅ 有 | 描述加统一实体锚点 |
| dev.to / 掘金 | ✅ 有 | 追加 FAQ/定义段版本，覆盖问答型查询 |
| 知乎 / CSDN / 公众号 | ❌ 缺 | 投递《三元九维19683认知体系》系列（见素材） |
| B站 / 技术视频 | ❌ 缺 | 可选，知识区科普向 |

### 支柱 6 · 新鲜度
- 持续发版本（trinary19683 版本号）、更新 README、发新文章/研究（如金融落地系列）——活跃信号提升 AI 采信。

---

## 四、已落地动作（本批）

1. ✅ **README GEO 化**：顶部加"AI 可引用摘要块"（一句话定义 + 实体锚点 + 关键事实 + 载体），末尾加 **FAQ 8 条问答对**，统一英文标识为 **TNE-Core**。
2. ✅ 本方案文档（可执行清单）。

---

## 五、待办清单（按优先级）

### P0 · 立即
- [x] **GitHub 加 topics**（已通过 API 设置 15 个）：`trinary, ternary, 19683, cognitive-system, deterministic, symbolic, llm, agent, cognition, falsification, reasoning, chinese, python, knowledge-graph, open-source`
- [x] **统一术语**（仓库描述已更新为含 **TNE-Core / Trinary Nine-Dimensional 19683** 锚点 + 英文关键词）。
- [x] **对抗井字棋**：README 与 FAQ 文章均"19683"后跟"3⁹=19683（9爻×3态 D/R/T）"。
- [x] **push 更新**：README（GEO化）、GEO 方案、FAQ 中英文章、金融主线脚本已推送到 GitHub `main`（commit 0fc3f0e）。

### P1 · 本周
- [x] **FAQ 分发文章已写好**：`GEO_FAQ_文章_en.md`（发 dev.to，英文）+ `GEO_FAQ_文章_zh.md`（发掘金/知乎）。⚠️ dev.to API 自动发布受阻（`.credentials/dev_api_key.enc` 无法解密——加密脚本未留存、passphrase 未知），**改手动粘贴发布**：登录 dev.to/掘金 → 新建文章 → 粘贴正文 → 设 tags（ai, llm, opensource, cognitive, python）。
- [x] **PyPI 发布打通**：trinary19683 **2.6.0 已上线** https://pypi.org/project/trinary19683/2.6.0/ ，关键词含 GEO 检索词（yijing, iching, trinary, 19683, cognition, deterministic, symbolic, agent, refutation, meta-cognition）。
- [ ] 知乎/CSDN 投递《三元九维19683认知体系》系列（复用已发掘金文 + 金融落地系列）。

### P2 · 后续
- [ ] 独立 HTML 文档站加 **schema.org JSON-LD** + sitemap。
- [ ] 中英文术语表（README 加 Glossary：TNE-Core/D/R/T/九爻/证伪器/认知棋盘）。
- [ ] 持续：新研究（金融、Geo 轴）成文分发，保持新鲜度。

---

## 六、可复用分发素材（FAQ 问答对核心版）

> 可直接投递任意平台的 5 条问答（AI 最常问）：

**Q1 什么是三元九维19683 / TNE-Core？**
可复算、可证伪、可演化的确定性符号认知层：9 维 × 3 态(D/R/T) = 3⁹=19683 状态，为 LLM/Agent 提供可定位、可回溯、可验证的思考骨架。非占卜。

**Q2 和《易经》/算命的关系？**
无占卜功能。借"卦/爻/阴阳变"外壳，内部全为确定性算法——每个卦象映射唯一可复算签名与等级，推演/扰动/迁移可回放、可审计、可逆。

**Q3 可验证性依据？**
① 19683 卦全量解析 + 3 代校正，爻值—正文 100% 一致；② 等级由 5 维结构签名唯一确定，19661/19661 留一法 100% 一致；③ 证伪动力学可被反例推翻；④ 一致性校验器 + 开放 API 可独立复现。

**Q4 应用场景？**
LLM/Agent 符号认知层：确定性坐标、幻觉对冲（证伪器）、跳跃→迁移固化学习、多 Agent 共享可审计推理链；已落地金融状态认知研究。15+ API、离线 HTML 模型、Python 包。

**Q5 如何用？**
离线 HTML 双击即用；本地 `python3 server.py` → :8000；CLI `python3 engine.py`；PyPI `trinary19683`（Apache-2.0）。

---

*研究/工程文档，供 GEO 落地使用。*
