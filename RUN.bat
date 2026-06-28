@echo off
title MARKYELLS
cd /d "%~dp0"

set PYW=C:\Users\ASPERA\AppData\Local\Programs\Python\Python311\pythonw.exe
if not exist "%PYW%" set PYW=pythonw

start "" "%PYW%" markyells_auto.py
exit /b 0