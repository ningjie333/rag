"""PDF 解析 + 文本分块"""
import re
from pathlib import Path
from typing import Iterator

import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings


def extract_text_from_pdf(pdf_path: str | Path) -> Iterator[dict]:
    """
    从 PDF 提取文本，逐页返回。

    Yields:
        dict: {page: int, text: str, source: str}
    """
    doc = pymupdf.open(str(pdf_path))
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            yield {
                "page": page_num + 1,
                "text": text.strip(),
                "source": str(pdf_path),
            }
    doc.close()


def chunk_text(text: str) -> list[str]:
    """
    将文本分块。

    Args:
        text: 原始文本
    Returns:
        chunks: 分块后的文本列表
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],
    )
    return splitter.split_text(text)


def process_pdf_to_chunks(pdf_path: str | Path, book_title: str) -> list[dict]:
    """
    处理 PDF → 分块，返回 chunk 列表（用于存入 ChromaDB）。

    Returns:
        list[dict]: [{chunk_id, text, source, page, chapter, book_title, chunk_index}]
    """
    chunks = []
    chunk_index = 0

    for page_data in extract_text_from_pdf(pdf_path):
        page_chunks = chunk_text(page_data["text"])
        for chunk_text_piece in page_chunks:
            if len(chunk_text_piece.strip()) < 20:
                continue
            chunks.append({
                "chunk_id": f"{Path(pdf_path).stem}_p{page_data['page']}_c{chunk_index}",
                "text": chunk_text_piece,
                "source": page_data["source"],
                "page": page_data["page"],
                "chapter": "",  # TODO: 后续从目录页提取
                "book_title": book_title,
                "chunk_index": chunk_index,
            })
            chunk_index += 1

    return chunks
