@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ====================================
echo  城投债采集 A+B 交替模式
echo  Ctrl+C 随时停止（自动保存进度）
echo ====================================
python run_ab.py --batch=5
pause
