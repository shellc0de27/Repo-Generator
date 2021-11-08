#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
     ____  ____  ____  _____     ___  ____  _  _  ____  ____    __   ____  _____  ____
    (  _ \( ___)(  _ \(  _  )   / __)( ___)( \( )( ___)(  _ \  /__\ (_  _)(  _  )(  _ \
     )   / )__)  )___/ )(_)(   ( (_-. )__)  )  (  )__)  )   / /(__)\  )(   )(_)(  )   /
    (_)\_)(____)(__)  (_____)   \___/(____)(_)\_)(____)(_)\_)(__)(__)(__) (_____)(_)\_)

    repository files and addons.xml generator

    All imports are from the built in standard library, with the exception of colorama (optional).
    Will need to pip3 install colorama and set colored_output=True in the config.ini

    **** See changelog.txt for all updates and fixes ****

    This file is "as is", without any warranty whatsoever. Use at your own risk

    Youtube Video Series for this script package:
        Playlist: https://www.youtube.com/playlist?list=PLYkSOUo1Vu4ZN6l6xJ9fzJ-d0Y_-ACo68
'''

__version__ = '1.5.9'

import os
import glob
import shutil
import hashlib
import zipfile
import traceback
from xml.dom import minidom
from sys import platform, stdout
from configparser import ConfigParser
try:
    import colorama as cr
    if platform == 'win32':
        if stdout.isatty():
            cr.init(convert=True)
        else:
            cr.init(strip=False)
except ImportError:
    pass


class Generator:
    '''
    Generates a new addons.xml file from each addons addon.xml file
    and a new addons.xml.md5 hash file. Must be run from a subdirectory (eg. _tools) of
    the checked-out repo. Only handles single depth folder structure.
    '''

    def __init__(self):
        '''
        Load the configuration
        '''
        self.tools_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__))))
        self.config = ConfigParser()
        self.config.read(os.path.join(self.tools_path, 'config.ini'))
        self.output_path = '_' + self.config.get('locations', 'output_path')
        self.excludes = self.config.get('addon', 'excludes').split(',')
        self.colored_output = self.config.getboolean('extras', 'colored_output')
        self.compress_zips = self.config.getboolean('extras', 'compress_zips')

        os.chdir(os.path.abspath(os.path.join(self.tools_path, os.pardir)))

        self._pre_run()
        self._generate_repo_files()
        self._get_filtered_path()
        self._generate_addons_file()
        self._generate_md5_file()
        self._generate_zip_files()

        self._printer('Finished updating addons xml, md5 files and zipping addons', color='green')
        self._printer('Always double check your MD5 Hash using a site like http://onlinemd5.com/', color='yellow')
        self._printer('if the repo is not showing files or downloading properly.', color='yellow')

    def _pre_run(self):
        if os.path.exists(self.output_path):
            shutil.rmtree(self.output_path, ignore_errors=True)
        os.makedirs(self.output_path)

    def _generate_repo_files(self):
        addonid = self.config.get('addon', 'id')
        name = self.config.get('addon', 'name')
        version = self.config.get('addon', 'version')
        author = self.config.get('addon', 'author')
        summary = self.config.get('addon', 'summary')
        description = self.config.get('addon', 'description')
        url = self.config.get('locations', 'url')

        if os.path.isfile(os.path.join(addonid, 'addon.xml')):
            return

        self._printer('Creating your repository addon for the first time', color='green')

        with open(os.path.join(self.tools_path, 'template.xml'), 'r') as template:
            template_xml = template.read()

        repo_xml = template_xml.format(
            addonid=addonid,
            name=name,
            version=version,
            author=author,
            summary=summary,
            description=description,
            url=url,
            output_path=self.output_path)

        if not os.path.exists(addonid):
            os.makedirs(addonid)

        self._save_file(repo_xml.encode('utf-8'), file=os.path.join(addonid, 'addon.xml'))

    def _get_filtered_path(self):
        self.addons = [os.path.join(x, 'addon.xml') for x in os.listdir() if os.path.isdir(x) and x not in [
            '.git', self.output_path[:-1], os.path.basename(self.tools_path)] and os.path.isfile(
            os.path.join(x, 'addon.xml'))]
        return self.addons

    def _generate_zip_files(self):
        for _path in self.addons:
            addon = _path.split(os.sep)[0]
            try:
                document = minidom.parse(_path)
                for parent in document.getElementsByTagName('addon'):
                    version = parent.getAttribute('version')
                    addonid = parent.getAttribute('id')
                self._generate_zip_file(addon, version, addonid)
            except Exception:
                self._printer('Kodi Repo Generator Exception', color='red', error=True)

    def _generate_zip_file(self, path, version, addonid):
        self._printer(f'Generating zip file for {addonid} {version}', color='cyan')
        cmode = zipfile.ZIP_DEFLATED if self.compress_zips else zipfile.ZIP_STORED
        filename = f'{path}-{version}.zip'
        try:
            with zipfile.ZipFile(filename, 'w', compression=cmode) as zips:
                for root, dirs, files in os.walk(path + os.path.sep):
                    for file in files:
                        ext = os.path.splitext(file)[-1].lower()
                        if ext not in self.excludes:
                            zips.write(os.path.join(root, file))

            os.makedirs(os.path.join(self.output_path, addonid))
            self._copy_files(addonid, filename)
        except Exception:
            self._printer('Kodi Repo Generator Exception', color='red', error=True)

    def _copy_files(self, addonid, zipped_file):
        dst_path = os.path.join(self.output_path, addonid)

        shutil.move(zipped_file, os.path.join(dst_path, zipped_file))
        shutil.copy(os.path.join(addonid, 'addon.xml'), os.path.join(dst_path, 'addon.xml'))
        try:
            icon_src = ''.join(str(x) for x in glob.glob(os.path.join(addonid, 'icon.*')) if x[-4:] != '.psd')
            shutil.copy(icon_src, os.path.join(dst_path, icon_src[-8:]))
        except FileNotFoundError:
            self._printer(f'**** Icon file missing for {addonid}', color='yellow')
        try:
            shutil.copy(os.path.join(addonid, 'fanart.jpg'), os.path.join(dst_path, 'fanart.jpg'))
        except FileNotFoundError:
            self._printer(f'**** Fanart file missing for {addonid}', color='yellow')

    def _generate_addons_file(self):
        addons_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<addons>\n'
        for _path in self.addons:
            try:
                with open(_path, 'r', encoding='utf-8') as xl:
                    xml_lines = xl.read().splitlines()

                addon_xml = '\n'.join(str(line.rstrip()) for line in xml_lines if not line.find('<?xml') >= 0)
                addons_xml += addon_xml + '\n\n'
            except Exception:
                self._printer(
                    f'Excluding {_path} for {_path.split(os.sep)[0]} due to a poorly formatted addon.xml',
                    color='red', error=True
                )

        addons_xml = addons_xml.strip() + '\n</addons>\n'
        self._save_file(addons_xml.encode('utf-8'), file=os.path.join(self.output_path, 'addons.xml'))

    def _generate_md5_file(self):
        try:
            hash_object = hashlib.md5()
            with open(os.path.join(self.output_path, 'addons.xml'), 'rb') as addons_file:
                hash_buf = addons_file.read()
                hash_object.update(hash_buf)

            result = hash_object.hexdigest()
            self._save_file(result.encode('utf-8'), file=os.path.join(self.output_path, 'addons.xml.md5'))
        except Exception:
            self._printer('**** An error occurred creating addons.xml.md5 file!', color='red', error=True)

    def _save_file(self, data, file):
        try:
            with open(file, 'w', encoding='utf-8') as sf:
                sf.write(data.decode('utf-8'))
        except Exception:
            self._printer(f'**** An error occurred saving --> {file}', color='red', error=True)

    def _printer(self, message, color='', error=False):
        try:
            if self.colored_output and error:
                print(f'{self._generate_fore_color(color)}{message}\n{traceback.format_exc()}{cr.Fore.RESET}')
            elif self.colored_output:
                print(f'{self._generate_fore_color(color)}{message}{cr.Fore.RESET}')
            elif error:
                print(f'{message}\n{traceback.format_exc()}')
            else:
                print(f'{message}')
        except NameError:
            print('Install colorama or set colored_output in the config file to False')

    def _generate_fore_color(self, fore_color):
        fore_colors = {
            'red': cr.Fore.RED, 'green': cr.Fore.GREEN, 'yellow': cr.Fore.YELLOW,
            'blue': cr.Fore.BLUE, 'magenta': cr.Fore.MAGENTA, 'cyan': cr.Fore.CYAN
        }
        return fore_colors[fore_color] if fore_color else ''


if __name__ == '__main__':
    apath = os.path.dirname(os.path.abspath(__file__))
    try:
        with open(os.path.join(apath, 'banner.txt'), 'r') as banner:
            print(banner.read())
    except FileNotFoundError:
        pass
    print(f'Executing the Kodi Repo Generator version {__version__}')
    Generator()
