#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拉取三元九维19683全量知识库（数据外置，放 HuggingFace，不入 git 包）。

用法：
    python3 scripts/download_data.py            # 下载到 知识库/

说明：本脚本从 HuggingFace 仓库拉取「规范校正版」全集 JSON 到本地知识库。
未上传前，请把 HF_REPO 换成你的数据集仓库 ID（如 q1z2q3/trinary-19683-data）。
"""
import json
import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB = os.path.join(ROOT, "知识库")

# 目标：规范校正版全集（引擎数据源）
TARGET = os.path.join(KB, "三元九维19683_全集_规范校正版.json")
# HuggingFace 仓库（把下两行换成你的仓库与文件名）
HF_REPO = "q1z2q3/trinary-19683-data"          # TODO: 改为你的 HF 仓库
HF_FILE = "三元九维19683_全集_规范校正版.json"


def main():
    os.makedirs(KB, exist_ok=True)
    if os.path.exists(TARGET):
        size = os.path.getsize(TARGET) / 1024 / 1024
        print(f"已存在：{TARGET}（{size:.1f} MB）")
        return
    url = f"https://huggingface.co/datasets/{HF_REPO}/resolve/main/{HF_FILE}"
    print(f"下载：{url}")
    urllib.request.urlretrieve(url, TARGET)
    size = os.path.getsize(TARGET) / 1024 / 1024
    print(f"完成：{TARGET}（{size:.1f} MB）")


if __name__ == "__main__":
    main()
