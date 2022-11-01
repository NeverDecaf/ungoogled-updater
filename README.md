# ungoogled-updater

Script for Windows to keep ungoogled-chromium up to date.
---

Will install/update Chromium in `%PROGRAMDATA%\Ungoogled Chromium\`.

You can change the install path to `%APPDATA%\Ungoogled Chromium\` by changing the `CHROMIUM_PATH` constant in `update.py`.

Binaries are obtained from [Marmaduke's repository](https://github.com/macchrome/winchrome).

**Requires:** Python 3, 7zip, `requests` and `psutil` (`pip3 install requests psutil`).

To setup to automatically run on Windows login, run `python update.py --install`.
