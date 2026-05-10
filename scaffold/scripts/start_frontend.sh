#!/bin/bash

echo "===== [1/3] 检查 node 是否存在 ====="
if ! command -v node &> /dev/null; then
    echo "错误：未找到 node，请先安装 Node.js"
    exit 1
fi
echo "node 已找到：$(node --version)"

echo "===== [2/3] 检查 node_modules 是否存在 ====="
if [ ! -d node_modules ]; then
    echo "node_modules 不存在，执行 npm install..."
    npm install
    if [ $? -ne 0 ]; then
        echo "错误：npm install 失败"
        exit 1
    fi
    echo "依赖安装完成"
else
    echo "node_modules 已存在，跳过"
fi

echo "===== [3/3] 启动 Vite 开发服务器 ====="
npm run dev
