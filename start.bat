@echo off
REM Multi-Agent RAG Local - 快速启动脚本
REM 版本: v0.4.5
REM 日期: 2026-06-17

echo ============================================
echo   Multi-Agent RAG Local v0.4.5
echo   快速启动脚本
echo ============================================
echo.

REM 检查conda环境
call conda activate rag-local 2>nul
if errorlevel 1 (
    echo [错误] 无法激活 rag-local 环境
    echo 请先运行: conda create -n rag-local python=3.11
    pause
    exit /b 1
)

echo [1/3] 激活 rag-local 环境... OK
echo.

REM 启动后端（新窗口）
echo [2/3] 启动后端服务器 (端口 8000)...
start "RAG Backend" cmd /k "conda activate rag-local && uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload && pause"

REM 等待后端启动
echo 等待后端初始化...
timeout /t 5 /nobreak >nul

echo.
echo [3/3] 启动前端开发服务器 (端口 5173)...
cd frontend
start "RAG Frontend" cmd /k "npm run dev && pause"

echo.
echo ============================================
echo   启动完成！
echo ============================================
echo.
echo 前端地址: http://localhost:5173/app
echo 后端API:  http://localhost:8000/docs
echo 健康检查: http://localhost:8000/health
echo.
echo 按任意键打开浏览器...
pause >nul

start http://localhost:5173/app

echo.
echo 提示: 关闭此窗口不会停止服务
echo       请分别关闭后端和前端窗口以停止服务
echo.
pause
