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

CHROMIUM_PATH = Path(os.getenv('PROGRAMDATA'),'Ungoogled Chromium')
VERSION_FROM_TAG = re.compile('^v([\d\.]*)')
import psutil
class ChromiumUpdater(object):
    OWNER = 'macchrome'
    REPO = 'winchrome'
    def __init__(self):
        try:
            os.mkdir(CHROMIUM_PATH)
        except FileExistsError:
            pass
        sub_key_7zfm = 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\7zFM.exe'
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_key_7zfm) as key_handle:
                sevenzipfm_dir = winreg.QueryValueEx(key_handle, 'Path')[0]
        except OSError:
            raise Exception('Unable to locate 7-zip from the Windows Registry')
        sevenzip_path = Path(sevenzipfm_dir, '7z.exe')
        if not sevenzip_path.is_file():
            raise Exception('7z.exe not found at path from registry: {}'.format(sevenzip_path))
        self.SEVENZIP = sevenzip_path
        self._check_running()
        
    def _get_latest_release(self):
        r = requests.get('https://api.github.com/repos/{}/{}/releases'.format(self.OWNER, self.REPO))
        r.raise_for_status()
        js = r.json()
        latest = sorted(js,key=lambda x: x['id'])[-1]

        r = requests.get('https://api.github.com/repos/{}/{}/releases/{}'.format(self.OWNER, self.REPO, latest['id']))
        r.raise_for_status()
        js = r.json()
        version = VERSION_FROM_TAG.findall(js['tag_name'])
        if not len(version):
            raise Exception('Latest release version number could not be parsed.')
        version = version[0]
        ungoogled = [release for release in js['assets'] if 'ungoogled' in release['name'].lower() and 'windows' in release['name'].lower()]
        if not len(ungoogled):
            raise Exception('No ungoogled version found in latest release.')
        self.DOWNLOAD_URL = ungoogled[0]['browser_download_url']
        return version

    def _check_running(self):
        for proc in psutil.process_iter():
            try:
                if proc.name() == 'chrome.exe' and proc.exe() == str(Path(CHROMIUM_PATH,'chrome.exe')):
                    raise Exception('Chromium is currently running.')
            except psutil.NoSuchProcess as err:
                pass
            except psutil.AccessDenied:
                pass
            
    def run_on_windows_startup(self, enable = True):
        startup_key = r'Software\Microsoft\Windows\CurrentVersion\Run'
        winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, startup_key)
        key = winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, startup_key, access=winreg.KEY_WRITE)
        winreg.SetValueEx(key, 'Ungoogled Chromium Updater', 0, winreg.REG_SZ, '"{}"'.format(__file__))
        winreg.CloseKey(key)

    def update(self):
        new_version = self._get_latest_release()
        version = [name for name in os.listdir(CHROMIUM_PATH) if name.lower().endswith('manifest')]
        if len(version):
            version = os.path.splitext(version[0])[0]
        else:
            version = '0'
        if version != new_version:
            print('New version found, updating...')
        tmpzip = Path(CHROMIUM_PATH,'zipped_tmp.7z')
        try:
            os.remove(tmpzip)
        except FileNotFoundError:
            pass
        r = requests.get(self.DOWNLOAD_URL)
        r.raise_for_status()
        with open(tmpzip,'wb') as fp:
            fp.write(r.content)
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        try:
            output = subprocess.check_output([str(self.SEVENZIP), 'x', str(tmpzip), '-o{}'.format(CHROMIUM_PATH)], startupinfo=si)
        except subprocess.CalledProcessError:
            raise Exception('7zip extraction failed.')
        
        # delete all files in directory:
        for path in os.listdir(CHROMIUM_PATH):
            if os.path.isdir(Path(CHROMIUM_PATH,path)):
                if not path.startswith('ungoogled'):
                    shutil.rmtree(Path(CHROMIUM_PATH,path))
                else:
                    googledir = Path(CHROMIUM_PATH,path)
            elif path != os.path.basename(tmpzip):
                os.remove(Path(CHROMIUM_PATH,path))

        # copy contents of folder.
        copy_tree(googledir, str(CHROMIUM_PATH))
        #cleanup
        try:
            os.remove(tmpzip)
        except FileNotFoundError:
            pass
        shutil.rmtree(googledir)
            
if __name__ == '__main__':
    c = ChromiumUpdater()
    c.update()
##    c.run_on_windows_startup()
