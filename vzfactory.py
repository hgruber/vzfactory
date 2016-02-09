#!/usr/bin/python

import re
import json
import os
import sys
import hashlib
import subprocess

vid        = '1000'
dockerfile = 'Dockerfile'
ip         = '10.0.2.18'
vzconf     = '/etc/vz/vz.conf'
workdir    = '/'

name       = os.path.dirname(os.path.realpath(dockerfile)).split('/')[-1].lower()
environment= []
maintainer = ''

def vzroot():
    root = re.compile('^VE_ROOT=(.*)\$.*')
    for line in open(vzconf).readlines():
        if root.match(line): return root.sub('\\1', line).strip()
        else: return '/vz/root/'

def vzabort(arg):
    print arg
    print 'Aborting'
    sys.exit(0)

def call(arg):
    if subprocess.call(arg) != 0:
        print 'Failed:'
        vzabort(arg)

def vzcreate(arg):
    call(['/usr/sbin/vzctl', 'create', vid, '--ostemplate', arg, '--ipadd', ip, '--name', name, '--hostname', name ])
    call(['/usr/sbin/vzctl', 'start', vid])
    # src directory where Dockerfile is located
    src = os.path.dirname(os.path.realpath(dockerfile))
    dst = vzroot() + vid + '/vztmp'
    call(['/usr/sbin/vzctl', 'exec2', vid, 'mkdir /vztmp'])
    call(['/bin/mount', '--bind', src, dst])

def vzadd(arg):
    files = ''
    try: a = json.loads(arg)
    except:
        lastarg = arg.split(' ')[-1]
        if lastarg[0] != '/':
            lastarg = workdir + lastarg
        array = arg.split(' ')
        for file in array[:-1]: files = files + file + ' '
        files = files + lastarg
    else:
        lastarg = a[-1]
        if lastarg[0] != '/':
            lastarg = workdir + lastarg
        for file in a[:-1]: files = files + '"' + file + '" '
        files = files + '"' + lastarg + '"'
    call(['/usr/sbin/vzctl', 'exec2', vid, 'cd /vztmp; mkdir -p $(dirname '+lastarg+'); cp -rv '+files])

def vzexec(arg):
    call(['/usr/sbin/vzctl', 'exec2', vid, arg])

def vzenv(arg):
    element = arg.split(' ')
    if '=' in element[0]:
        for elem in element:
            a = elem.split('=')
            environment.append({a[0]: a[1]})
    else:
        if len(element) != 2:
            vzabort('environment variable without value is not allowed')
        environment.append({element[0]: element[1]})

def vzdir(arg):
    workdir = arg
    if workdir[-1] != '/': workdir = workdir + '/'

def vzmaintain(arg):
    maintainer = arg

def nop(arg):
    print '  --> NOT implemented'


image_change = [ 'FROM', 'LABEL', 'ADD', 'COPY', 'RUN', 'ENV', 'ENTRYPOINT', 'CMD' ]
functions = {
    'FROM':         vzcreate,
    'MAINTAINER':   vzmaintain,
    'RUN':          vzexec,
    'CMD':          nop,
    'LABEL':        nop,
    'EXPOSE':       nop,
    'ENV':          vzenv,
    'ADD':          vzadd,
    'COPY':         vzadd,
    'ENTRYPOINT':   nop,
    'VOLUME':       nop,
    'USER':         nop,
    'WORKDIR':      vzdir,
    'ARG':          nop,
    'ONBUILD':      nop,
    'STOPSIGNAL':   nop
}

def run(commands):
    step = 1
    for command in commands:
        if command['command'] not in functions:
            vzabort('Error: unknown command ' + command['command'])
        cmd = functions[command['command']]
        arg = command['arguments']
        print 'Step ' + str(step) + ': ' + command['command'] + ' ' + arg
        cmd(arg)
        step = step + 1

def parse_dockerfile(dockerfile):
    comment = re.compile('^(#.*)$')
    nextline = re.compile('.*\\\$')
    arg = re.compile('([^ ]*)[ ](.*)')
    previous=''
    cs = ''
    commands = []
    for line in open(dockerfile).readlines():
        line = line.strip()
        if not line or comment.match(line): continue 
        if previous:
            line = previous[:-1] + line
            previous = ''
        if nextline.match(line):
            previous=line
            continue
        key = arg.sub('\\1',line)
        args = arg.sub('\\2',line)
        if key in image_change:
            cs = hashlib.sha1(cs+key+args).hexdigest()
        commands.append({ 'command': key, 'arguments': args, 'hash': cs })
    return commands

commands = parse_dockerfile(dockerfile)
run(commands)
