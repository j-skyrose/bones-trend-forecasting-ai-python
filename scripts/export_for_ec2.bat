@echo off
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
python %PROJECTDIR%\managers\databaseManager.py -f buildGIDBCopy > dbpath.txt
set /p DBPATH=<dbpath.txt
del dbpath.txt
echo %DBPATH%
move %DBPATH% %EXPORTDIR%\data\sp2Database.db

echo "Copying rest of python files"
copy %PROJECTDIR%\config.ini %EXPORTDIR%
copy %PROJECTDIR%\globalConfig.py %EXPORTDIR%
robocopy %PROJECTDIR%\constants %EXPORTDIR%\constants /e
robocopy %PROJECTDIR%\interfaces %EXPORTDIR%\interfaces /e
robocopy %PROJECTDIR%\managers %EXPORTDIR%\managers /e
robocopy %PROJECTDIR%\structures %EXPORTDIR%\structures /e
robocopy %PROJECTDIR%\utils %EXPORTDIR%\utils /e

echo "Removing tensorflow dependent code"
powershell -Command "(gc %PROJECTDIR%\globalConfig.py) -replace 'TESTING = True', 'pass' | Out-File -encoding ASCII %PROJECTDIR%\globalConfig.py"
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