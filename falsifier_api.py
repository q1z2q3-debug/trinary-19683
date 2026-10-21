#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TNE-Falsifier 标准 HTTP 端点（falsifier_api.py）

把三元九维证伪器暴露为 HTTP 服务，任何 LLM / Agent / 应用均可通过
POST /falsify 调用它作为确定性校验层。纯标准库，无第三方依赖。

请求：POST /falsify
      {"question":"该指数下周会涨吗？","evidence":{"放量下跌":true}}
响应：{ "refuted":true/false, "hit_type":"full|partial", "migrated_to":"DOWN'",
        "confidence_before":.., "confidence_after":.., "final_assertion":"..",
        "reason":"..", "mode":"real|simulator", "neg_lib_size":.. }

运行：python3 falsifier_api.py [端口=8787]
测试：curl -s -X POST localhost:8787/falsify -H 'Content-Type: application/json' \
        -d '{"question":"该指数下周会涨吗？","evidence":{"放量下跌":true}}'
"""
from __future__ import annotations
import sys, json
from http.server import BaseHTTPRequestHandler, HTTPServer
from tne_falsifier_llm import run_falsified_qa


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()
    def do_POST(self):
        if self.path.rstrip("/") != "/falsify":
            self.send_response(404); self.end_headers(); return
        try:
            ln = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(ln) or b"{}")
            audit = run_falsified_qa(body.get("question", ""),
                                     body.get("evidence", {}),
                                     body.get("projection"))
            payload = json.dumps(audit, ensure_ascii=False)
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers(); self.wfile.write(payload.encode())
        except Exception as e:
            err = json.dumps({"error": str(e)}, ensure_ascii=False)
            self.send_response(500); self._cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers(); self.wfile.write(err.encode())
    def log_message(self, *a):  # 静默
        pass


def main(port: int = 8787):
    srv = HTTPServer(("0.0.0.0", port), Handler)
    print(f"TNE-Falsifier 端点已启动: POST http://localhost:{port}/falsify")
    print("接入模式:", "simulator(无LLM_API_KEY回退)" )
    srv.serve_forever()


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8787)
