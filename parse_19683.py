# -*- coding: utf-8 -*-
"""
三元九维19683体系 · 全量解析器
将 729 份 docx（27上卦 × 27中卦，每份遍历 27 下卦）解析为结构化知识库。
输出：
  - 知识库/三元九维19683_全集.json        全部19683卦的完整结构化记录
  - 知识库/三元九维19683_索引.csv         精简索引（卦名/序列/自适配等级等）
  - 知识库/三元九维19683_层卦表.json      27种层卦定义（编号/名称/三爻值/语义）
"""
import zipfile, re, glob, json, os, csv

SRC = "/home/user/.doubao/agent_mode/workspace/.sessions/38447794378988290/attachments/extracted"
OUT_DIR = "/home/user/Doubao/chats/38447794378988290/三元九维19683大模型/知识库"
os.makedirs(OUT_DIR, exist_ok=True)

def docx_to_paras(path):
    z = zipfile.ZipFile(path)
    xml = z.read('word/document.xml').decode('utf-8')
    paras = re.findall(r'<w:p[ >].*?</w:p>', xml, re.S)
    return [''.join(re.findall(r'<w:t[^>]*>(.*?)</w:t>', p, re.S)).strip() for p in paras]

# ---------- 1. 提取 27 种层卦定义 ----------
layer_defs = {}          # key: 层卦编号(int) -> {编号,name,values,position_desc}
files = sorted(glob.glob(os.path.join(SRC, '*.docx')))
first_paras = docx_to_paras(files[0])
# 从 三层结构 行提取 上/中/下 各层卦名： 上01厚藏｜中01厚藏【D,D,D】｜下01厚藏【D D D】
# 兼容 逗号/空格 两种分隔
for f in files:
    for p in docx_to_paras(f):
        for m in re.finditer(r'([上下中])(\d{2})([^\n【｜]{1,6})【\s*([DTR])\s*[,，\s]\s*([DTR])\s*[,，\s]\s*([DTR])\s*】', p):
            pos, num, name, v1, v2, v3 = m.group(1), int(m.group(2)), m.group(3), m.group(4), m.group(5), m.group(6)
            layer_defs[num] = {"编号": num, "名称": name, "三爻": [v1, v2, v3], "位序": pos}

# 层卦语义（依据文档全局基调/运行逻辑提炼的定性语义）
SEMANTICS = {
    "D": "承载·按物理属性削减·能封存兜底·无分辨·不审定·不回灌",
    "R": "判定·审定/否决/回灌·分辨有序与无序·输出评估信息·管控吞吐",
    "T": "增益·萌发原生动能·整形/生发·对外释放信息",
}
def pos_label(i):  # 3爻位置说明（自底向上）
    return ["底层", "中位", "顶层"][i]

# 将 27 种层卦按 D/R/T 分布补充语义标注
for num in sorted(layer_defs):
    d = layer_defs[num]
    vals = d["三爻"]
    parts = []
    for i, v in enumerate(vals):
        parts.append(f"{pos_label(i)}{'·'+v}:{SEMANTICS[v].split('·')[0]}")
    d["逐位"] = parts
    d["判定数"] = vals.count("R")
    d["承载数"] = vals.count("D")
    d["增益数"] = vals.count("T")

# ---------- 2. 逐文件解析 27 卦块 ----------
def parse_file(path):
    paras = docx_to_paras(path)
    blocks = []
    # 定位所有卦块起始行
    starts = []
    for i, p in enumerate(paras):
        if re.match(r'^\d{2}｜\d{2}｜\d{2}\s', p):
            starts.append(i)
    starts.append(len(paras))
    for k in range(len(starts)-1):
        block = paras[starts[k]:starts[k+1]]
        blocks.append(block)
    return blocks

def parse_block(block):
    rec = {}
    for i, line in enumerate(block):
        # 卦首行: 01｜01｜01　全静六道承载零递送零输出卦
        m = re.match(r'^(\d{2})｜(\d{2})｜(\d{2})\s*(.*)$', line)
        if m and i == 0:
            rec["上编号"], rec["中编号"], rec["下编号"] = int(m.group(1)), int(m.group(2)), int(m.group(3))
            rec["复合卦名"] = m.group(4).strip()
            continue
        if line.startswith("九爻编号："):
            rec["九爻编号"] = line.split("：")[1].strip()
        elif re.match(r'^[上下中]\d{2}', line):
            mm = re.match(r'^上(\d{2})([^\n｜【]*)｜中(\d{2})([^\n｜【]*)｜下(\d{2})([^\n｜【]*)', line)
            if mm:
                rec["上卦"] = mm.group(2).strip(); rec["中卦"] = mm.group(4).strip(); rec["下卦"] = mm.group(6).strip()
            # 三层结构行里的三爻
            seq_m = re.search(r'【\s*([DTR])\s*,\s*([DTR])\s*,\s*([DTR])\s*】', line)
            if seq_m and "三层三爻" not in rec:
                pass
        elif line.startswith("九爻序列："):
            rec["九爻序列"] = line.split("：")[1].strip()
    # 段落字段抽取（按标题切分）
    full = "\n".join(block)
    def section(title):
        m = re.search(re.escape(title) + r"\n(.*?)(?=\n(?:分层拆解|跨层制衡|全局自适配能力评估|演化路径|复合卦总释)\n|\Z)", full, re.S)
        return m.group(1).strip() if m else ""
    rec["复合卦总释"] = section("复合卦总释")
    # 分层拆解（拆成3条）
    lj = section("分层拆解")
    rec["分层拆解"] = [x.strip() for x in lj.split("\n") if x.strip()]
    rec["跨层制衡"] = section("跨层制衡")
    # 自适配评估：第一行为等级，其后为正文
    zs = section("全局自适配能力评估")
    if zs:
        lines = [x.strip() for x in zs.split("\n") if x.strip()]
        rec["自适配等级"] = lines[0] if lines else ""
        rec["自适配评估"] = "\n".join(lines[1:]) if len(lines) > 1 else ""
    else:
        rec["自适配等级"], rec["自适配评估"] = "", ""
    # 演化路径
    yh = section("演化路径")
    evo = {}
    for line in yh.split("\n"):
        mm = re.match(r'^([①②])[\s\S]*?[:：]?\s*(.*)$', line.strip())
        if mm:
            evo["顺势演化" if mm.group(1) == "①" else "干预演化"] = mm.group(2).strip()
    # 去掉可能的重复前缀
    for k in list(evo):
        if evo[k].startswith("顺势演化") or evo[k].startswith("干预演化"):
            evo[k] = evo[k][4:] if "：" in evo[k][:5] else evo[k]
    rec["演化路径"] = evo
    # 派生指标
    seq = rec.get("九爻序列", "")
    vals = re.findall(r'[DTR]', seq)
    rec["九爻值"] = vals
    rec["判定数"] = vals.count("R")
    rec["承载数"] = vals.count("D")
    rec["增益数"] = vals.count("T")
    rec["三层值"] = [vals[0:3], vals[3:6], vals[6:9]]  # 上/中/下
    return rec

all_records = []
parse_errors = []
for f in files:
    try:
        blocks = parse_file(f)
    except Exception as e:
        parse_errors.append((os.path.basename(f), str(e)))
        continue
    for block in blocks:
        rec = parse_block(block)
        if rec.get("九爻编号"):
            all_records.append(rec)

print(f"解析完成：记录 {len(all_records)} 条，错误文件 {len(parse_errors)}")
if parse_errors:
    print("错误:", parse_errors[:10])

# 校验编号覆盖
ids = {(r["上编号"], r["中编号"], r["下编号"]) for r in all_records}
expected = {(a, b, c) for a in range(1, 28) for b in range(1, 28) for c in range(1, 28)}
print("唯一卦id数:", len(ids), "缺失:", len(expected - ids))

# ---------- 3. 输出 ----------
with open(os.path.join(OUT_DIR, "三元九维19683_全集.json"), "w", encoding="utf-8") as f:
    json.dump({"meta": {"体系": "三元九维19683体系", "卦总数": len(all_records),
                        "结构": "三层(上/中/下)×3爻=9爻, 每爻三态(D承载/R判定/T增益), 3^9=19683",
                        "来源": "729份docx(27上×27中, 每份遍历27下)"},
               "层卦": [layer_defs[n] for n in sorted(layer_defs)],
               "卦": all_records}, f, ensure_ascii=False, indent=1)

# CSV 索引
with open(os.path.join(OUT_DIR, "三元九维19683_索引.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["上编号","中编号","下编号","卦id","复合卦名","九爻序列","自适配等级","判定数","承载数","增益数"])
    for r in all_records:
        w.writerow([r["上编号"], r["中编号"], r["下编号"],
                    f"{r['上编号']:02d}{r['中编号']:02d}{r['下编号']:02d}",
                    r.get("复合卦名",""), r.get("九爻序列",""),
                    r.get("自适配等级",""), r["判定数"], r["承载数"], r["增益数"]])

with open(os.path.join(OUT_DIR, "三元九维19683_层卦表.json"), "w", encoding="utf-8") as f:
    json.dump([layer_defs[n] for n in sorted(layer_defs)], f, ensure_ascii=False, indent=1)

# 打印抽样
print("\n--- 层卦表(27) ---")
for n in sorted(layer_defs):
    d = layer_defs[n]
    print(f"{n:02d} {d['名称']} {d['三爻']} 判{d['判定数']}承{d['承载数']}增{d['增益数']}")
print("\n--- 抽样记录(第1条) ---")
print(json.dumps(all_records[0], ensure_ascii=False, indent=1)[:1500])
