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
    return ansi.BOLD+text+ansi.ENDC

def display(text, color=ansi.WHITE):
    bold = color.replace('[0;', '[1;')
    text = re.sub(r'`(.*?)`', r'`{}\1{}`'.format(bold, color), text)
    print("%s%s%s" % (color, text, ansi.ENDC))


class Application(object):

    def call(self, *cmdline, **params):
        ret = subprocess.call(cmdline, stdout=self.log, stderr=self.log, **params)
        if ret != 0: print('Error %i' % ret)
    
    def cmd_install(self, name, pkg):
        display('Installing nucl.ai package `%s`.' % (name), ansi.BLUE)
    
        for cmd, *args in pkg['install']['osx']:
            if cmd == 'github':
                repo, rev = args
                folder = re.split('[/.]', repo)[1]
                print('  *', style(cmd), folder)
                        
                self.call('git', 'clone', 'https://github.com/'+repo)
                self.call('git', 'reset', '--hard', rev, cwd=folder)
                if os.path.exists(os.path.join(folder, 'setup.py')):
                    self.call('python3', 'setup.py', 'develop', cwd=folder)
    
            if cmd == 'shell':
                print('  *', style(cmd), args[0])
                self.call(*args[1:], shell=True)
    
            if cmd == 'pypi':
                print('  *', style(cmd), *args)
                self.call('pip', 'install', '--upgrade', *args)
    
            if cmd == 'exec':
                if args[0].endswith('.py'):
                    args.insert(0, 'python3')
                self.call(*args)
    
            if cmd == 'fetch':
                if not os.path.exists(args[1]):
                    print('  *', style(cmd), args[1])
                    urllib.request.urlretrieve(*args)

    def cmd_demo(self, name, pkg):
        display('Demonstrating nucl.ai package `%s`.' % (name), ansi.BLUE)
        
        for cmd, *args in pkg['demo']:
            print('  *', style(cmd), *args)
    
            if cmd == 'open':
                call('open', *args)
    
            if cmd == 'exec':
                if args[0].endswith('.py'):
                    args.insert(0, 'python3')
                call(*args)
    
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
        return 0


def main(args):
    app = Application()
    return app.main(args)
