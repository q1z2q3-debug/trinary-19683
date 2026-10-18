# -*- coding: utf-8 -*-
"""
三元九维19683 推理引擎（大模型核心）
- 加载全集知识库
- 查询：按 上/中/下 编号、九爻编号、复合卦名、九爻序列 检索
- 分析：判定/承载/增益统计、层间制衡、自适配等级、规范一致性
- 生成：基于27层卦规则语义，对任意构型合成解读（在原文之外提供可推演能力）
- 抽签：随机取卦
"""
import json, os, random, re

ROOT = os.path.dirname(os.path.abspath(__file__))
KB = os.path.join(ROOT, "知识库", "三元九维19683_全集_规范校正版.json")

SEM = {
    "D": "承载：按物理属性削减，能封存兜底，无分辨，不审定，不回灌",
    "R": "判定：审定/否决/回灌，分辨有序无序，输出评估信息，管控吞吐",
    "T": "增益：萌发原生动能，整形生发，对外释放信息",
}
POS = ["底层", "中位", "顶层"]
LAYER_ROLE = {"上": "大势", "中": "枢纽", "下": "底盘"}
LEVEL_RANK = {"极弱":0,"弱":1,"较弱":2,"中等偏弱":3,"中等":4,"中等偏上":5,"较强":6,"强":7,"极强":8}


class Engine:
    def __init__(self, kb_path=KB):
        with open(kb_path, encoding="utf-8") as f:
            self.data = json.load(f)
        self.recs = self.data["卦"]
        self.layer = {t["编号"]: t for t in self.data["层卦规范"]}
        self.sem = self.data.get("语义字典", SEM)
        self.by_id = {self._id(r): r for r in self.recs}
        # 名称->卦 索引
        self.by_name = {}
        for r in self.recs:
            self.by_name.setdefault(r.get("复合卦名", ""), []).append(r)

    @staticmethod
    def _id(r):
        return f"{r['上编号']:02d}{r['中编号']:02d}{r['下编号']:02d}"

    # ---------- 查询 ----------
    def query(self, shang, zhong, xia):
        key = f"{int(shang):02d}{int(zhong):02d}{int(xia):02d}"
        return self.by_id.get(key)

    def query_by_pattern(self, nine_vals):
        """按9爻序列(D/R/T串)精确查卦（先查一致卦）。"""
        target = list(re.sub(r"[^DRT]", "", nine_vals.strip().upper()))
        if len(target) != 9 or any(c not in "DRT" for c in target):
            return None
        for r in self.recs:
            if r["九爻值"] == target:
                return r
        return None

    def search(self, text):
        text = text.strip()
        if not text:
            return []
        # 编号格式
        m = re.fullmatch(r"(\d{1,2})[-—/_. ]*(\d{1,2})[-—/_. ]*(\d{1,2})", text)
        if m:
            a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if all(1 <= x <= 27 for x in (a, b, c)):
                return [self.query(a, b, c)]
        # 9爻序列
        if re.fullmatch(r"[DRTdrｔｔ｜|,\s]+", text) and len(re.findall(r"[DRT]", text.upper())) == 9:
            r = self.query_by_pattern(text)
            return [r] if r else []
        # 名称/关键字
        out = []
        for r in self.recs:
            if text in r.get("复合卦名", "") or text in r.get("九爻编号", ""):
                out.append(r)
            if len(out) >= 20:
                break
        return out

    # ---------- 分析 ----------
    def analyze(self, r):
        vals = r["九爻值"]
        segs = {"上": vals[0:3], "中": vals[3:6], "下": vals[6:9]}
        res = {
            "判定数": r["判定数"], "承载数": r["承载数"], "增益数": r["增益数"],
            "三层": {}, "九爻一致": r["九爻一致"], "偏差说明": r["偏差说明"],
            "自适配等级": r["自适配等级"],
        }
        for role, v in segs.items():
            res["三层"][role] = {
                "爻值": "".join(v),
                "判定": v.count("R"), "承载": v.count("D"), "增益": v.count("T"),
                "名称": self.layer[r[{"上":"上编号","中":"中编号","下":"下编号"}[role]]]["规范名称"] if r["九爻一致"] else r.get({"上":"上卦","中":"中卦","下":"下卦"}[role], ""),
            }
        # 层间制衡判断
        res["制衡"] = self._balance(vals)
        return res

    def _balance(self, v):
        up, mid, lo = v[0:3], v[3:6], v[6:9]
        notes = []
        upR, upT = up.count("R"), up.count("T")
        midR, midT = mid.count("R"), mid.count("T")
        loR, loT = lo.count("R"), lo.count("T")
        if upR == 0 and upT == 0:
            notes.append("上层纯承载：不读信息、不自知、不对外释放，成果滞留锁界。")
        if upR > 0 and upT == 0:
            notes.append("上层有判定无增益：算得清但送不出去，价值在于内部存量纯度。")
        if upT > 0:
            notes.append("上层有增益单元：具备对外释放/生发的通道。")
        if midR == 0 and midT == 0:
            notes.append("中层纯承载：对上行分量一律削减，判定与增益归零。")
        if loR == 0 and loT == 0:
            notes.append("底层纯承载：无自发扰动，资源沉淀封存。")
        if v.count("R") == 0:
            notes.append("全卦零判定：分不清有序与无序。")
        if v.count("T") == 0:
            notes.append("全卦零增益：无撬动能力，只有消耗能力。")
        if v.count("D") == 9:
            notes.append("九爻全承载：全体系最安静的一卦，纯衰减构型。")
        return notes

    # ---------- 规则生成 ----------
    def generate(self, shang, zhong, xia):
        """基于层卦规则语义，对构型合成结构化解读（不依赖原文）。"""
        parts = []
        for role, num in [("上", shang), ("中", zhong), ("下", xia)]:
            t = self.layer[int(num)]
            parts.append(f"{role}卦{num:02d}{t['规范名称']}【{'·'.join(t['规范三爻'])}】")
        head = "｜".join(parts)
        vals = [c for n in (shang, zhong, xia) for c in self.layer[int(n)]["规范三爻"]]
        seg = {"上": vals[0:3], "中": vals[3:6], "下": vals[6:9]}
        # 逐层解读
        body = []
        for role in ["下", "中", "上"]:
            t = self.layer[int({"下": xia, "中": zhong, "上": shang}[role])]
            lines = [f"{role}卦（{LAYER_ROLE[role]}）{t['规范名称']}："]
            for i, c in enumerate(t["规范三爻"]):
                lines.append(f"  {POS[i]}{c}：{self.sem[c]}")
            body.append("\n".join(lines))
        # 综合
        nR, nD, nT = vals.count("R"), vals.count("D"), vals.count("T")
        from level9 import level9
        level = level9(tuple(vals))
        return {
            "构型": head,
            "九爻": "".join(vals),
            "判定/承载/增益": f"{nR}/{nD}/{nT}",
            "逐层": "\n\n".join(body),
            "自适配等级": level,
            "制衡要点": "\n".join(self._balance(vals)),
            "是否规范": True,
            "类型": "规则生成",
        }

    @staticmethod
    def _level_from_counts(nR, nT, nD):
        score = nR + 2 * nT
        if nD == 9: return "极弱"
        if score == 0: return "极弱"
        if score <= 2: return "弱"
        if score <= 4: return "中等"
        if score <= 6: return "较强"
        if score <= 8: return "强"
        return "极强"

    def random_gua(self, seed=None):
        rng = random.Random(seed)
        return rng.choice(self.recs)

    def stats(self):
        from collections import Counter
        c = Counter(r["自适配等级"] for r in self.recs)
        return {
            "总卦数": len(self.recs),
            "层卦数": 27,
            "一致卦数": sum(1 for r in self.recs if r["九爻一致"]),
            "自适配分布": dict(c.most_common()),
        }


if __name__ == "__main__":
    e = Engine()
    print("=== 统计 ===")
    print(e.stats())
    print("\n=== 查询 01/01/02 ===")
    r = e.query(1, 1, 2)
    print("卦名:", r["复合卦名"], "| 九爻:", r["九爻序列"], "| 等级:", r["自适配等级"])
    print("一致性:", "一致" if r["九爻一致"] else "偏差-" + r["偏差说明"])
    print("\n=== 规则生成 14/27/01 (全衡/全扬/厚藏) ===")
    g = e.generate(14, 27, 1)
    print(g["构型"])
    print(g["逐层"])
    print("等级:", g["自适配等级"])
    print("\n=== 搜索「全静」===")
    for x in e.search("全静"):
        print(" ", x["九爻编号"], x["复合卦名"])
