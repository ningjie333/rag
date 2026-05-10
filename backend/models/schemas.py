"""Pydantic 模型定义"""
from pydantic import BaseModel
from typing import Optional


class UploadResponse(BaseModel):
    success: bool
    chunks: int
    message: str
    book_title: str


class Citation(BaseModel):
    chunk_id: str
    text: str
    source: str
    page: int
    score: float


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    graph_context: dict


class KGNode(BaseModel):
    id: str
    label: str
    type: str  # concept, fact, definition
    description: str
    source: str


class KGEdge(BaseModel):
    from_node: str
    to_node: str
    relation_type: str  # prerequisite, contains, associate
    weight: float


class GraphResponse(BaseModel):
    nodes: list[KGNode]
    edges: list[KGEdge]
    total_nodes: int
    total_edges: int


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatContext(BaseModel):
    book_titles: list[str] = []


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    context: ChatContext = ChatContext()


class ChatResponse(BaseModel):
    reply: str
    citations: list[Citation]
    graph_snapshot: dict


class BookInfo(BaseModel):
    title: str
    chunk_count: int
    created_at: str


class BooksResponse(BaseModel):
    books: list[BookInfo]


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
