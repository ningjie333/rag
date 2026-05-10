"""FAISS 向量存储客户端

替代 ChromaDB，解决 Python 3.14 编译问题。
FAISS 有预编译 wheel，安装简单。
"""
import json
import os
import structlog
from pathlib import Path
from typing import Optional

import numpy as np
import faiss

log = structlog.get_logger()

# 获取数据目录
from config import settings
DATA_DIR = Path(settings.DATA_DIR) if hasattr(settings, 'DATA_DIR') else Path(__file__).parent.parent / "data"


class FAISSVectorStore:
    """FAISS 向量存储，支持增删改查"""

    def __init__(self, name: str):
        self.name = name
        self.index_path = DATA_DIR / f"faiss_{name}"
        self.meta_path = self.index_path.with_suffix(".meta.json")
        self._index: Optional[faiss.Index] = None
        self._metadata: list[dict] = []
        self._load()

    def _load(self):
        """加载索引和元数据"""
        if self.index_path.exists():
            try:
                self._index = faiss.read_index(str(self.index_path))
                if self.meta_path.exists():
                    with open(self.meta_path, "r", encoding="utf-8") as f:
                        self._metadata = json.load(f)
                log.info("faiss_loaded", name=self.name, vectors=self._index.ntotal)
            except Exception as e:
                log.warning("faiss_load_failed", error=str(e))
                self._index = None
                self._metadata = []

    def _save(self):
        """保存索引和元数据"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if self._index is not None:
            faiss.write_index(self._index, str(self.index_path))
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self._metadata, f, ensure_ascii=False)

    def _ensure_index(self, dim: int):
        """确保索引已初始化"""
        if self._index is None:
            self._index = faiss.IndexFlatL2(dim)
            self._metadata = []

    def upsert(self, ids: list[str], vectors: list[list[float]] = None, metadatas: list[dict] = None, documents: list[str] = None):
        """
        插入或更新向量。

        Args:
            ids: 文档 ID 列表
            vectors: 向量列表（如果为空字符串表示无向量）
            metadatas: 元数据列表
            documents: 文档文本列表（从 metadata["text"] 提取或直接提供）
        """
        if not ids:
            return

        # 处理文档文本
        if documents is None and metadatas:
            documents = [m.get("text", "") for m in metadatas]

        # 处理向量
        if vectors and all(len(v) > 0 for v in vectors):
            dim = len(vectors[0])
            self._ensure_index(dim)
            vectors_arr = np.array(vectors, dtype=np.float32)
            self._index.add(vectors_arr)
        else:
            # 无向量时创建假向量（用于只存储 metadata）
            dim = 128  # 默认维度
            self._ensure_index(dim)
            dummy_vectors = np.zeros((len(ids), dim), dtype=np.float32)
            self._index.add(dummy_vectors)

        # 存储 metadata
        for i, (doc_id, meta, doc_text) in enumerate(zip(ids, metadatas or [], documents or [])):
            entry = {"id": doc_id}
            if meta:
                entry.update(meta)
            if doc_text:
                entry["text"] = doc_text
            self._metadata.append(entry)

        self._save()
        log.info("faiss_upsert", name=self.name, count=len(ids))

    def search(self, query_vector: list[float], top_k: int = 5, filter_meta: dict = None) -> list[dict]:
        """
        向量检索。

        Args:
            query_vector: 查询向量
            top_k: 返回数量
            filter_meta: 元数据过滤（暂未实现）

        Returns:
            [{id, metadata, distance}]
        """
        if self._index is None or self._index.ntotal == 0:
            return []

        query_arr = np.array([query_vector], dtype=np.float32)
        distances, indices = self._index.search(query_arr, top_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self._metadata):
                results.append({
                    "id": self._metadata[idx].get("id", ""),
                    "metadata": self._metadata[idx],
                    "distance": float(dist),
                })

        return results

    def query(self, query_texts: list[str], n_results: int = 5, where: dict = None,
              include: list[str] = None) -> dict:
        """
        兼容 ChromaDB 接口的查询方法。

        由于我们没有真实 embedding，使用简单文本匹配作为后备。
        在生产环境中应接入真实的 embedding 模型（如 BGE）。

        Args:
            query_texts: 查询文本列表
            n_results: 返回数量
            where: 元数据过滤条件
            include: 返回字段

        Returns:
            {ids, documents, metadatas, distances}
        """
        if not query_texts:
            return {"ids": [], "documents": [], "metadatas": [], "distances": []}

        query = query_texts[0].lower()

        # 获取所有 metadata
        all_items = self._metadata

        # where 过滤
        if where:
            filtered = []
            for item in all_items:
                match = True
                for k, v in where.items():
                    if item.get(k) != v:
                        match = False
                        break
                if match:
                    filtered.append(item)
            all_items = filtered

        # 简单文本匹配：计算 query 在 text 中出现的次数
        scored = []
        for item in all_items:
            text = item.get("text", "").lower()
            if not text:
                continue
            # 简单评分：query 词在 text 中出现次数
            score = sum(1 for word in query.split() if word in text)
            if score > 0:
                scored.append((item, score))

        # 按评分排序
        scored.sort(key=lambda x: x[1], reverse=True)

        # 取 top_k
        results = scored[:n_results]

        ids = [r[0].get("id", "") for r in results]
        documents = [r[0].get("text", "") for r in results]
        metadatas = [r[0] for r in results]
        # 分数作为 distance（越小越好，所以用 1/score）
        distances = [1.0 / r[1] if r[1] > 0 else 999.0 for r in results]

        # ChromaDB 格式：嵌套列表
        return {
            "ids": [ids],
            "documents": [documents],
            "metadatas": [metadatas],
            "distances": [distances],
        }

    def get(self, ids: list[str] = None, where: dict = None, include: list[str] = None) -> dict:
        """
        获取文档。

        Args:
            ids: 指定 ID 列表（None 表示全部）
            where: 元数据过滤条件
            include: 返回字段（documents, metadatas, distances）

        Returns:
            {ids, documents, metadatas, distances}
        """
        if self._index is None:
            return {"ids": [], "documents": [], "metadatas": [], "distances": []}

        # 简单实现：返回所有或指定的
        if ids:
            items = [m for m in self._metadata if m.get("id") in ids]
        else:
            items = self._metadata

        # where 过滤
        if where:
            filtered = []
            for item in items:
                match = True
                for k, v in where.items():
                    if item.get(k) != v:
                        match = False
                        break
                if match:
                    filtered.append(item)
            items = filtered

        return {
            "ids": [m.get("id", "") for m in items],
            "documents": [m.get("text", "") for m in items],
            "metadatas": [m for m in items],
            "distances": [0.0] * len(items),  # FAISS 不保存距离
        }

    def count(self) -> int:
        """返回向量数量"""
        if self._index is None:
            return 0
        return self._index.ntotal

    def delete(self, ids: list[str]):
        """删除向量（标记为删除，不实际删除）"""
        # FAISS 不支持高效删除，简单标记
        for mid in ids:
            for m in self._metadata:
                if m.get("id") == mid:
                    m["_deleted"] = True
        self._save()


# 全局存储
_stores: dict[str, FAISSVectorStore] = {}


def get_or_create_store(name: str) -> FAISSVectorStore:
    """获取或创建 FAISS store"""
    if name not in _stores:
        _stores[name] = FAISSVectorStore(name)
    return _stores[name]


def get_or_create_collection(name: str):
    """兼容 ChromaDB 接口"""
    return FAISSVectorStore(name)


def reset_client():
    """重置客户端（测试用）"""
    global _stores
    _stores = {}