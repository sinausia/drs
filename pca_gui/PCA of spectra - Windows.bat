@echo off
rem Double-click to open the "PCA of spectra" window (Windows).
rem Finds a Python installation that has the required packages and starts
rem run_gui.py from this folder. Keep this file next to run_gui.py.
rem If the window doesn't appear, see %LOCALAPPDATA%\PCA of spectra.log
setlocal
set "APP_NAME=PCA of spectra"
set "MODULES=numpy pandas matplotlib tkinter"
cd /d "%~dp0"

rem ---- Find Python: conda installs, python.org installs, the py launcher, the PATH ----
set "CHECK=import importlib.util as u, sys; sys.exit(not all(u.find_spec(m) for m in sys.argv[1:]))"
set "PYCMD="
set "PYW="
set "FOUND_ANY="
call :try "%USERPROFILE%\anaconda3\python.exe"
call :try "%USERPROFILE%\miniconda3\python.exe"
call :try "%USERPROFILE%\miniforge3\python.exe"
call :try "%LOCALAPPDATA%\anaconda3\python.exe"
call :try "%LOCALAPPDATA%\miniconda3\python.exe"
call :try "%ProgramData%\anaconda3\python.exe"
call :try "%ProgramData%\miniconda3\python.exe"
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do call :try "%%D\python.exe"
for /d %%D in ("%LOCALAPPDATA%\Python\pythoncore-3*") do call :try "%%D\python.exe"
for /d %%D in ("%ProgramFiles%\Python3*") do call :try "%%D\python.exe"
if not defined PYCMD call :try_py_launcher
if not defined PYCMD for /f "delims=" %%P in ('where python 2^>nul') do call :try "%%P"

if not defined PYCMD goto not_found

rem pythonw = no console window; run_gui.py writes errors to the log file instead
start "" %PYW% "%~dp0run_gui.py"
exit /b 0

:not_found
echo.
echo %APP_NAME% could not start.
echo.
if defined FOUND_ANY (
    echo Python is installed, but it is missing some of these packages: %MODULES%
    echo.
    echo  - With internet:    open a terminal and run   py -m pip install numpy pandas matplotlib
    echo  - Without internet: run "install_offline - Windows.bat" from the
    echo                      offline_install_windows folder ^(see its README.md^)
) else (
    echo No Python installation was found. Install Python 3.11 - 3.14 ^(64-bit^) from
    echo python.org, then install the packages as described in README.md.
)
echo.
pause
exit /b 1


rem ---- :try <path to python.exe> : use it if it runs and has the packages ----
:try
if defined PYCMD exit /b 0
if not exist "%~1" exit /b 0
"%~1" -c "pass" >nul 2>&1 || exit /b 0
set "FOUND_ANY=1"
"%~1" -c "%CHECK%" %MODULES% >nul 2>&1 || exit /b 0
set PYCMD="%~1"
set PYW="%~1"
if exist "%~dp1pythonw.exe" set PYW="%~dp1pythonw.exe"
exit /b 0

rem ---- the "py" launcher installed by python.org ----
:try_py_launcher
where py >nul 2>&1 || exit /b 0
py -3 -c "pass" >nul 2>&1 || exit /b 0
set "FOUND_ANY=1"
py -3 -c "%CHECK%" %MODULES% >nul 2>&1 || exit /b 0
set "PYCMD=py -3"
set "PYW=pyw -3"
exit /b 0
