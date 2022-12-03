# ungoogled-updater

Script for Windows to keep ungoogled-chromium up to date.
---

Will install/update Chromium in `%PROGRAMDATA%\Ungoogled Chromium\`.

You can change the install path by changing the `CHROMIUM_PATH` constant in `update.py`.

Binaries are obtained from [Marmaduke's repository](https://github.com/macchrome/winchrome).

**Requires:** Python 3, 7zip, `requests` and `psutil` (`pip install requests psutil`).

To enable automatic updates (on windows login and daily at `0:00`), run `python update.py --install`. *Updates will only succeed if chromium is not currently running.*
