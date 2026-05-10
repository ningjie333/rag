"""POST /api/upload — 多格式文件上传 + 解析入库"""
import structlog
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from pathlib import Path

from models.schemas import UploadResponse
from vector_store.file_processor import process_file_to_chunks, SUPPORTED_EXTS
from vector_store.chroma_client import get_or_create_collection
from config import settings

router = APIRouter()
log = structlog.get_logger()


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    book_title: str = Form(...),
):
    """
    上传文件，解析文本、分块，存入 ChromaDB。

    支持格式：PDF, TXT, MD, DOCX, DOC, XLSX, XLS, CSV, JSON, YAML
    """
    log.info("upload_request", filename=file.filename, book_title=book_title)

    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}。支持: {', '.join(sorted(SUPPORTED_EXTS))}",
        )

    try:
        content = await file.read()

        if len(content) == 0:
            raise HTTPException(status_code=400, detail="文件为空")

        temp_dir = Path(settings.DATA_DIR) / "uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / file.filename

        with open(temp_path, "wb") as f:
            f.write(content)

        try:
            chunks = process_file_to_chunks(temp_path, book_title, ext)
        except Exception as e:
            log.error("parse_failed", error=str(e), filename=file.filename)
            raise HTTPException(status_code=422, detail=f"文件解析失败: {e}")
        finally:
            temp_path.unlink(missing_ok=True)

        if not chunks:
            raise HTTPException(status_code=422, detail="文件解析后无有效文本内容")

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
