# ungoogled-updater

## Script for Windows to keep ungoogled-chromium up to date.

Will install/update Chromium in `%PROGRAMDATA%\Ungoogled Chromium\` by default.

You can change the install path by uncommenting the desired `CHROMIUM_PATH` constant in `update.py`.

Binaries are obtained from [Marmaduke's repository](https://github.com/macchrome/winchrome).

**Requires:** Python 3, 7zip, `requests` and `psutil` (and `setuptools` if Python 3.12 or above)

```bash
pip3 install requests psutil setuptools
```

To enable automatic updates (on windows login and daily at `0:00`), run `python update.py --install`. _Updates will only succeed if Chromium is not currently running._
