#!/bin/bash

echo "===== [1/4] 检查 python3 是否存在 ====="
if ! command -v python3 &> /dev/null; then
    echo "错误：未找到 python3，请先安装 Python 3"
    exit 1
fi
echo "python3 已找到：$(python3 --version)"

echo "===== [2/4] 检查 backend/.env 是否存在 ====="
if [ ! -f backend/.env ]; then
    echo "backend/.env 不存在，从 .env.example 复制..."
    if [ -f .env.example ]; then
        cp .env.example backend/.env
        echo "已复制 .env.example -> backend/.env"
    else
        echo "警告：.env.example 不存在，跳过复制"
    fi
else
    echo "backend/.env 已存在，跳过"
fi

echo "===== [3/4] 安装后端依赖 ====="
pip install -r backend/requirements.txt

echo "===== [4/4] 启动 FastAPI (uvicorn) ====="
cd backend
uvicorn main:app --host 0.0.0.0 --port 3002 --reload
