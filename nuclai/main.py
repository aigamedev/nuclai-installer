import os
import re
import json
import subprocess


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


def do_install(package):
    display('Installing package `%s`.' % (package), ansi.BLUE)
    pkg = json.load(open(package+'.json'))
    
    if not os.path.isdir(package):
        os.mkdir(package)
    os.chdir(package)

    log = open('install.log', 'w')
    def call(*cmdline, cwd=None):
        subprocess.call(cmdline, stdout=log, stderr=log, cwd=cwd)

    for cmd, *args in pkg['install']['osx']:
        if cmd == 'github':
            repo, rev = args
            folder = re.split('[/.]', repo)[1]
            print('  *', style(cmd), folder)
                    
            call('git', 'clone', 'https://github.com/'+repo)
            call('git', 'reset', '--hard', rev, cwd=folder)
            if os.path.exists(os.path.join(folder, 'setup.py')):
                call('python3', 'setup.py', 'develop', cwd=folder)

        if cmd == 'pypi':
            print('  *', style(cmd), *args)
            call('pip', 'install', '--upgrade', *args)


def main(args):
    commands = {
        'install': do_install
    }
    
    commands[args[1]](*args[2:])
    return 0
