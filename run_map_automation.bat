@echo off
rem MapAction map automation: double-click this file to build the maps.
rem It runs map_automation_pro.py (in this folder) with ArcGIS Pro's Python.
rem ArcGIS Pro must be installed and signed in. Answer the questions in this
rem window, pressing Enter after each one.
setlocal

rem Find ArcGIS Pro (all-users install, then a per-user install).
set "PRODIR="
for /f "tokens=2,*" %%a in ('reg query "HKLM\SOFTWARE\ESRI\ArcGISPro" /v InstallDir 2^>nul ^| find "InstallDir"') do set "PRODIR=%%b"
if not defined PRODIR for /f "tokens=2,*" %%a in ('reg query "HKCU\SOFTWARE\ESRI\ArcGISPro" /v InstallDir 2^>nul ^| find "InstallDir"') do set "PRODIR=%%b"
if not defined PRODIR set "PRODIR=C:\Program Files\ArcGIS\Pro\"
if not "%PRODIR:~-1%"=="\" set "PRODIR=%PRODIR%\"
set "PROPY=%PRODIR%bin\Python\Scripts\propy.bat"

if not exist "%PROPY%" (
    echo ArcGIS Pro's Python was not found at:
    echo   %PROPY%
    echo Is ArcGIS Pro installed on this computer?
    echo.
    pause
    exit /b 1
)

cd /d "%~dp0"
call "%PROPY%" "%~dp0map_automation_pro.py" %*

echo.
echo Finished. Press any key to close this window.
pause >nul
