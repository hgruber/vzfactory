#!/usr/bin/python

import re
import json
import os
import sys
import hashlib
import subprocess

vid = '1000'
dockerfile = 'Dockerfile'
ip = '10.0.2.18'

def call(arg):
    if subprocess.call(arg) != 0:
        print 'Failed:'
        print arg
        print 'Aborting'
        sys.exit(0)

def vzcreate(arg):
    call(['/usr/sbin/vzctl', 'create', vid, '--ostemplate', arg, '--ipadd', ip ])
    call(['/usr/sbin/vzctl', 'start', vid])
    # src directory where Dockerfile is located
    src = os.path.dirname(os.path.realpath(dockerfile))
    dst = '/vz/root/' + vid + '/vztmp'
    call(['/usr/sbin/vzctl', 'exec2', vid, 'mkdir /vztmp'])
    call(['/bin/mount', '-n', '-r', '-t', 'simfs', src, dst, '-o', src])

def vzmaintain(arg):
    print 'MAINTAINER '+arg+': NOT IMPLEMENTED'

def vzlabel(arg):
    print 'LABEL '+arg+': NOT IMPLEMENTED'
    sys.exit(0)

def vzadd(arg):
    print 'ADD '+arg
    lastarg = arg.split(' ')[-1]
    call(['/usr/sbin/vzctl', 'exec2', vid, 'cd /vztmp; mkdir -p $(dirname '+lastarg+'); cp -rv '+arg])

def vzexec(arg):
    print 'RUN '+arg
    call(['/usr/sbin/vzctl', 'exec2', vid, arg])

def vzenv(arg):
    print 'ENV '+arg+': NOT IMPLEMENTED'
    sys.exit(0)

def vzentry(arg):
    print 'ENTYPOINT '+arg+': NOT IMPLEMENTED'
    sys.exit(0)

def vzaddservice(arg):
    print 'CMD '+arg+': NOT IMPLEMENTED'
    sys.exit(0)

def cleanup():
    None 

image_change = [ 'FROM', 'LABEL', 'ADD', 'COPY', 'RUN', 'ENV', 'ENTRYPOINT', 'CMD' ]
functions = {
    'FROM':         vzcreate,
    'MAINTAINER':   vzmaintain,
    'LABEL':        vzlabel,
    'ADD':          vzadd,
    'COPY':         vzadd,
    'RUN':          vzexec,
    'ENV':          vzenv,
    'ENTRYPOINT':   vzentry,
    'CMD':          vzaddservice
}

def run(commands):
    for command in commands:
        if command['command'] not in functions:
            print command['command'], command['arguments'], 'NOT LISTED'
            continue
        cmd = functions[command['command']]
        arg = command['arguments']
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
