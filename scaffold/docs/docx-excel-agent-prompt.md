# DOCX/Excel 支持 Agent 任务提示词

## 任务目标

扩展后端 `routers/upload.py`，新增 `.docx` 和 `.xlsx` 文件格式解析支持。

## 技术背景

- 现有上传接口支持：PDF、TXT、MD
- 后端已有 `vector_store/pdf_processor.py`（PyMuPDF）
- Python 库选择：
  - `python-docx` — 解析 .docx
  - `openpyxl` — 解析 .xlsx（Excel）

## 交付物

修改 `backend/vector_store/pdf_processor.py`，添加：

```python
def process_docx_to_chunks(file_path: Path, book_title: str) -> list[dict]:
    """解析 .docx 文件，返回分块列表"""

def process_xlsx_to_chunks(file_path: Path, book_title: str) -> list[dict]:
    """解析 .xlsx 文件，返回分块列表（每个 sheet + 行/单元格为一个 chunk）"""
```

然后修改 `routers/upload.py` 的 `allowed_exts`：

```python
allowed_exts = {".pdf", ".txt", ".md", ".docx", ".xlsx"}
```

并添加对应的处理分支。

## 错误处理

- 文件损坏 → 返回 400 错误并说明
- 空文件 → 返回 400 "文件为空"
- 不支持的格式（虽然已校验）→ 400

## 验收标准

1. `curl -X POST http://localhost:3002/api/upload -F "file=@test.docx" -F "book_title=测试"` 不报错
2. 能返回 `{"success": true, "chunks": N}`（N > 0）
3. xlsx 文件同样处理（按 sheet 分割）

## 禁止事项

- ❌ 不改 API 契约（接口格式不变）
- ❌ 不做 .doc 文件支持（已废弃格式）
- ❌ 不写测试

## 开始

修改 `backend/vector_store/pdf_processor.py`，添加 `process_docx_to_chunks` 和 `process_xlsx_to_chunks` 函数。然后修改 `routers/upload.py` 中的 allowed_exts 和处理逻辑。完成后在 task-board.md 记录完成状态。