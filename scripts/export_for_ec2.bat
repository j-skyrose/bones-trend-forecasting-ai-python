@echo off
@REM %~dp0 = (this) batch file directory
set MYPATH=%~dp0
set PROJECTDIR=%MYPATH%\..
set EXPORTDIR=%MYPATH%\sp-export

echo "Setting up EXPORT folder"
rmdir /S /Q %EXPORTDIR%
mkdir %EXPORTDIR%
mkdir %EXPORTDIR%\.vscode
@REM mkdir %EXPORTDIR%\constants
mkdir %EXPORTDIR%\data
@REM mkdir %EXPORTDIR%\interfaces
@REM mkdir %EXPORTDIR%\managers
@REM mkdir %EXPORTDIR%\structures
@REM mkdir %EXPORTDIR%\utils

echo "Exporting DB"
@REM can be run while other process has DB open
python %PROJECTDIR%/managers/databaseManager.py -f buildGIDBCopy verbose=0.5 > dbpath.txt
echo %ERRORLEVEL%
if %ERRORLEVEL% NEQ 0 exit /B
set /p DBPATH=<dbpath.txt
del dbpath.txt
echo %DBPATH%
move %DBPATH% %EXPORTDIR%\data\sp2Database.db

echo "Copying rest of python files"
copy %PROJECTDIR%\config.ini %EXPORTDIR%
copy %PROJECTDIR%\globalConfig.py %EXPORTDIR%
robocopy %PROJECTDIR%\constants %EXPORTDIR%\constants /e /xf *.pyc
robocopy %PROJECTDIR%\interfaces %EXPORTDIR%\interfaces /e /xf *.pyc
robocopy %PROJECTDIR%\managers %EXPORTDIR%\managers /e /xd *dynamicallyLoadedFactories /xf *.pyc
robocopy %PROJECTDIR%\structures %EXPORTDIR%\structures /e /xf *.pyc
robocopy %PROJECTDIR%\utils %EXPORTDIR%\utils /e /xf *.pyc

@REM tensorflow dependency not installed on EC2 agents, so removal of any references will allow the necessary things to run
echo "Removing tensorflow dependent code"
powershell -Command "(gc %EXPORTDIR%\globalConfig.py) -replace 'TESTING = True', 'pass' | Out-File -encoding ASCII %EXPORTDIR%\globalConfig.py"
del %EXPORTDIR%\interfaces\hyperParameterAnalyzer.py
del %EXPORTDIR%\interfaces\predictor.py
del %EXPORTDIR%\interfaces\trainer.py
del %EXPORTDIR%\managers\dataManager.py
del %EXPORTDIR%\managers\networkAnalysisManager.py
del %EXPORTDIR%\structures\EvaluationDataHandler.py
del %EXPORTDIR%\structures\neuralNetworkInstance.py
rmdir /S /Q %EXPORTDIR%\structures\callbacks

echo "Zipping"
tar -cf %MYPATH%\sp-export.tar -C %EXPORTDIR% .

echo "Cleaning up"
rmdir /S /Q %EXPORTDIR%

echo "Done"