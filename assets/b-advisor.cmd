@echo off
setlocal
set "ROOT=%~dp0"
set "BRIDGE=%ROOT%tools\ai-bridge.py"

if "%~1"=="" (
  py -3.10 "%BRIDGE%" --repo-root "%ROOT%." status
  exit /b %ERRORLEVEL%
)

set "FIRST=%~1"
if /I "%FIRST%"=="advise" goto pass
if /I "%FIRST%"=="implement" goto pass
if /I "%FIRST%"=="review" goto pass
if /I "%FIRST%"=="triage" goto pass
if /I "%FIRST%"=="status" goto pass
if /I "%FIRST%"=="sync" goto pass
if /I "%FIRST%"=="--dry-run" goto pass

py -3.10 "%BRIDGE%" --repo-root "%ROOT%." advise %*
exit /b %ERRORLEVEL%

:pass
py -3.10 "%BRIDGE%" --repo-root "%ROOT%." %*
exit /b %ERRORLEVEL%
