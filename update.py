# exes from https://github.com/macchrome/winchrome/releases
# requires a valid installation of 7zip.
# also requires psutil and requests: pip install psutil requests
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import winreg
from distutils.dir_util import copy_tree
from pathlib import Path

import psutil
import requests

##############################
## Choose Install Location: ##
##############################
# Install in ProgramData (old default)
CHROMIUM_PATH = Path(os.getenv('PROGRAMDATA'), 'Ungoogled Chromium').resolve()
# Install in Program Files (recommended)
# CHROMIUM_PATH = Path(os.getenv('PROGRAMFILES'),'Ungoogled Chromium').resolve()
# Install in AppData (if installing for a single user only)
# CHROMIUM_PATH = Path(os.getenv('LOCALAPPDATA'),'Programs','Ungoogled Chromium').resolve()
##############################
##############################
VERSION_FROM_TAG = re.compile('M([\d\.]*)')
RELEASE_INFO_PATH = CHROMIUM_PATH.joinpath('github_asset_info')
IS_64_BIT = platform.machine().endswith('64')


class ChromiumUpdater:
    OWNER = 'macchrome'
    REPO = 'winchrome'

    def __init__(self):
        try:
            CHROMIUM_PATH.mkdir()   # can use exist_ok=True if pathlib > 3.5
        except FileExistsError:
            pass
        sub_key_7zfm = (
            r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\7zFM.exe'
        )
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, sub_key_7zfm
            ) as key_handle:
                sevenzipfm_dir = winreg.QueryValueEx(key_handle, 'Path')[0]
        except OSError:
            raise Exception('Unable to locate 7-zip from the Windows Registry')
        self.SEVENZIP = Path(sevenzipfm_dir, '7z.exe')
        if not self.SEVENZIP.is_file():
            raise Exception(
                f'7z.exe not found at path from registry: {self.SEVENZIP}'
            )
        self.sinfo = subprocess.STARTUPINFO()
        self.sinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    def _get_latest_release(self):
        r = requests.get(
            f'https://api.github.com/repos/{self.OWNER}/{self.REPO}/releases'
        )
        r.raise_for_status()
        for release in sorted(
            [r for r in r.json() if 'ungoogled' in r['name'].lower()],
            key=lambda a: a['id'],
            reverse=True,
        ):
            version = VERSION_FROM_TAG.search(release['tag_name'])
            if not version:
                raise Exception('Release version number could not be parsed.')
            valid_assets = [
                a
                for a in sorted(
                    release['assets'], key=lambda a: a['id'], reverse=True
                )
                if a['name']
                .lower()
                .endswith(f"{'win64' if IS_64_BIT else 'win32'}.7z")
            ]
            if not valid_assets:
                continue
            valid_assets[0]['release_version'] = version.group(1)
            return valid_assets[0]
        raise Exception('No ungoogled versions found in releases.')

    def _check_running(self):
        for proc in psutil.process_iter():
            try:
                exepath = Path(CHROMIUM_PATH, 'chrome.exe')
                if proc.name() == exepath.name and proc.exe() == str(exepath):
                    raise Exception('Chromium is currently running.')
            except psutil.NoSuchProcess as err:
                pass
            except psutil.AccessDenied:
                pass

    def run_on_schedule_and_startup(self, enable=True, path=Path(__file__)):
        startup_key = r'Software\Microsoft\Windows\CurrentVersion\Run'
        winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, startup_key)
        key = winreg.OpenKeyEx(
            winreg.HKEY_CURRENT_USER, startup_key, access=winreg.KEY_WRITE
        )
        if enable:
            winreg.SetValueEx(
                key,
                'Ungoogled Chromium Updater',
                0,
                winreg.REG_SZ,
                f'"{sys.executable.replace("python.exe","pythonw.exe")}" "{path}"',
            )
        else:
            try:
                winreg.DeleteValue(key, 'Ungoogled Chromium Updater')
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        if enable:
            os.system(
                rf"""SchTasks /Create /SC DAILY /TN "Ungoogled Chromium Updater" /TR "'{sys.executable.replace('python.exe','pythonw.exe')}' '{path.absolute()}'" /ST 00:00 /F"""
            )
        else:
            os.system(
                """SchTasks /Delete /TN "Ungoogled Chromium Updater" /F"""
            )

    def verify_archive(self, zippath, expected_version):
        """returns name of chrome archive or None if not found."""
        bytes = subprocess.check_output(
            [str(self.SEVENZIP), 'l', str(zippath)], startupinfo=self.sinfo
        )
        paths = [
            split[-1]
            for split in [
                line.split() for line in bytes.decode('utf-8').splitlines()
            ]
            if len(split) and split[-1].endswith('.manifest')
        ]
        for filepath in paths:
            fp = Path(filepath)
            if fp.parent.name and fp.stem == expected_version:
                return fp.parent
        return None

    def update(self):
        self._check_running()
        if RELEASE_INFO_PATH.exists():
            with RELEASE_INFO_PATH.open('r') as f:
                current_release_id = json.load(f)['id']
        else:
            current_release_id = 0
        new_version_info = self._get_latest_release()
        if current_release_id != new_version_info['id']:
            print('New version found, updating...')
        else:
            print('Ungoogled Chromium is up to date.')
            return
        tmpzip = Path(CHROMIUM_PATH, 'zipped_tmp.7z')
        try:
            tmpzip.unlink()   # can use missing_ok=True if pathlib > 3.8
        except FileNotFoundError:
            pass
        r = requests.get(new_version_info['browser_download_url'])
        r.raise_for_status()
        tmpzip.write_bytes(r.content)

        archive_contents = self.verify_archive(
            tmpzip, new_version_info['release_version']
        )
        if not archive_contents:
            raise Exception('Unexpected contents of Chromium archive.')
        googledir = Path(CHROMIUM_PATH, archive_contents)
        try:
            output = subprocess.check_output(
                [
                    str(self.SEVENZIP),
                    'x',
                    str(tmpzip),
                    f'-o{CHROMIUM_PATH}',
                    '-y',
                ],
                startupinfo=self.sinfo,
            )
        except subprocess.CalledProcessError:
            raise Exception('7zip extraction failed.')

        # delete all files in directory:
        for path in CHROMIUM_PATH.iterdir():
            if path.is_dir():
                if path != googledir:
                    shutil.rmtree(path)
            elif path.name not in (tmpzip.name, os.path.basename(__file__)):
                path.unlink()

        # copy contents of folder.
        copy_tree(googledir, str(CHROMIUM_PATH))
        # cleanup
        with RELEASE_INFO_PATH.open('w') as f:
            json.dump(new_version_info, f)
        try:
            tmpzip.unlink()   # can use missing_ok=True if pathlib > 3.8
        except FileNotFoundError:
            pass
        shutil.rmtree(googledir)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Update Ungoogled Chromium.')
    parser.add_argument(
        '--install',
        action='store_true',
        help='Automatically update on Windows login and daily at 00:00.',
    )
    parser.add_argument(
        '--uninstall', action='store_true', help='Do not run automatically.'
    )

    args = parser.parse_args()
    c = ChromiumUpdater()
    try:
        c.update()
    finally:
        if args.install or args.uninstall:
            shutil.copyfile(
                Path(__file__).absolute(),
                Path(CHROMIUM_PATH, os.path.basename(__file__)),
            )
            c.run_on_schedule_and_startup(
                enable=args.install,
                path=Path(CHROMIUM_PATH, os.path.basename(__file__)),
            )
