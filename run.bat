@echo off
REM 정신질환 퇴원환자 Two-Track Care Coordination 대시보드 실행
REM 더블클릭하면 Anaconda Python으로 Streamlit 앱을 띄웁니다 (브라우저 자동 열림).
cd /d "%~dp0"
"C:\Users\tilti\anaconda3\python.exe" -m streamlit run app.py
pause
