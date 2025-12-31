@echo off
REM Launch the packing optimizer from this script's directory
cd /d "%~dp0"

setlocal

set "PYTHONPATH=%CD%\src;%PYTHONPATH%"

REM Try to locate a usable Python interpreter.
for %%P in (python python3 py) do (
    where %%P >nul 2>nul && (
        set "PYTHON_CMD=%%P"
        goto :found_python
    )
)

echo.
echo Could not find Python on PATH.
echo Please install Python 3 and make sure it is available in the PATH environment variable.
goto :end

:found_python
if /I "%PYTHON_CMD%"=="py" (
    %PYTHON_CMD% -3 -m packing_app 2>nul || %PYTHON_CMD% -3 main.py
) else (
    %PYTHON_CMD% -m packing_app 2>nul || %PYTHON_CMD% main.py
)

:end
pause
endlocal
