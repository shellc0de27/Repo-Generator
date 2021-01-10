# -*- coding: UTF-8 -*-
'''
     ____  ____  ____  _____     ___  ____  _  _  ____  ____    __   ____  _____  ____
    (  _ \( ___)(  _ \(  _  )   / __)( ___)( \( )( ___)(  _ \  /__\ (_  _)(  _  )(  _ \
     )   / )__)  )___/ )(_)(   ( (_-. )__)  )  (  )__)  )   / /(__)\  )(   )(_)(  )   /
    (_)\_)(____)(__)  (_____)   \___/(____)(_)\_)(____)(_)\_)(__)(__)(__) (_____)(_)\_)

    repository files and addons.xml generator

    All imports are from the built in standard library, nothing else is needed

    Unknown Dates - Work of previous developers
        Modified by Rodrigo@XMBCHUB to zip plugins/repositories to a "zip" folder
        Modified by BartOtten: create a repository addon, skip folders without addon.xml, user config file
    11/12/2017
        Modified by MuadDib: Include copying of addon.xml, icon.png, and fanart.jpg when present in addon folders
    04/12/2018
        Modified by MuadDib: Fixed md5 hashing issue for addons.xml file
        Modified by MuadDib: Added excludes line to config.ini. This is a comma separated value of file extensions to not add to zip file in releases
    12/4/2020
        Modified by Shellc0de: Cleaned up some code. Added the ability to capture both .png and .gif for icons
    12/13/2020
        Modified by Shellc0de: Port to Python 3.6+ only. Anything lower is not supported
        Modified by Shellc0de: Automatically deletes _zips (output_path set in the config.ini) folder for you
        whenever the repo needs to be updated

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
        self.config = ConfigParser()
        self.config.read('config.ini')
        self.tools_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__))))
        self.output_path = '_' + self.config.get('locations', 'output_path')
        self.excludes = self.config.get('addon', 'excludes').split(',')

        os.chdir(os.path.abspath(os.path.join(self.tools_path, os.pardir)))

        self._pre_run()
        self._generate_repo_files()
        self._generate_addons_file()
        self._generate_md5_file()
        self._generate_zip_files()

        print('Finished updating addons xml, md5 files and zipping addons')
        print('Always double check your MD5 Hash using a site like http://onlinemd5.com/', end=' ')
        print('if the repo is not showing files or downloading properly.')

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

        if os.path.isfile(addonid + os.path.sep + 'addon.xml'):
            return

        print('Create repository addon')

        with open(self.tools_path + os.path.sep + 'template.xml', 'r') as template:
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

        self._save_file(repo_xml.encode('utf-8'), file=addonid + os.path.sep + 'addon.xml')

    def _generate_zip_files(self):
        addons = os.listdir('.')
        for addon in addons:
            if not os.path.isdir(addon) or addon in ['.git', self.output_path[:-1], os.path.basename(self.tools_path)]:
                continue
            _path = os.path.join(addon, 'addon.xml')
            if not os.path.isfile(_path):
                continue
            try:
                document = minidom.parse(_path)
                for parent in document.getElementsByTagName('addon'):
                    version = parent.getAttribute('version')
                    addonid = parent.getAttribute('id')
                self._generate_zip_file(addon, version, addonid)
            except Exception:
                failure = traceback.format_exc()
                print(f'Kodi Repo Generator Exception: \n{failure}')

    def _generate_zip_file(self, path, version, addonid):
        print(f'Generate zip file for {addonid} {version}')
        filename = '{path}-{version}.zip'.format(path=path, version=version)
        try:
            with zipfile.ZipFile(filename, 'w') as zips:
                for root, dirs, files in os.walk(path + os.path.sep):
                    for file in files:
                        ext = os.path.splitext(file)[-1].lower()
                        if ext not in self.excludes:
                            zips.write(os.path.join(root, file))

            if not os.path.exists(self.output_path + addonid):
                os.makedirs(self.output_path + addonid)

            dst_path = self.output_path + addonid + os.path.sep

            shutil.move(filename, dst_path + filename)
            shutil.copy(addonid + '/addon.xml', dst_path + 'addon.xml')
            try:
                icon_src = ''.join(str(x) for x in glob.glob(addonid + '/icon.*') if x[-4:] != '.psd')
                shutil.copy(icon_src, dst_path + icon_src[-8:])
            except Exception:
                print(f'**** Icon file missing for {addonid}')
            try:
                shutil.copy(addonid + '/fanart.jpg', dst_path + 'fanart.jpg')
            except Exception:
                print(f'**** Fanart file missing for {addonid}')

        except Exception:
            failure = traceback.format_exc()
            print(f'Kodi Repo Generator Exception: \n{failure}')

    def _generate_addons_file(self):
        addons = os.listdir('.')
        addons_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<addons>\n'
        for addon in addons:
            _path = os.path.join(addon, 'addon.xml')
            if not os.path.isfile(_path):
                continue
            try:
                with open(_path, 'r', encoding='utf-8') as xl:
                    xml_lines = xl.read().splitlines()

                addon_xml = '\n'.join(str(line.rstrip()) for line in xml_lines if not line.find('<?xml') >= 0)
                addons_xml += addon_xml + '\n\n'
            except Exception:
                failure = traceback.format_exc()
                print(f'Excluding {_path} for {addon} due to missing or poorly formatted addon.xml')
                print(f'Exception Details: \n{failure}')

        addons_xml = addons_xml.strip() + '\n</addons>\n'
        self._save_file(addons_xml.encode('utf-8'), file=self.output_path + 'addons.xml')

    def _generate_md5_file(self):
        try:
            hash_object = hashlib.md5()
            with open(self.output_path + 'addons.xml', 'rb') as addons_file:
                hash_buf = addons_file.read()
                hash_object.update(hash_buf)

            result = hash_object.hexdigest()
            self._save_file(result.encode('utf-8'), file=self.output_path + 'addons.xml.md5')
        except Exception:
            failure = traceback.format_exc()
            print('**** An error occurred creating addons.xml.md5 file!')
            print(f'Kodi Repo Generator Exception: \n{failure}')

    def _save_file(self, data, file):
        try:
            with open(file, 'w', encoding='utf-8') as sf:
                sf.write(data.decode('utf-8'))
        except Exception:
            failure = traceback.format_exc()
            print(f'**** An error occurred saving --> {file}')
            print(f'Kodi Repo Generator Exception: \n{failure}')


if __name__ == '__main__':
    print('Executing the Kodi Repo Generator.....')
    Generator()
