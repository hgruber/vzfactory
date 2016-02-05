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
name       = os.path.dirname(os.path.realpath(dockerfile)).split('/')[-1].lower()

def call(arg):
    if subprocess.call(arg) != 0:
        print 'Failed:'
        print arg
        print 'Aborting'
        sys.exit(0)

def vzcreate(arg):
    call(['/usr/sbin/vzctl', 'create', vid, '--ostemplate', arg, '--ipadd', ip, '--name', name, '--hostname', name ])
    call(['/usr/sbin/vzctl', 'start', vid])
    # src directory where Dockerfile is located
    src = os.path.dirname(os.path.realpath(dockerfile))
    dst = '/vz/root/' + vid + '/vztmp'
    call(['/usr/sbin/vzctl', 'exec2', vid, 'mkdir /vztmp'])
    call(['/bin/mount', '--bind', src, dst])

def vzadd(arg):
    lastarg = arg.split(' ')[-1]
    call(['/usr/sbin/vzctl', 'exec2', vid, 'cd /vztmp; mkdir -p $(dirname '+lastarg+'); cp -r '+arg])

def vzexec(arg):
    call(['/usr/sbin/vzctl', 'exec2', vid, arg])

def nop(arg):
    print '  --> NOT implemented'

image_change = [ 'FROM', 'LABEL', 'ADD', 'COPY', 'RUN', 'ENV', 'ENTRYPOINT', 'CMD' ]
functions = {
    'FROM':         vzcreate,
    'MAINTAINER':   nop,
    'RUN':          vzexec,
    'CMD':          nop,
    'LABEL':        nop,
    'EXPOSE':       nop,
    'ENV':          nop,
    'ADD':          vzadd,
    'COPY':         vzadd,
    'ENTRYPOINT':   nop,
    'VOLUME':       nop,
    'USER':         nop,
    'WORKDIR':      nop,
    'ARG':          nop,
    'ONBUILD':      nop,
    'STOPSIGNAL':   nop
}

def run(commands):
    for command in commands:
        if command['command'] not in functions:
            print command['command'], command['arguments'], 'NOT LISTED'
            continue
        cmd = functions[command['command']]
        arg = command['arguments']
        print command['command'], arg
        cmd(arg)

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
