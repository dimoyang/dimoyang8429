@echo off
echo Creating MediTour Flutter project structure...

REM 创建lib下的目录
mkdir lib\app 2>nul
mkdir lib\core 2>nul
mkdir lib\core\constants 2>nul
mkdir lib\core\utils 2>nul
mkdir lib\core\services 2>nul
mkdir lib\data 2>nul
mkdir lib\data\models 2>nul
mkdir lib\data\repositories 2>nul
mkdir lib\data\datasources 2>nul
mkdir lib\business 2>nul
mkdir lib\business\providers 2>nul
mkdir lib\business\usecases 2>nul
mkdir lib\presentation 2>nul
mkdir lib\presentation\widgets 2>nul
mkdir lib\presentation\widgets\common 2>nul
mkdir lib\presentation\widgets\medical 2>nul
mkdir lib\presentation\widgets\booking 2>nul
mkdir lib\presentation\screens 2>nul
mkdir lib\presentation\screens\auth 2>nul
mkdir lib\presentation\screens\main 2>nul
mkdir lib\presentation\screens\medical 2>nul
mkdir lib\presentation\screens\booking 2>nul
mkdir lib\presentation\screens\profile 2>nul
mkdir lib\presentation\screens\guides 2>nul
mkdir lib\presentation\themes 2>nul

REM 创建测试目录
mkdir test 2>nul
mkdir test\unit 2>nul
mkdir test\widget 2>nul
mkdir test\integration 2>nul

REM 创建基础Dart文件
echo // Application entry point > lib\main.dart
echo // App configuration > lib\app\app.dart
echo // Theme configuration > lib\presentation\themes\app_theme.dart

echo.
echo Directory structure created successfully!
echo.
pause