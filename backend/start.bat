@echo off
echo Installing Python dependencies...
python -m pip install -r requirements.txt
echo.
echo Starting Photexx Backend Server...
python server.py
pause
