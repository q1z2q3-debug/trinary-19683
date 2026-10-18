# 三元九维19683 大模型 · Trinary-19683 Cognitive System

> **EN** · *中文详版见下方 / Full Chinese documentation below.*

---

## English Overview

A **recomputable, falsifiable, evolvable deterministic symbolic cognition layer**, built from the *Trinary Nine-Dimensional 19683 System* (729 sources, **19,683 gua**) — not a divination tool, but a deterministic cognitive anchor for LLMs / agents.

**Structure:** each gua = 3 layers (upper/trend · middle/pivot · lower/base) × 3 lines = **9 lines**; each line is one of three states — **D** (carry/deposit), **R** (judge/feedback), **T** (gain/release). Total = **3⁹ = 19,683**.

**Highlights**
- **Deterministic reasoning layer** — full 19,683-gua space with a 3-generation corrected canonical table, deterministic self-adaptive rank (5-dim structural signatures, 100% recomputable, leave-one-out validated 100%), dynamic potential-flow inference, three-state axiomatic semantics, temporal evolution paths.
- **Cognition Board v2** — falsification dynamics (tiered refutation, reversible migration, self-contradiction detection), Meta-Board L4 (M(X) meta-evaluation + M(M(X)) recursive self-examination), multi-agent protocol L5 (conflict localization to a migration edge, recomputable joint chains).
- **Why it is not fortune-telling** — every gua / jump / migration carries a deterministic signature and an auditable trace: recomputable, verifiable, replayable, reversible.

**Delivery:** standalone offline HTML model / inference workbench / service console (15+ APIs) / Python package (Apache-2.0).

**Quick start**
```bash
# local service (full corpus + cognition board console)
python3 server.py          # default port 8000 → http://127.0.0.1:8000/

# CLI inference engine
python3 engine.py
python3 -c "from engine import Engine; e=Engine(); print(e.generate(14,27,1)['构型'])"

# cognition board demos
python3 cognition_board.py   # falsification / guided jump / dual-corpus learning
python3 multi_agent.py       # multi-agent consensus from conflict
python3 meta_board.py        # M(M(X)) recursive self-examination
```

**Links:** GitHub `q1z2q3-debug/trinary-19683` · License **Apache-2.0** · data hosted on HuggingFace (see `scripts/download_data.py`).

---

# 中文详版 · Full Chinese Documentation

## 体系是什么

- **结构**：每卦 = 三层（上卦·大势 / 中卦·枢纽 / 下卦·底盘）× 每层 3 爻 = **9 爻**。
- **三态**：每爻三态——**D** 承载（削减/封存）、**R** 判定（审定/回灌）、**T** 增益（生发/释放）。
- **总数**：3⁹ = **19683** 卦，对应 729 文件 × 每文件 27 卦。
- **层卦编码**：27 种层卦 = 三进制（D=0, R=1, T=2，底→顶），编号 01=厚藏DDD … 27=全扬TTT。

> **规范校正版（当前版本）**：初版语料中同一层卦编号在不同文件出现不同爻值。本版已按三进制规范层卦表统一校正全部 19683 卦的结构身份（上/中/下规范名称、爻值、九爻序列、判定/承载/增益、自适配等级）；原九爻值≠规范值的 11105 卦，正文已按规范爻值以语料富文本重建，保证「爻值—正文」一致；其余 8578 卦正文原样保留。离线模型、服务、SQLite/CSV/层卦表均基于校正版数据。

## 交付物

| 文件 | 说明 |
|---|---|
| `三元九维19683_离线模型.html` | **单文件、双击即可用**的离线模型（内嵌 27 层卦规则 + 19683 卦索引 + **推理面板**：动态推演/语义推导/确定性等级/点爻扰动，无需安装/联网） |
| `index.html` + `server.py` | 完整版交互界面 + 本地服务（含 19683 卦**全文**解读 + **认知棋盘工作台**：证伪/多Agent/元评估流程演示 + 实时元评估器） |
| `engine.py` | 推理引擎（查询/分析/规则生成/检索/抽签） |
| `三元九维19683_推演推导工作台.html` | **单文件离线**推演·推导工作台（动态势能流 + 三态公理推导 + 确定性等级 + 扰动演化 + **演化建议**） |
| `dynamics.py` | **动态推演引擎**（扰动任意爻→全链路势能流演化） |
| `infer.py` | **语义推导器**（从三态公理推导任意构型，不依赖语料模板） |
| `level9.py` | **确定性自适配等级函数**（5维结构签名→等级，19683卦100%一致、可复算） |
| `validator.py` | **一致性校验器**（结构不变量+正文断言，可作回归测试） |
| `cognition_board.py` | **认知棋盘 v2 最小原型**（基元层 + 认知张量 + 三档证伪动力学 + 跳跃→迁移三联验证 + 受引导跳跃 + 正/反例双库；`python3 cognition_board.py` 演示 agent 决策全流程） |
| `multi_agent.py` | **多 Agent 共享协议最小原型**（冲突检测定位到具体迁移边 + 共享证据证伪对撞 + 置信度合并收敛 + 可复算联合推导链；`python3 multi_agent.py` 演示两派收敛） |
| `meta_board.py` | **元棋盘（L4 自指/反思层）最小原型**（M(X) 元评估 + 策略调整 + M(M(X)) 递归自省 + 元层可证伪；`python3 meta_board.py` 演示"审视自己的结论"） |
| `三元九维19683_使用与设计总说明书.md` | 整套系统的权威使用与设计总说明 |
| `三元九维19683_开放API文档.md` | 开放 API 文档（端点/参数/跨语言调用示例） |
| `认知棋盘v2设计提案.md` | 「认知棋盘」v2 设计提案（可生长的确定性认知空间，已落成最小原型） |
| `知识库/` | 结构化知识库：`三元九维19683_全集_规范校正版.json`(校正版全部卦全文，当前引擎数据源)、`三元九维19683_全集.json`(初版原文备份)、`三元九维19683.db`(SQLite)、`三元九维19683_索引.csv`、`三元九维19683_层卦表.json`、`三元九维19683_等级签名表.json`(等级查表)、`数据质量报告.md`(规范校正报告)、`一致性校验报告.md` |

## 快速开始

**方式一 · 离线模型（推荐，最快）**
> 直接用浏览器打开 `三元九维19683_离线模型.html` 即可推演、检索、随机抽卦。

**方式二 · 完整版本地服务（含全文解读）**
```bash
cd 三元九维19683大模型
python3 server.py            # 默认端口 8000
# 浏览器打开 http://127.0.0.1:8000/
```

**方式三 · 命令行推理引擎**
```bash
python3 engine.py            # 自测示例
python3 -c "from engine import Engine; e=Engine(); print(e.query(1,1,2)['复合卦名']); print(e.generate(14,27,1)['构型'])"
```

## 接口（服务版）

- `GET /api/stats` 体系统计
- `GET /api/layers` 27 层卦规范表
- `GET /api/gua?shang=&zhong=&xia=` 查询某卦（返回原文全文 + 分析）
- `GET /api/generate?shang=&zhong=&xia=` 规则生成解读
- `GET /api/search?q=` 按编号 / 卦名 / 9 爻序列检索
- `GET /api/random` 随机抽卦
- `GET /api/infer?shang=&zhong=&xia=` 语义推导（三态公理，不查语料）
- `GET /api/flow?shang=&zhong=&xia=` 动态推演（自下而上势能流 + 指标 + 等级）
- `GET /api/level?shang=&zhong=&xia=` 确定性自适配等级
- `GET /api/evolve?shang=&zhong=&xia=&idx=&newc=` 扰动演化对比（原/新势能流、等级、输出/滞留变化）
- `GET /api/derive9?seq=RRRTTTDDD` 按 9 爻综合推理（推导 + 推演 + 等级，前端扰动实时重算用）
- `GET /api/suggest?shang=&zhong=&xia=&top=3` 演化建议（确定性穷举单爻改动，给出最优增强方向）
- `GET /api/trace?shang=&zhong=&xia=&steps=4` 时序演化路径（顺势倾向 + 贪心逐代干预轨迹，含每步构型/等级/输出）
- `GET /api/cognition` 认知棋盘 v2 流程（跑通 agent 决策的证伪/迁移/受引导跳跃全流程）
- `GET /api/agents` 多 Agent 共享协议（从冲突到共识的可复算联合推导链）
- `GET /api/meta` 元棋盘 L4（M(X) 元评估 + 策略调整 + M(M(X)) 递归自省）

## 认知棋盘层（整体更新）

在三元九维确定性推理之上，新增「认知棋盘 v2」——把静态状态地图升级为**带记忆、会证伪、能自省、可共享的活的认知系统**：

- **三元九维 = 棋盘的退化特例**：三态（D/R/T）可视为棋盘在 3 个基元（SUP+SUS / VRF+GAT / ACT+MRG）下的实例。
- **认知张量**：状态 = 格局 × 投影 × 置信度 × 历史（不再是孤立点）。
- **三档证伪动力学**：全命中硬迁（可逆）/ 部分降置信 / 预设外降级；自我矛盾检测 = 内源反例（棋盘可判定，LLM 难自查）。
- **跳跃→迁移三联验证**：自由联想经 V1一致性/V2可逆性/V3收益性 → 权威边（入正例库）或试探边。
- **受引导跳跃**：证伪失败不缩回，沿失败点生成修正格局，失败成为生成正确的原料。
- **双库学习闭环**：正例库（成功模式）+ 反例库（失败模式），可反向修正证伪条件，供蒸馏。

> 定位：棋盘给思考提供骨架/坐标/尺子（可复算、可校验、可回溯、可逆）；认知主体仍是 Agent/大模型。完整设计见 `认知棋盘v2设计提案.md`。

## 重要说明：数据质量

全量解析发现，原始语料存在**编号取值不一致**（详见 `知识库/数据质量报告.md`）：

- 知识库**忠实保留每卦原文**（照录各文件的声明爻值、卦名与正文），并逐卦标注「与规范表是否一致」。
- **规范层卦表**以三进制规律为准（经语料多数派验证）。约 **8578/19683 卦与规范表一致**，另有 412 个文件存在偏差，主要来自：
  1. 部分「NN上」整块（如 07上/08上…）把上卦名称/爻值用成了相邻编号的取值（块内正文与声明值自洽）；
  2. 少数文件（如 `01上08中`、`05上06中`~`05上21中`）中卦爻值被模板默认成 D,R,R；
  3. 零星下卦错位（`05上14/15/18中`）。
- 离线/服务模型的**推演解读**采用规范层卦规则生成；**检索到的原文解读**保留作者内容。若需将语料统一为规范表，可据报告批量校正。

## 数据统计（按规范层卦表）
- 自适配等级分布：中等 3902 / 弱 3769 / 极弱 2994 / 较强 2916 / 中等偏弱 2373 / 强 1584 / 中等偏上 971 / 较弱 796 / 极强 378。
