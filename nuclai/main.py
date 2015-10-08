import os
import re
import json
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

def style(text):
    return ansi.BOLD+('{: <8}'.format(text))+ansi.ENDC

def display(text, color=ansi.WHITE):
    bold = color.replace('[0;', '[1;')
    text = re.sub(r'`(.*?)`', r'`{}\1{}`'.format(bold, color), text)
    print("%s%s%s" % (color, text, ansi.ENDC))


class Application(object):

    def call(self, *cmdline, **params):
        ret = subprocess.call(cmdline, stdout=self.log, stderr=self.log, **params)
        if ret != 0:
            raise RuntimeError('Command returned status %i.' % ret)
    
    def recipe_github(self, repo, rev):
        folder = re.split('[/.]', repo)[1]
        if not os.path.exists(folder):
            self.call('git', 'clone', 'https://github.com/'+repo)
        else:
            self.call('git', 'pull', cwd=folder)
        self.call('git', 'reset', '--hard', rev, cwd=folder)
        if os.path.exists(os.path.join(folder, 'setup.py')):
            self.call('python3', 'setup.py', 'develop', cwd=folder)            
        return repo, ''

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
            try:
                status = '✓'
                brief, detail = recipe(*args)
            except:
                status = '✗'
            print(' ● {} {: <40} {}'.format(style(cmd), brief, status))
    
    def main(self, args):
        commands = {
            'install': self.cmd_install,
            'demo': self.cmd_demo
        }
        cmd, package = args[1], args[2]
        assert cmd in commands
    
        pkg = json.load(open(package+'.json'))
        
        if not os.path.isdir(package):
            os.mkdir(package)
        os.chdir(package)
        
        self.log = open(cmd+'.log', 'w')
        commands[cmd](package, pkg)
        print('')
        return 0


def main(args):
    app = Application()
    return app.main(args)
