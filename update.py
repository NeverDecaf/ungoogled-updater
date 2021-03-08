# exes from https://github.com/macchrome/winchrome/releases
# requires a valid installation of 7zip.
# also requires psutil: pip3 install psutil
import os
import requests
import winreg
import re
from pathlib import Path
import subprocess
import shutil
from distutils.dir_util import copy_tree
import psutil

CHROMIUM_PATH = Path(os.getenv('PROGRAMDATA'),'Ungoogled Chromium')
VERSION_FROM_TAG = re.compile('^v([\d\.]*)')

class ChromiumUpdater:
    OWNER = 'macchrome'
    REPO = 'winchrome'
    def __init__(self):
        try:
            CHROMIUM_PATH.mkdir() # can use exist_ok=True if pathlib > 3.5
        except FileExistsError:
            pass
        sub_key_7zfm = r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\7zFM.exe'
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_key_7zfm) as key_handle:
                sevenzipfm_dir = winreg.QueryValueEx(key_handle, 'Path')[0]
        except OSError:
            raise Exception('Unable to locate 7-zip from the Windows Registry')
        self.SEVENZIP = Path(sevenzipfm_dir, '7z.exe')
        if not self.SEVENZIP.is_file():
            raise Exception(f'7z.exe not found at path from registry: {self.SEVENZIP}')
        
    def _get_latest_release(self):
        r = requests.get(f'https://api.github.com/repos/{self.OWNER}/{self.REPO}/releases')
        r.raise_for_status()
        js = r.json()
        for release in sorted(js, key=lambda a:a['id'], reverse=True):
            version = VERSION_FROM_TAG.findall(release['tag_name'])
            if not len(version):
                raise Exception('Release version number could not be parsed.')
            version = version[0]
            if 'ungoogled' not in release['name'].lower():
                continue
            self.DOWNLOAD_URL = release['assets'][0]['browser_download_url']
            return version
        else:
            raise Exception('No ungoogled versions found in releases.')
            
    def _check_running(self):
        for proc in psutil.process_iter():
            try:
                exepath = Path(CHROMIUM_PATH,'chrome.exe')
                if proc.name() == exepath.name and proc.exe() == str(exepath):
                    raise Exception('Chromium is currently running.')
            except psutil.NoSuchProcess as err:
                pass
            except psutil.AccessDenied:
                pass
            
    def run_on_windows_startup(self, enable = True, path = __file__ ):
        startup_key = r'Software\Microsoft\Windows\CurrentVersion\Run'
        winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, startup_key)
        key = winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, startup_key, access=winreg.KEY_WRITE)
        winreg.SetValueEx(key, 'Ungoogled Chromium Updater', 0, winreg.REG_SZ, f'pyw "{path}"')
        winreg.CloseKey(key)

    def update(self):
        self._check_running()
        new_version = self._get_latest_release()
        version = [path for path in CHROMIUM_PATH.iterdir() if path.suffix.lower() == '.manifest']
        version = version[0].stem if version else '0'
        if version != new_version:
            print('New version found, updating...')
        else:
            print('Ungoogled Chromium is up to date.')
            return
        tmpzip = Path(CHROMIUM_PATH,'zipped_tmp.7z')
        try:
            tmpzip.unlink() # can use missing_ok=True if pathlib > 3.8
        except FileNotFoundError:
            pass
        r = requests.get(self.DOWNLOAD_URL)
        r.raise_for_status()
        tmpzip.write_bytes(r.content)
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        dirs_before = set([f for f in CHROMIUM_PATH.iterdir() if f.is_dir()])
        try:
            output = subprocess.check_output([str(self.SEVENZIP), 'x', str(tmpzip), f'-o{CHROMIUM_PATH}','-y'], startupinfo=si)
        except subprocess.CalledProcessError:
            raise Exception('7zip extraction failed.')
        dirs_after = set([f for f in CHROMIUM_PATH.iterdir() if f.is_dir()])
        if len(dirs_after-dirs_before) != 1:
            raise Exception('Unexpected contents of Chromium archive.')
        googledir = (dirs_after-dirs_before).pop()
        
        # delete all files in directory:
        for path in CHROMIUM_PATH.iterdir():
            if path.is_dir():
                if path != googledir:
                    shutil.rmtree(path)
            elif path.name not in (tmpzip.name,os.path.basename(__file__)):
                path.unlink()

        # copy contents of folder.
        copy_tree(googledir, str(CHROMIUM_PATH))
        #cleanup
        try:
            tmpzip.unlink() # can use missing_ok=True if pathlib > 3.8
        except FileNotFoundError:
            pass
        shutil.rmtree(googledir)
            
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Update Ungoogled Chromium.')
    parser.add_argument('--install', action='store_true',
                        help='Automatically update on windows login.')

    args = parser.parse_args()
    c = ChromiumUpdater()
    c.update()
    if args.install:
        shutil.copyfile(os.path.abspath(__file__),Path(CHROMIUM_PATH,os.path.basename(__file__)))
        c.run_on_windows_startup(path=Path(CHROMIUM_PATH,os.path.basename(__file__)))
        print('Install successful, will run automatically on Windows startup.')
