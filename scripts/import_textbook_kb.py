#!/usr/bin/env python3
"""
导入医学教科书 chunks.pkl 到 FAISS 向量库

用法:
    python scripts/import_textbook_kb.py
"""
import pickle
import sys
from pathlib import Path

# 添加 backend 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from vector_store.faiss_client import get_or_create_collection
from config import settings

KB_DIR = Path("C:/Users/ZhuanZ（无密码）/Desktop/教科书/medical_kb")
CHUNK_SIZE = 600
CHUNK_OVERLAP = 80


def load_medical_kb():
    """加载已有的医学知识库"""
    chunks_path = KB_DIR / "chunks.pkl"
    if not chunks_path.exists():
        print(f"错误: {chunks_path} 不存在")
        print("请先运行 教科书/process_pdfs.py")
        return []

    with open(chunks_path, "rb") as f:
        chunks = pickle.load(f)

    print(f"加载了 {len(chunks)} 个文本块")
    return chunks


def import_chunks_to_faiss(chunks: list[dict]):
    """将 chunks 导入 FAISS 向量库"""
    collection = get_or_create_collection(settings.COLLECTION_CHUNKS)

    # 批量导入
    ids = []
    vectors = []  # 暂时用零向量（因为原来没有向量）
    metadatas = []

    for chunk in chunks:
        meta = chunk.get("metadata", {})
        ids.append(chunk["id"])
        vectors.append([0.0] * 128)  # 假向量

        metadatas.append({
            "text": chunk["text"][:500],  # 截断保存
            "source": meta.get("book", ""),
            "page": meta.get("page_start", 0),
            "chapter": meta.get("chapter", ""),
            "book_title": meta.get("book", ""),
            "chunk_index": meta.get("chunk_index", 0),
        })

    collection.upsert(ids, vectors, metadatas)
    print(f"已导入 {len(ids)} 个 chunks 到 FAISS")

    return len(ids)


def main():
    print("=" * 50)
    print("导入医学教科书知识库到 FAISS")
    print("=" * 50)

    chunks = load_medical_kb()
    if not chunks:
        return

    # 按书名统计
    book_stats = {}
    for c in chunks:
        book = c.get("metadata", {}).get("book", "未知")
        book_stats[book] = book_stats.get(book, 0) + 1

    print("\n各书籍文本块数量:")
    for book, count in sorted(book_stats.items()):
        print(f"  {book}: {count}")

    print("\n开始导入...")
    total = import_chunks_to_faiss(chunks)
    print(f"\n完成！共导入 {total} 个文本块")
    print(f"数据位置: backend/data/")


if __name__ == "__main__":
    main()