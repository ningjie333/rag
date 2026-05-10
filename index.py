"""
Vercel Serverless Function - FastAPI entrypoint
Minimal version for testing Vercel deployment
"""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "学科知识整合智能体 API", "status": "ok"}

@app.get("/health")
def health():
    return {"status": "healthy"}