@echo off
setlocal enabledelayedexpansion

echo ============================================
echo  Batch runner for tps2toj.py
echo  Runs from pA to pX as specified.
echo ============================================
echo.

:: Ask for user inputs
set /p input=Enter input folder path: 
set /p output=Enter output folder path: 
set /p start=Enter start letter (e.g., A): 
set /p end=Enter end letter (e.g., I): 

:: Remove any quotes
set input=%input:"=%
set output=%output:"=%

:: Get only the first letter and uppercase it
set start=%start:~0,1%
set end=%end:~0,1%

:: Find index of start and end letters
set idx=0
set start_idx=
set end_idx=
for %%L in (A B C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
  set /a idx+=1
  if /i "%%L"=="%start%" set start_idx=!idx!
  if /i "%%L"=="%end%" set end_idx=!idx!
)

if not defined start_idx (
  echo Invalid start letter: %start%
  goto :end
)
if not defined end_idx (
  echo Invalid end letter: %end%
  goto :end
)

:: Swap if needed
if %start_idx% GTR %end_idx% (
  set tmp=%start_idx%
  set start_idx=%end_idx%
  set end_idx=%tmp%
)

:: Run python for each problem folder
set idx=0
for %%L in (A B C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
  set /a idx+=1
  if !idx! GEQ %start_idx% if !idx! LEQ %end_idx% (
    echo.
    echo ===== Running p%%L =====
    echo python tps2toj.py "%input%\p%%L" "%output%\p%%L"
    python tps2toj.py "%input%\p%%L" "%output%\p%%L"
    if ERRORLEVEL 1 (
      echo [Warning] p%%L returned non-zero exit code: !ERRORLEVEL!
    )
  )
)

echo.
echo All tasks completed!
:end
pause
