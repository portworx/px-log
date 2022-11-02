#!/usr/bin/env python3
# - Log parser for portworx.service logfiles

import os
import sys
import re
import argparse
from collections import defaultdict
from datetime import timezone as tz
from dateutil import parser as dupa


# GLOBALS
#
version = '1.0.1'
lineFormat = os.getenv(
    'PX_LOG_FORMAT', default='%(time)19s %(lcode)s %(msg)-100s %(misc)s')
tm0 = 0
utf8stdout = open(1, 'w', encoding='utf-8', closefd=False)  # fd 1 is stdout

reKV = re.compile(r'(\w+)=(".*?(?<!\\)"|\S+)\s*')
reTm = re.compile(r'^time="(20\d\d-[0-9:TZ-]+)"\s+')
reTm2 = re.compile(
    r'^(20\d{2}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\,\d+)?|.{3} \d{2} \d{2}:\d{2}:\d{2})\s+')
reHost = re.compile(r'^[@]*([a-z0-9\.-]+) (\w+)\[\d+\]: ')
reSev = re.compile(
    r'^\s*(DEBUG|TRACE|INFO|WARN|WARNING|ERROR|FATAL|CRIT)[:]*\s+')

miscSkip = ['time', 'asctime', 'reltime',
            'host', 'level', 'unit', 'msg', 'orig']


class Line:
    def __init__(self, line):
        global tm0
        line = line.rstrip()
        self.pt = defaultdict(str, orig=line)
        line = self.lstrip(line)

        # process <key>=<value> fields
        idx = 0
        while True:
            m = reKV.match(line, pos=idx)
            if not m:
                break
            (k, v) = m.group(1, 2)
            if v:
                self.pt[k] = v.strip(' \t"')
            idx = m.end()
        # have unmatched?
        if idx >= 0 and idx != len(line):
            self.pt['msg'] += line[idx:]

        # move severity into 'level'  (if applicable)
        m = reSev.match(self.pt['msg'])
        if m:
            self.pt['level'] = m.group(1)
            self.pt['msg'] = self.pt['msg'][m.end():]

        # record 1st timestamp
        if not tm0 and 'time' in self.pt:
            tm0 = dupa.parse(self.pt['time'])
            if not tm0.tzinfo:
                tm0 = tm0.replace(tzinfo=tz.utc)

    def lstrip(self, line):     # strip left side of logline  (remove timestamp, host and unit)
        m = reTm2.match(line)
        if m:
            self.pt['time'] = m.group(1)
            line = line[m.end():]
        m = reHost.match(line)
        if m:
            self.pt['host'] = m.group(1)
            self.pt['unit'] = m.group(2)
            line = line[m.end():]
        m = reTm2.match(line)
        if m:
            self.pt['time'] = m.group(1)
            line = line[m.end():]
        return line.rstrip()

    def level(self):            # convert level into color-code  (see https://en.wikipedia.org/wiki/ANSI_escape_code#3-bit_and_4-bit_
        if not 'level' in self.pt:
            return '', ' '
        lvl = self.pt['level'].lower()
        if not lvl:
            return '', ' '
        if lvl in ['error', 'fatal', 'crit']:
            # return u'\u001b[1;31m\u2717\u001b[m'
            return u'\u001b[1;31m', u'\u001b[1;31mX\u001b[m'
        elif lvl in ['warning', 'warn']:
            # return u'\u001b[1;33m\u26A0\u001b[m'
            return u'\u001b[1;33m', u'\u001b[1;30;43m!\u001b[m'
        elif lvl in ['info', 'note']:
            # return u'\u001b[32m\u2713\u001b[m'
            return '', u'\u001b[42m \u001b[m'
        elif lvl in ['debug', 'trace']:
            return u'\u001b[90m', ' '
        return '', lvl

    def td2str(self, td):       # convert time-difference into
        days, rem = divmod(int(td.total_seconds()), 86400)
        hors, rem = divmod(rem, 3600)
        mins, rem = divmod(rem, 60)
        if days > 0:
            return '{}_{:02}:{:02}:{:02}'.format(days, hors, mins, rem)
        elif hors > 0:
            return '   {:2}:{:02}:{:02}'.format(hors, mins, rem)
        else:
            return '      {:2}:{:02}'.format(mins, rem)

    def getasctm(self, dfl='.'):    # convert time to asctime
        if 'time' in self.pt:
            return dupa.parse(self.pt['time']).strftime("%F %T")
        return dfl

    def getdifftm(self, dfl='.'):   # convert time to reltime
        if 'time' in self.pt:
            tm = dupa.parse(self.pt['time'])
            if not tm.tzinfo:
                tm = tm.replace(tzinfo=tz.utc)
            return self.td2str(tm - tm0)
        return dfl

    def __str__(self):              # render string
        if args.isAscTime:
            self.pt['asctime'] = self.getasctm()
        if args.isRelTime:
            self.pt['reltime'] = self.getdifftm()

        if args.isMisc:
            misc, sep = '', ''
            for k in self.pt:
                v = self.pt[k]
                if k == 'unit' and v == 'systemd':
                    self.pt['msg'] = '\u001b[35m[systemd] ' + \
                        self.pt['msg'] + '\u001b[m'
                if k not in miscSkip:
                    if k == 'error' and v != '<nil>':
                        v = u'\u001b[31m' + v + '\u001b[m'
                    if ' ' in v:
                        v = '"' + v + '"'
                    misc += sep + k + '=' + v
                    sep = ' '
            self.pt['misc'] = misc

        clr, self.pt['lcode'] = self.level()
        if 'msg' in self.pt:
            self.pt['msg'] = self.pt['msg'].replace('\\"', '"')
            if clr:
                self.pt['msg'] = clr + self.pt['msg'] + '\u001b[m'
                if 'misc' in self.pt:
                    self.pt['misc'] = ' ' * (len(clr)+3) + self.pt['misc']

        return lineFormat % self.pt


def parseFile(input):
    global tm0
    tm0 = 0
    for line in input:
        print(Line(line), file=utf8stdout)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Portworx log parser.', usage='%(prog)s [options] [<log1> [<log2>...]]',
        formatter_class=argparse.RawTextHelpFormatter, epilog='''examples:
    %(prog)s px1.log px2.log          # display given log-files
    cat px2.log | %(prog)s            # parse logs from STDIN
    kubectl -n kube-system logs portworx-XXX | %(prog)s
    %(prog)s --fmt "%%(asctime)19s @%%(host)s [%%(level)s] %%(msg)s" px3.log
    %(prog)s --fmt "%%(reltime)11s %%(file)19s] %%(level)8.8s: %%(msg)s" px4.log
    ''')
    parser.add_argument('-A', '--asctime', default=False,
                        action='store_true', help='use ASCII time  (dfl: "%%F %%T" format)')
    parser.add_argument('-R', '--reltime', default=False,
                        action='store_true', help='use relative time')
    parser.add_argument('-F', '--fmt', metavar='FORMAT', type=str, action='store',
                        help='specify format  (dfl: "' + lineFormat.replace('%', '%%') + '")')
    parser.add_argument('logs', type=str, action='store', nargs='*',
                        help='log files to parse')
    parser.add_argument('-V', '--version', default=False,
                        action='store_true', help='display version')
    args = parser.parse_args()

    if args.version:
        print('px-log version ' + version)
        sys.exit(0)

    if args.fmt:
        lineFormat = args.fmt
    elif args.asctime:
        lineFormat = lineFormat.replace('%(time)19s ', '%(asctime)19s ')
    elif args.reltime:
        lineFormat = lineFormat.replace('%(time)19s ', '%(reltime)11s ')

    args.isMisc = 'misc' in lineFormat
    args.isRelTime = 'reltime' in lineFormat
    args.isAscTime = 'asctime' in lineFormat

    if len(args.logs) <= 0:
        print(
            '{0}: READY to read from STDIN  (CTRL-C to abort)'.format(sys.argv[0]), file=sys.stderr)
        parseFile(sys.stdin)
    else:
        for f in args.logs:
            with open(f, encoding='utf-8') as fd:
                parseFile(fd)
