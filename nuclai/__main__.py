import os
import re
import sys
import json
import glob
import time
import shutil
import zipfile
import tarfile
import argparse
import tempfile
import subprocess
import urllib.request
import urllib.parse
import uuid
import distutils.util

__version__ = '0.6'


class ansi:
    WHITE = '\033[0;97m'
    WHITE_B = '\033[1;97m'
    YELLOW = '\033[0;33m'
    YELLOW_B = '\033[1;33m'
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
            self.cmdline = cmdline
            ret = subprocess.call(cmdline, stdout=self.log, stderr=self.log, **params)
            if ret != 0:
                raise RuntimeError('Command {} returned status {}.'.format(cmdline[0], ret))
        self.calls = []
    
    def recipe_github(self, repo, rev, target=None):
        folder = re.split('[/.]', repo)[1]
        target = os.path.join(target or self.params.package, folder)
        if not os.path.exists(target):
            self.call('git', 'clone', 'https://github.com/'+repo, target)
        else:
            self.call('git', 'pull', cwd=target)
        self.call('git', 'reset', '--hard', rev, cwd=target)
        return folder, '', target

    def recipe_ghpy(self, repo, rev):
        short, desc, target = self.recipe_github(repo, rev, 'common')
        self.call('python', 'setup.py', 'develop', cwd=target)
        return short, desc

    def recipe_extract(self, archive, target):
        forceClean = False
        archiveFormat = "zip"
        if 'linux' in sys.platform or 'darwin' in sys.platform:
            archiveFormat = "tar" 

        if urllib.parse.urlparse(archive).netloc: # if archive is hosted somehere on remote machine, dowload it first
            segments = archive.split("/")
            archive = archive + "/" + segments[-1] if segments[-1] else archive + segments[-2] # if absolute
            archive = '{}-{}.{}'.format(archive, distutils.util.get_platform().replace('.', '_').replace('-', '_'), archiveFormat)
            tmpArchive = str(uuid.uuid1()) + "." + archiveFormat
            try:
                urllib.request.urlretrieve(archive, tmpArchive)
            except urllib.error.HTTPError as e:
                raise RuntimeError("File not found (404): {}.".format(archive))
            archive = tmpArchive
            forceClean = True
        else:
           archive = archive + archiveFormat

        try:
            target = os.path.join(self.params.package, target)
            if not os.path.exists(target):
                # Use .tar here becasue zip doesn't store permissions.
                if 'linux' in sys.platform or 'darwin' in sys.platform:
                    archiveFile = tarfile.TarFile(archive)
                    if 'darwin' in sys.platform:
                        _, base, *files = archiveFile.getmembers() # one extra file for mac
                    else:
                        base, *files = archiveFile.getmembers()
                    base = base.name 
                    validate = lambda f: f.name.startswith(base)
                else: # 'win32'
                    archiveFile = zipfile.ZipFile(archive)
                    base, *files = archiveFile.namelist()
                    validate = lambda f: f.startswith(base)
                if all([validate(f) for f in files]):
                    archiveFile.extractall(path=self.params.package)
                    shutil.move(os.path.join(self.params.package, base), target)
                else:
                    assert False, "Found no root folder as expected."
                archiveFile.close()
        finally:
            if forceClean: os.remove(archive) # if archive downloaded. always remove

        if not forceClean: os.remove(archive) # if archive from local filesystem, remove only on success
        return target, ''

    def recipe_script(self, name):
        exec_line = name + ".bat" if 'win32' in sys.platform else "./" + name + ".sh"
        return self.recipe_exec(exec_line)
        
    def recipe_shell(self, title, *args):
        self.call(*args, shell=True)
        return title, ''

    def recipe_pypi(self, *packages):
        self.call('pip', 'install', *packages)
        return ' '.join(packages),  ''

    def recipe_wheel(self, root, slug):
        # @TODO: remove hardcoded values for abi tag, try to download from the most general to the most specific
        cp1 = "cp" + str(sys.version_info.major) + str(sys.version_info.minor)
        cp2 = "none" if 'win32' in sys.platform else cp1 + "m"
        filename = '{}-{}-{}-{}.whl'.format(slug, cp1, cp2, distutils.util.get_platform().replace('.', '_').replace('-', '_'))
        url = root + filename
        filename = os.path.join(tempfile.mkdtemp(), filename)
        self.brief = slug
        try:
            urllib.request.urlretrieve(url, filename)
        except urllib.error.HTTPError as e:
            raise RuntimeError("File not found as wheel: {}.".format(slug))
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
        elif 'linux' in sys.platform:
            self.call('xdg-open', target)
        else: 
            self.call('open', target)
        return target, ''

    def cmd_install(self, name, pkg):
        display('Installing nucl.ai package `{}`.'.format(name), ansi.BLUE)
        platform = 'windows' if 'win32' in sys.platform else 'osx' # the same recipe for osx and linux.
        if 'all' in pkg['install']: self.do_recipes(pkg['install']['all']) # execute common
        if platform in pkg['install']: self.do_recipes(pkg['install'][platform]) # execute specific if any

    def cmd_demo(self, name, pkg):
        os.chdir(name)
        display('Demonstrating nucl.ai package `{}`.'.format(name), ansi.BLUE)
        self.do_recipes(pkg['demo'])
        
    def do_recipes(self, recipes):
        for cmd, *args in recipes:
            recipe = getattr(self, 'recipe_'+cmd)
            step = ansi.WHITE_B+('{: <8}'.format(cmd))+ansi.ENDC
            self.cmdline = None # reset cmdline, otherwsie it remembers an old one if new one is not set
            exception = None
            try:
                status, error = '✓', None
                self.brief, detail, *_ = recipe(*args)
                print(' ● {} {: <40} …'.format(step, self.brief), end='', flush=True)
                self.execute()
            except RuntimeError as e:
                detail, status = None, ansi.RED_B + '✗' + ansi.ENDC
                error = '\rERROR: Failed during command execution. See `{}.log` for details.'.format(self.command)
                exception = e 
            except OSError as e:
                detail, status = None, ansi.RED_B + '✗' + ansi.ENDC
                error = '\rERROR: Could not execute `{}`; {}.'.format(self.cmdline[0], e.strerror)
                exception = e 
            except:
                import traceback
                traceback.print_exc()

            if self.brief: print('\r ● {} {: <40} {}'.format(step, self.brief, status), flush=True)
            else: print('\r ● {} {: <40} {}'.format(step, "", status), flush=True)
            self.brief = None

            if error is not None:
                message = "Some error occured." # the default message - should never be printed
                if self.cmdline:
                    message = "\n" + error + "\n\n  > {}".format(' '.join(self.cmdline))
                elif exception:
                    message = str(exception)
                display(message, ansi.RED)
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
        sub.required = True
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
            self.call('git', 'pull', cwd=package)
            self.call('git', 'checkout', cwd=package)
        
        try:
            self.execute()
            self.log.truncate()
        except RuntimeError:
            display('ERROR: Failed to retrieve package. See `{}.log` for details.'.format(self.command), ansi.RED)
            return 1
        except OSError as e:
            self.log.write(e.strerror)
            display('ERROR: Could not execute `{}`, error code {}.'.format(self.cmdline[0], e.errno), ansi.RED)
            return 1

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
    # Window terminals need some customization to work out-of-the-box with unicode.  
    if 'win32' in sys.platform:
        # Must be a UTF-8 compatible codepage in the terminal or output doesn't work.
        with open(os.devnull, 'w') as null:
            subprocess.call(['chcp', '65001'], stdout=null, stderr=null, shell=True)
        
        # Optionally relaunch the application to let Python update the stdout encoding.
        try:
            print("…\r \r", end='')
        except UnicodeEncodeError:
            return os.spawnv(os.P_WAIT, sys.executable, [sys.executable] + args)

    # Use colored console output; required on Windows only, works by default elsewhere.
    try:
        import colorama; colorama.init(); del colorama
    except ImportError:
        pass

    import platform
    if platform.architecture()[0] != '64bit':
        display('WARNING: Running on 32-bit platforms is not officially supported.\n', color=ansi.YELLOW_B)

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
