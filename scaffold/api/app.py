"""
Vercel Serverless Function - FastAPI entrypoint
"""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "学科知识整合智能体 API"}

handler = app