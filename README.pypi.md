# 三元九维19683认知体系（trinary19683）

把《三元九维19683体系》（729 份语料、**19683 卦**）构建为**可复算、可证伪、可演化的确定性符号认知层**——可被 LLM 与 Agent 调用。

## 它是什么

不是"算命"工具，而是一个**可生长的确定性认知系统**，分两层：

**① 三元九维确定性推理层**
- 每卦 = 上·中·下三层 × 3 爻，三态（D 承载 / R 判定 / T 增益），共 **19683 卦**
- 确定性自适配等级（5 维结构签名，19683 卦 100% 可复算）
- 动态势能流推演、三态公理语义推导、时序演化路径

**② 认知棋盘 v2（升级层）**
- **证伪动力学**：三档证伪（全命中硬迁/部分降置信/预设外降级），可逆，治幻觉
- **元棋盘 L4**：M(X) 元评估 + 策略调整 + M(M(X)) 递归自省（自指/反思）
- **多 Agent 共享协议 L5**：冲突定位到具体迁移边 + 共享证据证伪对撞 + 可复算联合链

## 安装

```bash
pip install trinary19683
```

首次使用拉取全量知识库（可选，用于全文查询/检索）：
```bash
python3 scripts/download_data.py   # 从 HuggingFace 拉取 19683 卦全量数据
```

## 快速开始

```python
# 确定性等级
from level9 import level9_str
print(level9_str("RRRTTTDDD"))            # → 中等（可复算）

# 语义推导（从三态公理，不依赖语料）
from infer import infer_by_num
print(infer_by_num(14, 27, 1)["上层输出"])

# 动态推演（自下而上势能流）
from dynamics import flow
nodes, final = flow("DDDTTTRRR")

# 证伪器（认知棋盘）
from cognition_board import Stance, Evidence, Refuter
r = Refuter(); r.add_condition("P", ["反证A"], all_required=True, fallback="Q")
s, e = r.check(Stance("P", {"ACT": 1.0}, confidence=0.8), Evidence({"反证A": True}))
```

## 本地服务 / 控制台

```bash
trinary-server 8000     # 或 python3 server.py 8000
# 浏览器打开 http://127.0.0.1:8000/
```

离线单文件模型：`三元九维19683_离线模型.html`（双击即用，含推演/推导/等级/扰动/演化建议/路径）。

## 文档

- `三元九维19683_使用与设计总说明书.md`
- `三元九维19683_开放API文档.md`
- `认知棋盘v2设计提案.md`

## License

Apache-2.0
