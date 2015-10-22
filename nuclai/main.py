import os
import re
import sys
import json
import glob
import time
import shutil
import zipfile
import argparse
import tempfile
import subprocess
import urllib.request
import urllib.parse


class ansi:
    WHITE = '\033[0;97m'
    WHITE_B = '\033[1;97m'
    YELLOW = '\033[0;33m'
    RED = '\033[0;31m'
    RED_B = '\033[1;31m'
    GREEN = '\033[0;32m'
    BLUE = '\033[0;94m'
    ENDC = '\033[0m'

def display(text, color=ansi.WHITE):
    bold = color.replace('[0;', '[1;')
    text = re.sub(r'`(.*?)`', r'`{}\1{}`'.format(bold, color), text)
    print(color + text + ansi.ENDC)
    

def symlink(src, dst):
    if 'win32' in sys.platform:
        import ctypes
        kernel32 = ctypes.windll.LoadLibrary("kernel32.dll")
        kernel32.CreateSymbolicLinkW(dst, src, 1)
        if not os.path.exists(dst):
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy(src, dst)
    else:
        os.symlink(src, dst)


class Application(object):

    def __init__(self):
        self.calls = []

    def call(self, *cmdline, **params):
        self.calls.append((cmdline, params))
        
    def execute(self):
        self.log.truncate()

        for cmdline, params in self.calls:
            ret = subprocess.call(cmdline, stdout=self.log, stderr=self.log, **params)
            if ret != 0:
                raise RuntimeError('Command returned status %i.' % ret)
        self.calls = []
    
    def recipe_github(self, repo, rev):
        folder = re.split('[/.]', repo)[1]
        if not os.path.exists(folder):
            self.call('git', 'clone', 'https://github.com/'+repo)
        else:
            self.call('git', 'pull', cwd=folder)
        self.call('git', 'reset', '--hard', rev, cwd=folder)
        if os.path.exists(os.path.join(folder, 'setup.py')):
            self.call('python', 'setup.py', 'develop', cwd=folder)            
        return folder, ''

    def recipe_extract(self, archive, target):
        if not os.path.exists(target):
            zf = zipfile.ZipFile(archive)
            base, *files = zf.namelist()
            if all([f.startswith(base) for f in files]):
                zf.extractall(path=".")
                print(base, '->', target)
                shutil.move(base, target)
            else:
                assert False, "Found no root folder as expected."
            zf.close()
        os.remove(archive)
        return target, ''

    def recipe_shell(self, title, *args):
        self.call(*args, shell=True)
        return title, ''

    def recipe_pypi(self, *packages):
        remaining = []
        packages = list(packages)
        if 'cython' in packages: packages.append('cython.py')
        for p in packages:
            base_folder = os.path.join(sys.base_prefix, 'Lib', 'site-packages', p)
            # TODO: Scan other than base_prefix, not good enough.
            # for f in glob.glob(base_folder + '*'):
            #     print(f, flush=True)
            # os._exit(-1)

            target_folder = os.path.join(sys.prefix, 'Lib', 'site-packages', p)
            if os.path.exists(base_folder) and not os.path.exists(target_folder):
                symlink(base_folder, target_folder)
            if not os.path.exists(target_folder):
                remaining.append(p)

        if remaining:
            self.call('pip', 'install', *remaining)
        return ' '.join(packages),  ''

    def recipe_wheel(self, root, slug):
        import distutils.util
        filename = '{}-cp34-cp34m-{}.whl'.format(slug, distutils.util.get_platform().replace('.', '_').replace('-', '_'))
        url = root + filename
        filename = os.path.join(tempfile.mkdtemp(), filename)
        try:
            urllib.request.urlretrieve(url, filename)
        except urllib.error.HTTPError as e:
            raise RuntimeError("File not found as wheel: %s.".format(slug))
        self.call('pip', 'install', filename)
        return slug, ''

    def recipe_del(self, target):
        if os.path.isfile(target):
            os.remove(target)
        if os.path.isdir(target):
            shutil.rmtree(target)
        return target, ''

    def recipe_exec(self, *args):
        args, brief = list(args), os.path.split(args[0])[1]
        if args[0].endswith('.py'):
            args.insert(0, 'python')
        self.call(*args)
        return brief,  ''

    def recipe_fetch(self, url, file):
        if not os.path.exists(file):
            urllib.request.urlretrieve(url, file)
        return file, ''

    def recipe_open(self, target):
        if 'win32' in sys.platform:
            os.startfile(target.replace(r'/', r'\\'))
        else:
            self.call('open', target)
        return target, ''

    def cmd_install(self, name, pkg):
        display('Installing nucl.ai package `{}`.'.format(name), ansi.BLUE)
        self.do_recipes(pkg['install']['osx'])

    def cmd_demo(self, name, pkg):
        display('Demonstrating nucl.ai package `{}`.'.format(name), ansi.BLUE)
        self.do_recipes(pkg['demo'])
        
    def do_recipes(self, recipes):
        for cmd, *args in recipes:
            recipe = getattr(self, 'recipe_'+cmd)
            step = ansi.WHITE_B+('{: <8}'.format(cmd))+ansi.ENDC

            try:
                status = '✓'
                brief, detail = recipe(*args)
                print(' ● {} {: <40} …'.format(step, brief), end='', flush=True)
                self.execute()
            except RuntimeError:
                detail = None
                status = ansi.RED_B + '✗' + ansi.ENDC
                print('\n%sRuntime error while executing command. See `%s` for details.%s' % (ansi.RED, self.command, ansi.ENDC))
            except:
                import traceback
                traceback.print_exc()
            
            print('\r ● {} {: <40} {}'.format(step, brief, status), flush=True)
            if detail is None:
                break

    def is_stale(self, filename):
        if not os.path.exists(filename):
            return True

        modified = os.path.getmtime(filename)
        yesterday = time.time() - 24 * 3600
        return bool(modified < yesterday)

    def _parse(self, args):
        root = argparse.ArgumentParser(prog='nuclai')
        sub = root.add_subparsers(title='commands', dest='command', description='Specific commands available.')
        p_install = sub.add_parser('install', help='Download and setup a remote package.')
        p_install.add_argument('package', type=str)
        p_demo = sub.add_parser('demo', help='Run demonstration for an installed package.')
        p_demo.add_argument('package', type=str)
        params = root.parse_args(args)
        print(params)
        return params

    def main(self, args):
        params = self._parse(args)

        cmd, package = params.command, params.package
        command = getattr(self, 'cmd_'+cmd)

        if not os.path.isdir(package):
            os.mkdir(package)            
        os.chdir(package)

        filename = package+'.json'
        # if self.is_stale(filename):
        #     urllib.request.urlretrieve('http://courses.nucl.ai/packages/'+filename, filename)
        pkg = json.load(open(filename))
        
        self.command = cmd
        self.log = open(cmd+'.log', 'w')
        command(package, pkg)
        print('')
        return 0


def main(args):
    # Must be a UTF-8 compatible codepage in the terminal or output doesn't work.
    if 'win32' in sys.platform:
        with open(os.devnull, 'w') as null:
            subprocess.call(['chcp', '65001'], stdout=null, stderr=null, shell=True)

    # Fail if the user is running from a system-wide Python 3.4 installation.
    if not hasattr(sys, 'base_prefix'):
        display('ERROR: Please run this script from a virtual environment.\n', color=ansi.RED_B)
        executable = os.path.split(sys.executable)[1]
        display('  > {} -m venv pyenv\n'.format(executable), color=ansi.RED)
        return 1

    app = Application()
    return app.main(args[1:])
