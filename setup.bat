@echo off
chcp 65001 >nul
echo.
echo ╔══════════════════════════════════════╗
echo ║  咨询侠 v2.6.0 — 一键安装          ║
echo ╚══════════════════════════════════════╝
echo.
echo 正在安装依赖（阿里云镜像）...
echo.

pip install mcp python-docx langgraph langchain-core langchain-deepseek ^
    -i https://mirrors.aliyun.com/pypi/simple/ ^
    --trusted-host mirrors.aliyun.com

echo.
echo ══════════════════════════════════════
if %ERRORLEVEL% EQU 0 (
    echo  ✅ 安装完成！
    echo.
    echo  交互模式：在 Claude Code 中输入 @咨询侠 开始使用
    echo  批量模式：python batch/run_batch.py 学生列表.csv
) else (
    echo  ❌ 安装失败，请检查网络连接后重试
    echo  或手动执行：pip install mcp python-docx langgraph langchain-core langchain-deepseek
)
echo ══════════════════════════════════════
echo.
pause
