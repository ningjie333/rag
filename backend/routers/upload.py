"""POST /api/upload — PDF 上传 + 解析入库"""
import structlog
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from pathlib import Path

from models.schemas import UploadResponse
from vector_store.pdf_processor import process_pdf_to_chunks
from vector_store.chroma_client import get_or_create_collection
from config import settings

router = APIRouter()
log = structlog.get_logger()


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    book_title: str = Form(...),
):
    """
    上传 PDF/TXT，解析文本、分块，存入 ChromaDB。
    """
    log.info("upload_request", filename=file.filename, book_title=book_title)

    # 验证文件类型
    allowed_exts = {".pdf", ".txt", ".md"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    try:
        content = await file.read()

        # 保存到临时文件
        temp_dir = Path(settings.DATA_DIR) / "uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / file.filename

        with open(temp_path, "wb") as f:
            f.write(content)

        # 解析并分块
        if ext == ".pdf":
            chunks = process_pdf_to_chunks(temp_path, book_title)
        else:
            # TXT/MD 文件：直接分块
            from vector_store.pdf_processor import chunk_text
            text = content.decode("utf-8", errors="replace")
            chunk_texts = chunk_text(text)
            chunks = [
                {
                    "chunk_id": f"{Path(file.filename).stem}_c{i}",
                    "text": ct,
                    "source": str(temp_path),
                    "page": 1,
                    "chapter": "",
                    "book_title": book_title,
                    "chunk_index": i,
                }
                for i, ct in enumerate(chunk_texts)
                if len(ct.strip()) >= 20
            ]

        # 存入 ChromaDB
        if chunks:
            collection = get_or_create_collection(settings.COLLECTION_CHUNKS)
            ids = [c["chunk_id"] for c in chunks]
            docs = [c["text"] for c in chunks]
            metas = [
                {
                    "source": c["source"],
                    "page": c["page"],
                    "chapter": c["chapter"],
                    "book_title": c["book_title"],
                    "chunk_index": c["chunk_index"],
                }
                for c in chunks
            ]
            collection.upsert(ids=ids, documents=docs, metadatas=metas)
            log.info("chunks_stored", count=len(chunks), book_title=book_title)

        # 清理临时文件
        temp_path.unlink(missing_ok=True)

        return UploadResponse(
            success=True,
            chunks=len(chunks),
            message=f"文件 {file.filename} 已解析，共 {len(chunks)} 个文本块",
            book_title=book_title,
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error("upload_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")
