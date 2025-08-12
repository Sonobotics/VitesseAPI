@echo off
setlocal EnableExtensions
net session >nul 2>&1
if %errorlevel% NEQ 0 (
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)
set "DLL=%~dp0windows_FTDI\ftd2xx.dll"
set "DEST=%WINDIR%\System32"
if not exist "%DLL%" exit /b 1
copy /Y "%DLL%" "%DEST%" >nul
endlocal