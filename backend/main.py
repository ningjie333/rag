"""FastAPI 应用入口"""
import logging
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from routers import upload, query, kg, chat, books, report, feedback

structlog.configure(
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
)
log = structlog.get_logger()

app = FastAPI(
    title="学科知识整合 API",
    description="AI 医学知识树洞 — 知识图谱 + RAG 问答",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": f"服务器内部错误: {str(exc)}"},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "backend"}


# 注册路由
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(query.router, prefix="/api", tags=["query"])
app.include_router(kg.router, prefix="/api", tags=["knowledge-graph"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(books.router, prefix="/api", tags=["books"])
app.include_router(report.router, prefix="/api", tags=["report"])
app.include_router(feedback.router, prefix="/api", tags=["feedback"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
