#!/usr/bin/env python3
"""初始化向量库脚本"""
import sys
from pathlib import Path

# 添加 backend 到 path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from vector_store.chroma_client import get_client, get_or_create_collection
from config import settings
import structlog

log = structlog.get_logger()


def main():
    print("=== 向量库初始化 ===")
    print(f"存储目录: {settings.CHROMA_PERSIST_DIR}")

    client = get_client()

    # 创建 collections
    for name in [settings.COLLECTION_CHUNKS, settings.COLLECTION_KG]:
        col = client.get_or_create_collection(name=name)
        print(f"  ✓ Collection '{name}' 就绪 (当前记录数: {col.count()})")

    print("\n初始化完成！")
    print(f"上传 PDF 后调用 POST /api/upload 即可自动分块入库。")


if __name__ == "__main__":
    main()
