# -*- coding: utf-8 -*-
"""
知识库增强：为 19683 卦加入「规范层卦表 + 一致性偏差标注」，并生成 SQLite 与数据质量报告。
- 规范层卦表 = 三进制编码（编号=底中顶三态, D=0,R=1,T=2, +1），经语料多数派验证为权威约定。
- 每卦保留原文声明的 上/中/下 名称与爻值，同时标注其相对规范表的偏差。
"""
import json, os, sqlite3, csv

ROOT = "/home/user/Doubao/chats/38447794378988290/三元九维19683大模型/知识库"
d = json.load(open(os.path.join(ROOT, "三元九维19683_全集.json"), encoding="utf-8"))

CANON_NAME = ["厚藏","待衡","启生","衡藏","双衡","启衡","抑扬","扬衡","奋生",
              "基衡","上下衡","基启","双衡藏","全衡","衡启","抑衡","扬双衡","衡奋",
              "基扬抑","基扬衡","对扬","基扬抑衡","基扬双衡","扬衡启","奋抑","奋衡","全扬"]
def canon(num):
    n = num - 1; out = []
    for _ in range(3):
        out.append(["D","R","T"][n % 3]); n //= 3
    return list(reversed(out))

layer_table = {}
for i in range(27):
    num = i + 1
    v = canon(num)
    layer_table[num] = {
        "编号": num, "规范名称": CANON_NAME[i], "规范三爻": v,
        "判定数": v.count("R"), "承载数": v.count("D"), "增益数": v.count("T"),
        "逐位语义": [("底","中","顶")[j] + v[j] for j in range(3)]
    }

# 语义字典
SEM = {
    "D": "承载·按物理属性削减·能封存兜底·无分辨·不审定·不回灌",
    "R": "判定·审定/否决/回灌·分辨有序无序·输出评估信息·管控吞吐",
    "T": "增益·萌发原生动能·整形生发·对外释放信息",
}

def flag_record(r):
    up = canon(r["上编号"]); mp = canon(r["中编号"]); lo = canon(r["下编号"])
    declared = r["九爻值"]
    canonical = up + mp + lo
    match = (declared == canonical)
    # 偏差类型
    dev = []
    if r["上编号"] in layer_table and declared[0:3] != up:
        dev.append(f"上卦{r['上编号']:02d}声明{''.join(declared[0:3])}≠规范{''.join(up)}")
    if declared[3:6] != mp:
        dev.append(f"中卦{r['中编号']:02d}声明{''.join(declared[3:6])}≠规范{''.join(mp)}")
    if declared[6:9] != lo:
        dev.append(f"下卦{r['下编号']:02d}声明{''.join(declared[6:9])}≠规范{''.join(lo)}")
    r["规范九爻值"] = canonical
    r["九爻一致"] = match
    r["偏差说明"] = "；".join(dev) if dev else ""
    return r

recs = [flag_record(r) for r in d["卦"]]

# 覆盖规范层卦表 + 语义
d["层卦规范"] = []
for num in range(1, 28):
    t = dict(layer_table[num])
    t["逐位语义"] = [pos + "·" + v + "：" + SEM[v] for pos, v in zip(["底", "中", "顶"], t["规范三爻"])]
    d["层卦规范"].append(t)
d["语义字典"] = SEM

# 写回全集
with open(os.path.join(ROOT, "三元九维19683_全集.json"), "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=1)

# SQLite
db_path = os.path.join(ROOT, "三元九维19683.db")
if os.path.exists(db_path): os.remove(db_path)
con = sqlite3.connect(db_path); cur = con.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS gua(
  id TEXT PRIMARY KEY, shang INT, zhong INT, xia INT,
  guaname TEXT, seq TEXT, seqvals TEXT,
  zishitext TEXT, zishi TEXT, panding INT, chengzai INT, zengyi INT,
  consistent INT, deviation TEXT, docfile TEXT)""")
for r in recs:
    docfile = f"{r['上编号']:02d}上{r['中编号']:02d}中"
    cur.execute("INSERT OR REPLACE INTO gua VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (f"{r['上编号']:02d}{r['中编号']:02d}{r['下编号']:02d}",
         r["上编号"], r["中编号"], r["下编号"],
         r.get("复合卦名",""), r.get("九爻序列",""), "".join(r["九爻值"]),
         r.get("自适配等级",""), r.get("自适配评估","").replace("**",""),
         r["判定数"], r["承载数"], r["增益数"],
         1 if r["九爻一致"] else 0, r["偏差说明"], docfile))
con.commit()
cur.execute("CREATE INDEX IF NOT EXISTS idx_gua_shang ON gua(shang,zhong,xia)")
con.commit(); con.close()
print("SQLite 写入完成:", db_path)

# 数据质量报告
from collections import Counter
n_total = len(recs); n_match = sum(1 for r in recs if r["九爻一致"])
print(f"卦总数 {n_total}，与规范表一致 {n_match}，偏差 {n_total-n_match}")

# 偏差按文件聚合
dev_files = Counter()
for r in recs:
    if not r["九爻一致"]:
        dev_files[f"{r['上编号']:02d}上{r['中编号']:02d}中"] += 1

lines = []
lines.append("# 三元九维19683体系 · 数据质量与一致性报告\n")
lines.append(f"- 卦总数：**{n_total}**（729 文件 × 27 卦）")
lines.append(f"- 九爻序列与规范层卦表一致：**{n_match}**（{n_match/n_total:.1%}）")
lines.append(f"- 存在偏差：**{n_total-n_match}**（涉及 {len(dev_files)} 个文件）\n")
lines.append("## 一、规范层卦表（三进制权威约定）\n")
lines.append("|编号|规范名称|底·中·顶|判定|承载|增益|逐位语义|")
lines.append("|---|---|---|---|---|---|---|")
for t in d["层卦规范"]:
    lines.append(f"|{t['编号']:02d}|{t['规范名称']}|{'·'.join(t['规范三爻'])}|{t['判定数']}|{t['承载数']}|{t['增益数']}|{'；'.join(t['逐位语义'])}|")
lines.append("")
lines.append("## 二、偏差概况\n")
lines.append("同一编号在语料中出现多套取值，多数派即规范表。主要偏差来源：")
lines.append("1. **上卦块错位**：编号 07/08/09/10/12–21 的整块「NN上」文件（各 729 卦）把上卦名称与爻值用成了相邻编号的取值（如 07上 块把上卦写成「基衡R,D,D」而非规范「抑扬D,T,D」），但块内正文与声明值自洽。")
lines.append("2. **中卦模板残留**：`01上08中`、`05上06中`~`05上21中` 等文件的中卦爻值被模板默认成 D,R,R。")
lines.append("3. **下卦零散错位**：`05上14中`、`05上15中`、`05上18中` 的下卦 05/25/26 爻值错位。")
lines.append("")
lines.append("## 三、逐文件偏差统计（仅列有偏差的文件）\n")
lines.append("|文件|偏差卦数|")
lines.append("|---|---|")
for fk, c in sorted(dev_files.items()):
    lines.append(f"|{fk}|{c}|")
lines.append("")
lines.append("> 说明：知识库忠实保留每卦原文声明值与正文。若需统一为规范表，可据本报告批量校正上/中/下卦名与爻值，并同步改写受影响的正文。")
report = "\n".join(lines)
with open(os.path.join(ROOT, "数据质量报告.md"), "w", encoding="utf-8") as f:
    f.write(report)
print("报告写入:", os.path.join(ROOT, "数据质量报告.md"))
print(report[:600])
