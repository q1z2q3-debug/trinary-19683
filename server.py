# -*- coding: utf-8 -*-
"""
三元九维19683 大模型 · 本地服务
启动：  python3 server.py [端口]
打开：  http://127.0.0.1:8000/
接口：
  /                    交互式网页
  /api/stats           体系统计
  /api/layers          27层卦规范表
  /api/gua?shang=1&zhong=1&xia=2   查询某卦（原文全文）
  /api/generate?shang=&zhong=&xia= 规则生成解读
  /api/search?q=        按编号/卦名/九爻序列搜索
  /api/random           随机抽卦
  /api/infer?shang=&zhong=&xia=    语义推导（三态公理，不查语料）
  /api/flow?shang=&zhong=&xia=     动态推演（数值势能流 + 指标 + 等级）
  /api/level?shang=&zhong=&xia=    确定性自适配等级
  /api/evolve?shang=&zhong=&xia=&idx=&newc=   扰动演化对比
"""
import json, os, sys, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from engine import Engine
import dynamics, infer, level9, cognition_board, multi_agent, meta_board

ROOT = os.path.dirname(os.path.abspath(__file__))
engine = Engine()

def seq_of(shang, zhong, xia):
    """上/中/下编号 -> 9爻D/R/T序列（上+中+下）。"""
    return infer._canon(shang) + infer._canon(zhong) + infer._canon(xia)

def out(h, obj):
    b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    h.send_response(200)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Cache-Control", "no-store")
    h.send_header("Content-Length", str(len(b)))
    h.end_headers()
    h.wfile.write(b)

def clean(r):
    """去除 ** 强调标记，便于网页展示。"""
    if isinstance(r, dict):
        return {k: clean(v) for k, v in r.items()}
    if isinstance(r, list):
        return [clean(x) for x in r]
    if isinstance(r, str):
        return r.replace("**", "").replace("\u200b", "")
    return r

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):  # 静默
        pass

    def _api(self):
        q = urllib.parse.urlparse(self.path)
        u = urllib.parse.parse_qs(q.query)
        def gi(k, d=1):
            return int(u.get(k, [d])[0])
        if q.path == "/api/stats":
            return out(self, engine.stats())
        if q.path == "/api/layers":
            return out(self, clean(engine.layer))
        if q.path == "/api/gua":
            r = engine.query(gi("shang"), gi("zhong"), gi("xia"))
            if not r:
                return self._err("未找到该卦")
            r2 = clean(r); r2["analysis"] = clean(engine.analyze(r))
            return out(self, r2)
        if q.path == "/api/generate":
            g = engine.generate(gi("shang"), gi("zhong"), gi("xia"))
            return out(self, clean(g))
        if q.path == "/api/search":
            r = engine.search(u.get("q", [""])[0])
            return out(self, [clean(x) for x in r[:20]])
        if q.path == "/api/random":
            r = engine.random_gua()
            r2 = clean(r); r2["analysis"] = clean(engine.analyze(r))
            return out(self, r2)
        if q.path == "/api/infer":
            s, z, x = gi("shang"), gi("zhong"), gi("xia")
            r = infer.infer_by_num(s, z, x)
            return out(self, clean(r))
        if q.path == "/api/level":
            s, z, x = gi("shang"), gi("zhong"), gi("xia")
            return out(self, {"构型": "".join(seq_of(s, z, x)),
                              "自适配等级": level9.level9(tuple(seq_of(s, z, x))),
                              "方法": "确定性5维签名(level9, 全库100%一致)"})
        if q.path == "/api/derive9":
            s = u.get("seq", [""])[0].upper()
            if len(s) != 9 or any(c not in "DRT" for c in s):
                return self._err("需要9爻D/R/T(如 ?seq=RRRTTTDDD)")
            v = list(s)
            inf = infer.infer_seq(v)
            bu = v[6:] + v[3:6] + v[0:3]
            nodes, final = dynamics.flow(bu)
            m = dynamics.metrics(nodes, bu, final)
            return out(self, {
                "构型": s, "自适配等级": level9.level9(tuple(v)),
                "推导": {"底层势能": inf["底层势能"], "层间传递": inf["层间传递"],
                         "上层输出": inf["上层输出"], "关键制约": inf["关键制约"]},
                "推演": {"势能流": nodes, "最终输出": final, "累计滞留": m["累计滞留"],
                         "判定承载增益": [m["判定"], m["承载"], m["增益"]]}})
        if q.path == "/api/suggest":
            s, z, x = gi("shang"), gi("zhong"), gi("xia")
            top = gi("top", 3)
            seq = seq_of(s, z, x)
            return out(self, infer.suggest(seq, top=top))
        if q.path == "/api/trace":
            s, z, x = gi("shang"), gi("zhong"), gi("xia")
            steps = gi("steps", 4)
            seq = seq_of(s, z, x)
            return out(self, infer.trace(seq, steps=steps))
        if q.path == "/api/cognition":
            # 认知棋盘 v2：跑通 agent 决策全流程（可复算、可审计）
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                cognition_board.demo()
            return out(self, {"认知棋盘": "v2 最小原型", "流程": buf.getvalue()})
        if q.path == "/api/agents":
            # 多 Agent 共享协议：从冲突到共识的可复算联合链
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                multi_agent.demo()
            return out(self, {"多Agent共享协议": "v2 最小原型", "流程": buf.getvalue()})
        if q.path == "/api/meta":
            # 元棋盘 L4：自指/反思——审视自己的结论（M(X)→策略→M(M(X))）
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                meta_board.demo()
            return out(self, {"元棋盘": "L4 自指/反思层", "流程": buf.getvalue()})
        if q.path == "/api/flow":
            s, z, x = gi("shang"), gi("zhong"), gi("xia")
            seq = seq_of(s, z, x)
            bu = seq[6:] + seq[3:6] + seq[0:3]          # 自下而上：下+中+上
            nodes, final = dynamics.flow(bu)
            m = dynamics.metrics(nodes, bu, final)
            return out(self, {"构型": "".join(seq), "方向": "自下而上(底层→顶层)",
                              "势能流": nodes, "最终输出": final, "指标": m,
                              "自适配等级": level9.level9(tuple(seq))})
        if q.path == "/api/evolve":
            s, z, x = gi("shang"), gi("zhong"), gi("xia")
            idx = gi("idx", 0); newc = u.get("newc", ["T"])[0][:1].upper()
            seq = seq_of(s, z, x)
            seq2 = list(seq); seq2[idx] = newc
            def fb(st):
                bu = st[6:] + st[3:6] + st[0:3]
                nodes, final = dynamics.flow(bu)
                return nodes, final, dynamics.metrics(nodes, bu, final)
            n1, f1, m1 = fb(seq); n2, f2, m2 = fb(seq2)
            return out(self, {"构型": "".join(seq),
                              "扰动": f"第{idx}爻 {seq[idx]}→{newc} (原序, 上+中+下)",
                              "原": {"势能流": n1, "最终输出": f1, "指标": m1,
                                     "自适配等级": level9.level9(tuple(seq))},
                              "新": {"势能流": n2, "最终输出": f2, "指标": m2,
                                     "自适配等级": level9.level9(tuple(seq2))},
                              "输出变化": round(f2 - f1, 4),
                              "滞留变化": round(m2["累计滞留"] - m1["累计滞留"], 4)})
        return self._err("未知接口")

    def _err(self, msg):
        b = json.dumps({"error": msg}, ensure_ascii=False).encode("utf-8")
        self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        q = urllib.parse.urlparse(self.path)
        if q.path.startswith("/api/"):
            return self._api()
        # 首页
        f = os.path.join(ROOT, "index.html")
        if os.path.exists(f):
            b = open(f, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        else:
            self.send_response(404); self.end_headers()
            self.wfile.write(b"index.html not found")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"三元九维19683 大模型已启动")
    print(f"  请在浏览器打开： http://127.0.0.1:{port}/")
    print("  按 Ctrl+C 停止")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")

if __name__ == "__main__":
    main()
