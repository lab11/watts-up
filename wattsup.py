#!/usr/bin/env python
"""record data from WattsUp power meter

Reads data from a Watts Up PRO or compatible power meter (http://www.wattsupmeters.com).
Plots in real time, can run in simulation mode, reading from a file rather than
a physical power meter.

Output format will be space sperated containing:
YYYY-MM-DD HH:MM:SS.ssssss n W V A
where n is sample number, W is power in watts, V volts, A current in amps

Usage: "wattsup.py -h" for options

Author: Kelsey Jordahl
Copyright: Kelsey Jordahl 2011
License: GPLv3
Time-stamp: <Tue Sep 20 09:14:29 EDT 2011>

"""

from __future__ import print_function

import os, serial
import datetime, time
import argparse
import json
import curses
import string
import sys



USER_AGENT = 'WattsUp.NET'


commands = {'header_request':   '#H,R,0;',
            'version_request':  '#V,R,0;',
            'network_info':     '#I,Q,0;',
            'network_info_ext': '#I,E,0;',
            'set_network_ext':  '#I,X,5,{},{},{},{},{};',
            'write_network':    '#I,W,0;',
            'logging':          '#L,W,3,E,,{};',
            'reset':            '#V,W,0;'}

verbose = False

class stdoutfile ():
    def write (self, s):
        print(s, end='')
    def close (self):
        pass

class wattsup (object):

    def __init__(self, port):

        if verbose:
            print('Looking for {}'.format(port))

        if not os.path.exists(port):
            # Could not find the watts up meter
            raise Exception('Unable to find {}'.format(port))

        self.s = serial.Serial(port, 115200)

    def getHeader (self):
        """ Return an array of strings that identify the data columns. """
        if verbose:
            print('Retrieving header information')

        # Loop until the header info comes back
        while True:
            self.s.write(commands['header_request'])
            h = self.s.readline()
            if h[0:2] == "#h":
                break

        hf = h.split(';')[0].split(',')
        return hf[3:]

    def getVersionInfo (self):
        """ Returns a string that nicely formats the meter's version and info"""
        if verbose:
            print('Retrieving identifying information')

        while True:
            self.s.write(commands['version_request'])
            i = self.s.readline()
            if i[0:2] == "#v":
                ifields = i.split(';')[0].split(',')[3:]
                if len(ifields) == 8:
                    break
        ret = ''
        versions = ['Standard', 'PRO', 'ES', '.NET']
        hwma = ['ADE7763, PIC18F45J10', 'ADE7763, PIC18F45J10, Ethernet']
        hwmi = ['no USB', 'USB @ 19200bps', 'USB @ 115200bps', 'Ethernet']
        comptime = datetime.datetime.strptime(ifields[6], '%Y%m%d%H%M%S')
        ret += 'Watts Up? Meter Version Information:\n'
        ret += 'Model type:     {}\n'.format(versions[int(ifields[0])])
        ret += 'Memory (bytes): {}\n'.format(ifields[1])
        ret += 'Hardware Major: {}\n'.format(hwma[int(ifields[2])-5])
        ret += 'Hardware Minor: {}\n'.format(hwmi[int(ifields[3])])
        ret += 'Firmware Major: {}\n'.format(ifields[4])
        ret += 'Firmware Minor: {}\n'.format(ifields[5])
        ret += 'SW Compilation: {}\n'.format(comptime)
        return ret

    def getNetworkInfo (self):
        if verbose:
            print('Retrieving network information')

        while True:
            self.s.write(commands['network_info'])
            i = self.s.readline()
            if i[0:2] == "#i":
                n1 = i.split(';')[0].split(',')[3:]
                if len(n1) == 7:
                    break

        while True:
            self.s.write(commands['network_info_ext'])
            i = self.s.readline()
            if i[0:2] == "#i":
                n2 = i.split(';')[0].split(',')[3:]
                if len(n2) == 5:
                    break

        mac = ':'.join(s.encode('hex') for s in n1[6].decode('hex'))
        ret = ''
        ret += 'Watts Up? Meter Network Information:\n'
        ret += 'IP Address:    {}\n'.format(n1[0])
        ret += 'Gateway:       {}\n'.format(n1[1])
        ret += 'DNS 1:         {}\n'.format(n1[2])
        ret += 'DNS 2:         {}\n'.format(n1[3])
        ret += 'Net Mask:      {}\n'.format(n1[4])
        ret += 'DHCP:          {}\n'.format(bool(n1[5]))
        ret += 'MAC Address:   {}\n'.format(mac)
        ret += 'POST Host:     {}\n'.format(n2[0])
        ret += 'POST Port:     {}\n'.format(n2[1])
        ret += 'POST File:     {}\n'.format(n2[2])
        ret += 'User Agent:    {}\n'.format(n2[3])
        ret += 'POST Interval: {} seconds\n'.format(n2[4])
        return ret

    def log (self, outfile=None, interval=1, format='raw'):
        """ Log data from the watts up """
        if outfile:
            f = open(outfile, 'w')

            f.write('# Readings from a Watts Up? Meter\n')
            f.write('# {}\n\n'.format(datetime.datetime.now()))

            if format == 'raw':
                f.write('timestamp,{}\n'.format(','.join(self.getHeader())))
        else:
            f = stdoutfile()

        self.s.write(commands['logging'].format(int(interval)))

        try:
            while True:
                l = self.s.readline()
                if l[0:2] == '#d':
                    vals = l.split(';')[0].split(',')[3:]

                    now = int(time.time()*1000)

                    m = [('time', now),
                         ('watts', float(vals[0])/10.0),
                         ('volts', float(vals[1])/10.0),
                         ('amps', float(vals[2])/10.0),
                         ('watt-hours', float(vals[3])/10.0),
                         ('dollars', float(vals[4])/1000.0),
                         ('watt hours monthly', float(vals[5])),
                         ('dollars monthly', float(vals[6])*10.0),
                         ('power factor', float(vals[7])),
                         ('duty cycle', float(vals[8])),
                         ('power cycle', float(vals[9])),
                         ('frequency', float(vals[10])/10.0),
                         ('volt-amps', float(vals[10])/10.0)]

                    if format == 'raw':
                        for i,item in zip(range(len(m)), m):
                            f.write('{}'.format(item[1]))
                            if i == len(m) - 1:
                                f.write('\n')
                            else:
                                f.write(',')

                    elif format == 'pretty':
                        for i,item in zip(range(len(m)), m):
                            f.write('{} {}'.format(item[1], item[0]))
                            if i == len(m) - 1:
                                f.write('\n')
                            else:
                                f.write(', ')

                    elif format == 'json':
                        f.write('{}\n'.format(json.dumps(dict(m))))

        except KeyboardInterrupt:
            self.s.close()

    def setNetworkExtended (self, url, port, pfile, interval=1):
        if len(url) > 40:
            print("POST URL too long. Must be 40 characters or less.")
            sys.exit(1)
        if len(pfile) > 40:
            print("POST file too long. Must be 40 characters or less.")
            sys.exit(1)

        cmd = commands['set_network_ext'].format(url, port, pfile,
            USER_AGENT, int(interval))
        self.s.write(cmd)
        self.s.readline()
        self.s.write(commands['write_network'])
        self.s.readline()

    def reset (self):
        """ Soft reset the watts up """
        if verbose:
            print("Resetting the Watts Up")

        self.s.write(commands['reset'])



    def mode(self, runmode):
        if args.sim:
            return                      # can't set run mode while in simulation
        self.s.write('#L,W,3,%s,,%d;' % (runmode, self.interval) )
        if runmode == INTERNAL_MODE:
            self.s.write('#O,W,1,%d' % FULLHANDLING)

    def fetch(self):
        if args.sim:
            return                      # can't fetch while in simulation
        for line in self.s:
            if line.startswith( '#d' ):
                fields = line.split(',')
                W = float(fields[3]) / 10;
                V = float(fields[4]) / 10;
                A = float(fields[5]) / 1000;




if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Get data from Watts Up power meter.')
    parser.add_argument('-v', '--verbose',
                        dest='verbose',
                        action='store_true',
                        help='Extra output messages')
    parser.add_argument('--header',
                        dest='header',
                        action='store_true',
                        help='Print the data header info and exit.')
    parser.add_argument('-l', '--log',
                        dest='log',
                        action='store_true',
                        help='Tell the meter to send us samples via USB.')
    parser.add_argument('-f', '--format',
                        dest='format',
                        choices=['raw', 'pretty', 'json'],
                        default='raw',
                        help='How to display the data in log format. raw: \
comma separated values directly from watts up. pretty: easy to read by humans. \
json: JSON dict.')
    parser.add_argument('--outfile',
                        dest='outfile',
                        action='store',
                        help='File to write samples to in log mode.')
    parser.add_argument('--save',
                        dest='save',
                        action='store_true',
                        help='Like --outfile, but the filename is set for you.')
    parser.add_argument('-s', '--sample-interval',
                        dest='interval',
                        default=1.0,
                        type=int,
                        help='Sample interval (default 1 s)')
    parser.add_argument('-n', '--network-config',
                        dest='network',
                        action='append',
                        nargs=3,
                        help='Configure POST settings. <POST URL> <POST port> \
<POST file>')
    parser.add_argument('--reset',
                        dest='reset',
                        action='store_true',
                        help='Soft reset the meter.')
    parser.add_argument('-i', '--info',
                        dest='info',
                        action='store_true',
                        help='Request identifying information from the meter.')
    parser.add_argument('-p', '--port',
                        dest='port',
                        required=True,
                        help='USB serial port that the meter is connected to')
    args = parser.parse_args()

    if args.verbose:
        verbose = True

    # Connect to the meter
    meter = wattsup(args.port)

    # Do the commands in the correct order

    if args.header:
        # Get the header info for the data
        print('Headings: {}'.format(', '.join(meter.getHeader())))
        sys.exit(0)

    if args.info:
        print(meter.getVersionInfo())
        print(meter.getNetworkInfo())
        sys.exit(0)

    if args.reset:
        meter.reset()
        sys.exit(0)

    if args.log:
        if args.outfile:
            outfile = args.outfile
        elif args.save:
            outfile = 'wattsup_{}.data'.format(
                datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        else:
            # stdout
            outfile = None

        # Tell the meter to send us samples
        meter.log(outfile=outfile, interval=args.interval, format=args.format)

    elif args.network:
        url = args.network[0][0]
        port = args.network[0][1]
        pfile = args.network[0][2]

        interval = 1
        if args.interval:
            interval = int(args.interval)

        meter.setNetworkExtended(url, port, pfile, interval)


























