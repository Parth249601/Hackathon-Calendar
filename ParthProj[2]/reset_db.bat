@echo off
echo Stopping any running Flask server...
taskkill /f /im python.exe 2>nul

echo Looking for SQLite database files...
dir /s /b *.db

echo Deleting database files...
del /f /q users.db 2>nul
del /f /q instance\users.db 2>nul
del /f /q .\instance\users.db 2>nul
del /f /q %CD%\instance\users.db 2>nul

echo Starting Flask app with new schema...
python app.py

echo Done! 