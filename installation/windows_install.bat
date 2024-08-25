@echo off
setlocal enabledelayedexpansion

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Please install Python and try again.
    pause
    exit /b 1
)

:: Create a virtual environment
python -m venv clockwork_env
call clockwork_env\Scripts\activate.bat

:: Install the package
pip install -e .

:: Create the clockwork.bat file
echo @echo off > %USERPROFILE%\clockwork.bat
echo call %cd%\clockwork_env\Scripts\activate.bat >> %USERPROFILE%\clockwork.bat
echo python -m clockwork %%* >> %USERPROFILE%\clockwork.bat

:: Add the user's home directory to PATH if it's not already there
echo !PATH! | find /i "%USERPROFILE%" >nul
if %errorlevel% neq 0 (
    setx PATH "%PATH%;%USERPROFILE%"
    echo Added %USERPROFILE% to PATH. Please restart your command prompt after installation.
)

:: Create alias batch files
for %%C in (clockin clockout clocklog clocksum clockvis clockcsv) do (
    echo @echo off > %USERPROFILE%\%%C.bat
    echo clockwork %%C %%* >> %USERPROFILE%\%%C.bat
)

echo Installation complete! You can now use 'clockwork' and its commands from any command prompt.
echo Please restart your command prompt to use the new commands.
pause