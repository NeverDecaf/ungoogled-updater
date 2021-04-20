# ungoogled-updater
Script for windows to keep ungoogled-chromium up to date.  
Will install/update chromium in %PROGRAMDATA%\Ungoogled Chromium\  
binaries are currently obtained from: https://github.com/macchrome/winchrome  
requires python 3, 7zip, and psutil (pip3 install psutil)  
To setup to automatically run on Windows login, run `python update.py --install`
