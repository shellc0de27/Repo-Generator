# -*- coding: UTF-8 -*-
'''
     ____  ____  ____  _____     ___  ____  _  _  ____  ____    __   ____  _____  ____
    (  _ \( ___)(  _ \(  _  )   / __)( ___)( \( )( ___)(  _ \  /__\ (_  _)(  _  )(  _ \
     )   / )__)  )___/ )(_)(   ( (_-. )__)  )  (  )__)  )   / /(__)\  )(   )(_)(  )   /
    (_)\_)(____)(__)  (_____)   \___/(____)(_)\_)(____)(_)\_)(__)(__)(__) (_____)(_)\_)

    repository files and addons.xml generator

    All imports are from the built in standard library, with the exception of colorama (optional).
    Will need to pip3 install colorama and set colored_output=True in the config.ini

    Unknown Dates - Work of previous developers
        Modified by Rodrigo@XMBCHUB to zip plugins/repositories to a "zip" folder
        Modified by BartOtten: create a repository addon, skip folders without addon.xml, user config file
    11/12/2017
        Modified by MuadDib: Include copying of addon.xml, icon.png, and fanart.jpg when present in addon folders
    04/12/2018
        Modified by MuadDib: Fixed md5 hashing issue for addons.xml file
        Modified by MuadDib: Added excludes line to config.ini. This is a comma separated value of file extensions to
        not add to zip file in releases
    12/4/2020
        Modified by Shellc0de: Cleaned up some code. Added the ability to capture .png or .gif for icons
    12/13/2020
        Modified by Shellc0de: Port to Python 3.6+ only. Anything lower is not supported
        Modified by Shellc0de: Automatically deletes _zips (output_path set in the config.ini) folder for you
        whenever the repo needs to be updated
    01/22/2021
        Modified by Shellc0de: Code fixes and updates. Can now run from IDE's without having to set the absolute path.
    07/25/2021
        Modified by Shellc0de: Code updates, 2 new methods created.
    10/09/2021
        Modified by Shellc0de: Added colored output to the terminal and zip compression which both are optional
        and off by default. They can be enabled in the config.ini by setting the value to True. NOTE - enabling
        compression will be make this script slower for obvious reasons.

    This file is "as is", without any warranty whatsoever. Use at your own risk

    Youtube Video Series for this script package:
        Playlist: https://www.youtube.com/playlist?list=PLYkSOUo1Vu4ZN6l6xJ9fzJ-d0Y_-ACo68
'''

import os
import glob
import shutil
import hashlib
import zipfile
import traceback
from xml.dom import minidom
from configparser import ConfigParser
try:
    from colorama import init, Fore
    init(autoreset=True)
except ImportError:
    print('*** Note: PIP install colorama if you want colored text in the terminal.')


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

        self._printer(msg='Finished updating addons xml, md5 files and zipping addons', color='green')
        self._printer(msg='Always double check your MD5 Hash using a site like http://onlinemd5.com/', color='yellow')
        self._printer(msg='if the repo is not showing files or downloading properly.', color='yellow')

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

        self._printer(msg='Creating your repository addon for the first time', color='green')

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
                self._printer(color='red')
                self._printer(msg=f'{traceback.format_exc()}')

    def _generate_zip_file(self, path, version, addonid):
        self._printer(msg=f'Generating zip file for {addonid} {version}', color='green')
        cmode = zipfile.ZIP_DEFLATED if self.compress_zips is True else zipfile.ZIP_STORED
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
            self._printer(color='red')
            self._printer(msg=f'{traceback.format_exc()}')

    def _copy_files(self, addonid, zipped_file):
        dst_path = os.path.join(self.output_path, addonid)

        shutil.move(zipped_file, os.path.join(dst_path, zipped_file))
        shutil.copy(os.path.join(addonid, 'addon.xml'), os.path.join(dst_path, 'addon.xml'))
        try:
            icon_src = ''.join(str(x) for x in glob.glob(os.path.join(addonid, 'icon.*')) if x[-4:] != '.psd')
            shutil.copy(icon_src, os.path.join(dst_path, icon_src[-8:]))
        except FileNotFoundError:
            self._printer(msg=f'**** Icon file missing for {addonid}', color='yellow')
        try:
            shutil.copy(os.path.join(addonid, 'fanart.jpg'), os.path.join(dst_path, 'fanart.jpg'))
        except FileNotFoundError:
            self._printer(msg=f'**** Fanart file missing for {addonid}', color='yellow')

    def _generate_addons_file(self):
        addons_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<addons>\n'
        for _path in self.addons:
            try:
                with open(_path, 'r', encoding='utf-8') as xl:
                    xml_lines = xl.read().splitlines()

                addon_xml = '\n'.join(str(line.rstrip()) for line in xml_lines if not line.find('<?xml') >= 0)
                addons_xml += addon_xml + '\n\n'
            except Exception:
                self._printer(msg=f'Excluding {_path} for {_path.split(os.sep)[0]} due to missing or poorly formatted addon.xml', color='red')
                self._printer(msg=f'{traceback.format_exc()}')

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
            self._printer(msg='**** An error occurred creating addons.xml.md5 file!', color='red')
            self._printer(msg=f'{traceback.format_exc()}')

    def _save_file(self, data, file):
        try:
            with open(file, 'w', encoding='utf-8') as sf:
                sf.write(data.decode('utf-8'))
        except Exception:
            self._printer(msg=f'**** An error occurred saving --> {file}', color='red')
            self._printer(msg=f'{traceback.format_exc()}')

    def _printer(self, msg='Kodi Repo Generator Exception', color=''):
        if self.colored_output is True:
            try:
                fore_colors = {
                    'red': Fore.RED, 'green': Fore.GREEN, 'yellow': Fore.YELLOW,
                    'blue': Fore.BLUE, 'magenta': Fore.MAGENTA, 'cyan': Fore.CYAN
                }
                color = fore_colors[color] if color else ''
                print(f'{color}{msg}')
            except NameError:
                print('Install colorama or set colored_output in the config file to False')
        else:
            print(f'{msg}')


if __name__ == '__main__':
    print('Executing the Kodi Repo Generator.....')
    Generator()
