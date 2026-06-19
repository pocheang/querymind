#!/bin/bash
# Multi-Agent RAG Local - 快速启动脚本
# 版本: v0.4.5
# 日期: 2026-06-17

echo "============================================"
echo "  Multi-Agent RAG Local v0.4.5"
echo "  快速启动脚本"
echo "============================================"
echo ""

# 检查conda
if ! command -v conda &> /dev/null; then
    echo "[错误] 未找到 conda 命令"
    echo "请先安装 Anaconda 或 Miniconda"
    exit 1
fi

# 激活环境
echo "[1/3] 激活 rag-local 环境..."
eval "$(conda shell.bash hook)"
conda activate rag-local

if [ $? -ne 0 ]; then
    echo "[错误] 无法激活 rag-local 环境"
    echo "请先运行: conda create -n rag-local python=3.11"
    exit 1
fi

echo "      OK"
echo ""

# 启动后端（后台）
echo "[2/3] 启动后端服务器 (端口 8000)..."
uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "      后端 PID: $BACKEND_PID"

# 等待后端启动
echo "      等待后端初始化..."
sleep 5

# 检查后端是否启动成功
if ps -p $BACKEND_PID > /dev/null; then
    echo "      OK"
else
    echo "[错误] 后端启动失败，请查看 logs/backend.log"
    exit 1
fi

echo ""

# 启动前端
echo "[3/3] 启动前端开发服务器 (端口 5173)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
echo "      前端 PID: $FRONTEND_PID"

echo ""
echo "============================================"
echo "  启动完成！"
echo "============================================"
echo ""
echo "前端地址: http://localhost:5173/app"
echo "后端API:  http://localhost:8000/docs"
echo "健康检查: http://localhost:8000/health"
echo ""
echo "PID 文件已保存，停止服务请运行: ./stop.sh"
echo ""

# 保存PID
echo $BACKEND_PID > .backend.pid
echo $FRONTEND_PID > .frontend.pid

# 等待用户输入
echo "按 Ctrl+C 停止服务"
wait
