import os
import re
import sys
import json
import time
import subprocess
import urllib.request


class ansi:
    BOLD = '\033[1;97m'
    WHITE = '\033[0;97m'
    YELLOW = '\033[0;33m'
    RED = '\033[0;31m'
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
        for cmdline, params in self.calls:
            # , stdout=self.log, stderr=self.log
            ret = subprocess.call(cmdline, **params)
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
            self.call('python3', 'setup.py', 'develop', cwd=folder)            
        return folder, ''

    def recipe_shell(self, title, *args):
        self.call(*args, shell=True)
        return title, ''

    def recipe_pypi(self, *packages):
        self.call('pip', 'install', '--upgrade', *packages)
        return ' '.join(packages),  ''

    def recipe_exec(self, *args):
        args, brief = list(args), os.path.split(args[0])[1]
        if args[0].endswith('.py'):
            args.insert(0, 'python3')
        self.call(*args)
        return brief,  ''

    def recipe_fetch(self, url, file):
        if not os.path.exists(file):
            urllib.request.urlretrieve(url, file)
        return file, ''

    def recipe_open(self, target):
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
            step = ansi.BOLD+('{: <8}'.format(cmd))+ansi.ENDC

            try:
                status = '✓'
                brief, detail = recipe(*args)
                print(' ● {} {: <40} …'.format(step, brief), end='', flush=True)
                self.execute()
            except RuntimeError:
                print('RuntimeError')
                status = ansi.RED + '✗' + ansi.ENDC
            except:
                import traceback
                traceback.print_exc()
            
            print('\r ● {} {: <40} {}'.format(step, brief, status))
    
    def is_stale(self, filename):
        if not os.path.exists(filename):
            return True

        modified = os.path.getmtime(filename)
        yesterday = time.time() - 24 * 3600
        return bool(modified < yesterday)
    
    def main(self, args):
        cmd, package = args[1], args[2]
        command = getattr(self, 'cmd_'+cmd)

        if not os.path.isdir(package):
            os.mkdir(package)
        os.chdir(package)

        filename = package+'.json'
        if self.is_stale(filename):
            urllib.request.urlretrieve('http://courses.nucl.ai/packages/'+filename, filename)
        pkg = json.load(open(filename))
        
        self.log = open(cmd+'.log', 'w')
        command(package, pkg)
        print('')
        return 0


def main(args):
    # Must be a UTF-8 compatible codepage in the terminal or output doesn't work.
    if 'win32' in sys.platform:
        with open(os.devnull, 'w') as null:
            subprocess.call(['chcp', '65001'], stdout=null, stderr=null, shell=True)

    app = Application()
    return app.main(args)
