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


from . import __version__


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
        target = os.path.join('common', folder)
        if not os.path.exists(target):
            self.call('git', 'clone', 'https://github.com/'+repo, target)
        else:
            self.call('git', 'pull', cwd=target)
        self.call('git', 'reset', '--hard', rev, cwd=target)
        if os.path.exists(os.path.join(target, 'setup.py')):
            self.call('python', 'setup.py', 'develop', cwd=target)
        return folder, ''

    def recipe_extract(self, archive, target):
        if not os.path.exists(target):
            zf = zipfile.ZipFile(archive)
            base, *files = zf.namelist()
            if all([f.startswith(base) for f in files]):
                zf.extractall(path=".")
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
        self.call('pip', 'install', *packages)
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
                display('\nERROR: Failed during command execution. See `{}.log` for details.'.format(self.command), ansi.RED)
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
        return params

    def main(self, args):
        self.params = self._parse(args)

        self.command, package = self.params.command, self.params.package
        self.log = open(self.command+'.log', 'w')

        if not os.path.isdir(package):
            self.call('git', 'clone', 'http://courses.nucl.ai/packages/{}.git'.format(package))
        else:
            self.call('git', 'pull', '-u', cwd=package)
        self.execute()
            
        if not os.path.isdir('common'):
            os.mkdir('common')

        filename = os.path.join(package, 'nuclai.json')
        pkg = json.load(open(filename))
        if float(__version__) < float(pkg['version']):
            display('ERROR: Run `pip install --upgrade nuclai` to get latest tool version.'.format(package), ansi.RED)
            return 1
        
        proc = getattr(self, 'cmd_'+self.command)
        proc(package, pkg)
        print('')
        return 0


def main(args):
    # Windows needs some customization to work out-of-the-box.  
    if 'win32' in sys.platform:
        # Must be a UTF-8 compatible codepage in the terminal or output doesn't work.
        with open(os.devnull, 'w') as null:
            subprocess.call(['chcp', '65001'], stdout=null, stderr=null, shell=True)
        
        # Optionally relaunch the application to let Python update the stdout encoding.
        try:
            print("…\r")
        except UnicodeEncodeError:
            os.execv(sys.executable, [sys.executable] + args)

    # Fail if the user is running from a system-wide Python 3.4 installation.
    if not hasattr(sys, 'base_prefix'):
        display('ERROR: Please run this script from a virtual environment.\n', color=ansi.RED_B)
        executable = os.path.split(sys.executable)[1]
        display('  > {} -m venv pyenv\n'.format(executable), color=ansi.RED)
        return 1

    app = Application()
    return app.main(args[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
