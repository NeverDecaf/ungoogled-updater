# ungoogled-updater
Script for windows to keep ungoogled-chromium up to date.
Will install/update chromium in %PROGRAMDATA%\Ungoogled Chromium\
binaries are currently obtained from: https://github.com/macchrome/winchrome
Recommended to run update.py on a schedule and/or on startup. note that updates will fail if chromium is in use.
requires python 3, 7zip, and psutil (pip3 install psutil)