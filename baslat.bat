@echo off
REM ===================================================================
REM Cebimde - Windows baslatici. CIFT TIKLA, baska bir sey yapma.
REM
REM NEDEN VAR: "python sunucu.py" komutu Windows'ta terminal acmayi,
REM dogru klasorde olmayi ve Python'un PATH'te olmasini gerektiriyor.
REM Ucu de yanlis gidebiliyor ve ucunun de hata mesaji anlasilmaz.
REM Bu dosya ucunu de kendisi kontrol ediyor ve NE YAPILACAGINI yaziyor.
REM
REM PENCERE KAPANMIYOR (pause): hata verip aninda kapanan bir pencere,
REM hicbir sey soylemeyen bir pencereyle aynidir.
REM ===================================================================
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo   Cebimde - yerel calistirma
echo   ---------------------------
echo.

REM --- 1. Dogru klasorde miyiz ---
if not exist "sunucu.py" (
  echo   HATA: sunucu.py bulunamadi.
  echo   Bu dosya deponun KOK klasorunde olmali ^(app\, veritabani\ ile yan yana^).
  echo.
  pause
  exit /b 1
)
if not exist "app\index.html" (
  echo   HATA: app\index.html yok. Depo eksik indirilmis olabilir.
  echo   ZIP indirdiysen ZIP'i actigindan emin ol.
  echo.
  pause
  exit /b 1
)

REM --- 2. Python var mi ---
REM "py" Windows'un resmi baslaticisi; yoksa "python" denenecek.
set PY=
where py >nul 2>nul && set PY=py
if "%PY%"=="" ( where python >nul 2>nul && set PY=python )
if "%PY%"=="" (
  echo   HATA: Python bulunamadi.
  echo.
  echo   Kur: https://www.python.org/downloads/
  echo   Kurulum ekraninda "Add python.exe to PATH" kutusunu ISARETLE.
  echo   Sonra bu dosyayi tekrar cift tikla.
  echo.
  pause
  exit /b 1
)

REM --- 3. Baslat ve tarayiciyi ac ---
echo   Sunucu baslatiliyor... ^(kapatmak icin bu pencerede Ctrl+C^)
echo   Adres: http://localhost:8123
echo.
start "" http://localhost:8123
%PY% sunucu.py --yerel

echo.
echo   Sunucu durdu.
pause
