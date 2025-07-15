@echo off
echo Running Duplicate Prevention Monitor...
cd /d "C:\work\aggregator-menu-scraper\test-tools"
"C:/Users/mbouklas/.pyenv/pyenv-win/versions/3.12.7/python.exe" monitor_duplicates.py
pause
